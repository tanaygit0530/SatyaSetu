import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import jwt
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.repositories.user_repository import UserRepository
from app.schemas.core import User, UserRole


class AuthService:
    """
    Production-ready authentication service using Twilio Verify with WhatsApp channel.
    Manages OTP generation, verification checks, phone number normalization,
    rate-limiting cooldowns, and secure JWT session issuance.
    """

    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()
        self._last_otp_request: Dict[str, float] = {}
        self._hourly_requests: Dict[str, List[float]] = {}
        self._verify_failures: Dict[str, int] = {}
        # WhatsApp linking tokens (single-use, short-lived)
        self._linking_tokens: Dict[str, Dict[str, Any]] = {}
        self._user_linking_tokens: Dict[str, str] = {}
        self._linking_cooldown: Dict[str, float] = {}

    def normalize_phone(self, raw_phone: str) -> str:
        """
        Validates and standardizes a phone number into strict E.164 format.
        E.164 pattern: +[country code][subscriber number], 8-15 total digits.
        """
        if not raw_phone or not raw_phone.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile phone number is required.",
            )

        # Remove spaces, hyphens, parentheses
        cleaned = re.sub(r"[\s\-\(\)]", "", raw_phone.strip())

        # If user entered 10 digits without country code (e.g. 9820123456), default to India (+91)
        if re.match(r"^[6-9]\d{9}$", cleaned):
            cleaned = f"+91{cleaned}"
        elif not cleaned.startswith("+"):
            cleaned = f"+{cleaned}"

        # Strict E.164 validation regex: + followed by 8 to 15 digits
        if not re.match(r"^\+[1-9]\d{7,14}$", cleaned):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid phone number format '{raw_phone}'. Must be in valid international E.164 format (e.g. +919820123456).",
            )

        return cleaned

    def _check_rate_limits(self, phone: str) -> None:
        """
        Enforces cooldown and hourly limits per phone number to prevent abuse.
        """
        now = time.time()

        # 1. Cooldown check: minimum 45 seconds between requests
        last_req = self._last_otp_request.get(phone, 0.0)
        cooldown_remaining = int(45 - (now - last_req))
        if cooldown_remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {cooldown_remaining} seconds before requesting a new OTP.",
            )

        # 2. Hourly check: maximum 6 requests per hour per phone
        timestamps = [t for t in self._hourly_requests.get(phone, []) if now - t < 3600]
        if len(timestamps) >= 6:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum OTP request limit reached for this number. Please try again in an hour.",
            )

        timestamps.append(now)
        self._hourly_requests[phone] = timestamps
        self._last_otp_request[phone] = now

    def request_otp(self, raw_phone: str) -> Dict[str, Any]:
        """
        Requests an OTP using Twilio Verify via WhatsApp channel.
        """
        phone = self.normalize_phone(raw_phone)
        self._check_rate_limits(phone)

        # Ensure Twilio credentials are configured
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.error("Twilio credentials missing in configuration.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication provider is not configured. Please contact administrator.",
            )

        service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        if not service_sid:
            logger.error("TWILIO_VERIFY_SERVICE_SID is missing in configuration.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Twilio Verify Service SID is not configured.",
            )

        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            verification = client.verify.v2.services(service_sid).verifications.create(
                to=phone,
                channel="whatsapp",
            )
            logger.info("Twilio Verify WhatsApp OTP requested for %s. Status: %s", phone, verification.status)
            # Reset verification failures counter on fresh OTP
            self._verify_failures.pop(phone, None)

            return {
                "status": verification.status or "pending",
                "phone_number": phone,
                "channel": "whatsapp",
                "cooldown_seconds": 45,
                "message": "Verification code dispatched via WhatsApp.",
            }

        except TwilioRestException as te:
            logger.warning("Twilio Verify error for %s (code %s): %s", phone, te.code, te.msg)
            # Safe user-friendly error translations
            if te.code == 21608:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Twilio Trial Account Restriction: WhatsApp messages can only be sent to verified caller IDs. "
                        f"Number '{phone}' is not verified on this Twilio account. Please add it to your Twilio console or upgrade account."
                    ),
                )
            elif te.code == 60200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid phone number format provided to verification service.",
                )
            elif te.code == 60203:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Maximum send attempts reached for this phone number. Please wait before retrying.",
                )
            elif te.code in (60228, 60212):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="WhatsApp channel delivery is pending sender approval on this Twilio Verify Service.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to deliver verification code: {te.msg}",
                )
        except Exception as e:
            logger.error("Unexpected failure requesting OTP for %s: %s", phone, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error requesting verification code.",
            )

    def verify_otp(self, raw_phone: str, code: str) -> Dict[str, Any]:
        """
        Verifies the code against Twilio Verify Verification Checks API.
        Creates or loads the User account upon successful verification and generates JWT token.
        """
        phone = self.normalize_phone(raw_phone)
        clean_code = (code or "").strip()

        if not clean_code or len(clean_code) < 4 or len(clean_code) > 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please enter a valid verification code.",
            )

        # Check maximum failed verification attempts (max 5)
        failures = self._verify_failures.get(phone, 0)
        if failures >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed verification attempts. Please request a new code.",
            )

        service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        if not service_sid:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Twilio Verify Service SID is not configured.",
            )

        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            verification_check = client.verify.v2.services(service_sid).verification_checks.create(
                to=phone,
                code=clean_code,
            )

            if verification_check.status != "approved":
                self._verify_failures[phone] = failures + 1
                logger.warning("OTP verification rejected for %s: status=%s", phone, verification_check.status)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired verification code.",
                )

        except TwilioRestException as te:
            logger.warning("Twilio verification check exception for %s: code=%s, msg=%s", phone, te.code, te.msg)
            if te.code == 20404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has expired or was not requested. Please request a new code.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification failed: {te.msg}",
            )

        # Clear failure counts on success
        self._verify_failures.pop(phone, None)

        # Look up or create user profile in UserRepository
        user = self.user_repo.get_by_phone(phone)
        is_new_user = False
        if not user:
            is_new_user = True
            user = User(
                user_id=f"usr_{uuid.uuid4().hex[:12]}",
                phone_number=phone,
                role=UserRole.CITIZEN,
                language="en",
            )
            self.user_repo.save_user(user)
            logger.info("New citizen registered via Twilio Verify: user_id=%s, phone=%s", user.user_id, phone)
        else:
            logger.info("Citizen logged in via Twilio Verify: user_id=%s, phone=%s", user.user_id, phone)

        # Generate JWT session token
        token = self.create_access_token(user)

        return {
            "access_token": token,
            "token_type": "bearer",
            "is_new_user": is_new_user,
            "user": user.model_dump(mode="json"),
        }

    def change_phone_number(self, current_user: User, new_raw_phone: str, code: str) -> Dict[str, Any]:
        """
        Updates the authenticated user's phone number after successful OTP verification.
        Preserves user_id, verification history, and all personal account records.
        """
        new_phone = self.normalize_phone(new_raw_phone)
        clean_code = (code or "").strip()

        if new_phone == current_user.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New phone number cannot be the same as the current phone number.",
            )

        # Check if the new phone is already registered to another account
        existing_user = self.user_repo.get_by_phone(new_phone)
        if existing_user and existing_user.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This phone number is already associated with another account.",
            )

        # Verify OTP on new phone via Twilio Verify
        service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            verification_check = client.verify.v2.services(service_sid).verification_checks.create(
                to=new_phone,
                code=clean_code,
            )
            if verification_check.status != "approved":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired verification code for the new phone number.",
                )
        except TwilioRestException as te:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification failed: {te.msg}",
            )

        # Update phone number in UserRepository while keeping user_id intact
        updated_user = self.user_repo.update_phone_number(current_user.user_id, new_phone)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile in database.",
            )

        logger.info(
            "User %s successfully updated login phone number from %s to %s",
            current_user.user_id,
            current_user.phone_number,
            new_phone,
        )

        new_token = self.create_access_token(updated_user)
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "user": updated_user.model_dump(mode="json"),
            "message": "Phone number updated successfully.",
        }

    def create_access_token(self, user: User) -> str:
        """
        Creates signed JWT access token valid for configured expiration days.
        """
        now = int(time.time())
        exp_seconds = getattr(settings, "JWT_EXPIRATION_DAYS", 7) * 86400
        payload = {
            "sub": user.user_id,
            "phone": user.phone_number,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "iat": now,
            "exp": now + exp_seconds,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"))

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decodes and validates JWT token.
        """
        try:
            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[getattr(settings, "JWT_ALGORITHM", "HS256")],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please sign in again.",
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials.",
            )

    def get_bot_display_number(self) -> Dict[str, Any]:
        """
        Returns the configured Twilio WhatsApp bot sender number and deep link.
        Never confuses the bot tipline number with the user's account identity.
        """
        raw = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886") or "whatsapp:+14155238886"
        clean = raw.replace("whatsapp:", "").strip()
        digits = re.sub(r"\D", "", clean)

        return {
            "raw": raw,
            "number": clean,
            "display": clean,
            "digits": digits,
            "deep_link": f"https://wa.me/{digits}?text=SatyaSetu%20Forward",
            "is_sandbox": "14155238886" in clean,
        }

    get_bot_number_info = get_bot_display_number

    def initiate_whatsapp_link(self, current_user: User) -> Dict[str, Any]:
        """
        Initiates WhatsApp account linking for the authenticated user.
        Generates a short-lived (10 min), single-use linking code.
        Requires that the incoming WhatsApp message is sent from the user's verified phone number.
        """
        if not current_user.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must have a verified login phone number to link WhatsApp.",
            )

        now = time.time()
        # Cooldown check: minimum 15 seconds between generating linking codes
        last_req = self._linking_cooldown.get(current_user.user_id, 0.0)
        if now - last_req < 15:
            remaining = int(15 - (now - last_req))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting a new linking code.",
            )

        # Invalidate any existing linking code for this user
        old_code = self._user_linking_tokens.get(current_user.user_id)
        if old_code:
            self._linking_tokens.pop(old_code, None)

        # Generate fresh single-use code: e.g. LINK-9A3F1B
        token_suffix = secrets.token_hex(3).upper()
        code = f"LINK-{token_suffix}"
        expires_at = now + 600.0  # 10 minutes

        self._linking_tokens[code] = {
            "code": code,
            "user_id": current_user.user_id,
            "phone_number": current_user.phone_number,
            "created_at": now,
            "expires_at": expires_at,
        }
        self._user_linking_tokens[current_user.user_id] = code
        self._linking_cooldown[current_user.user_id] = now

        bot_info = self.get_bot_display_number()
        link_text = f"LINK-{token_suffix}"
        encoded_text = f"{code}"

        return {
            "linking_code": code,
            "verified_phone_number": current_user.phone_number,
            "bot_number": bot_info["display"],
            "deep_link": f"https://wa.me/{bot_info['digits']}?text={encoded_text}",
            "expires_in_seconds": 600,
            "is_sandbox": bot_info["is_sandbox"],
            "instructions": (
                f"Send '{code}' to SatyaSetu Bot from your verified WhatsApp number "
                f"{current_user.phone_number} within 10 minutes to complete linking."
            ),
        }

    def get_whatsapp_link_status(self, current_user: User) -> Dict[str, Any]:
        """
        Returns authoritative verified phone number, WhatsApp link status, and bot tipline number.
        """
        # Re-fetch fresh user record from repository
        fresh_user = self.user_repo.get_user(current_user.user_id) or current_user
        bot_info = self.get_bot_display_number()

        # Check if user has an active linking token pending
        active_code = self._user_linking_tokens.get(fresh_user.user_id)
        active_token_info = None
        if active_code and active_code in self._linking_tokens:
            tok = self._linking_tokens[active_code]
            if time.time() < tok["expires_at"]:
                active_token_info = {
                    "code": tok["code"],
                    "expires_in_seconds": max(0, int(tok["expires_at"] - time.time())),
                    "deep_link": f"https://wa.me/{bot_info['digits']}?text={tok['code']}",
                }
            else:
                self._linking_tokens.pop(active_code, None)
                self._user_linking_tokens.pop(fresh_user.user_id, None)

        return {
            "user_id": fresh_user.user_id,
            "verified_login_number": fresh_user.phone_number,
            "phone_verified": getattr(fresh_user, "phone_verified", True),
            "whatsapp_account_identity": fresh_user.phone_number,
            "whatsapp_linked": getattr(fresh_user, "whatsapp_linked", False),
            "whatsapp_phone_number": getattr(fresh_user, "whatsapp_phone_number", None),
            "whatsapp_linked_at": (
                fresh_user.whatsapp_linked_at.isoformat()
                if getattr(fresh_user, "whatsapp_linked_at", None)
                else None
            ),
            "bot_tipline_number": bot_info["display"],
            "bot_deep_link": bot_info["deep_link"],
            "is_sandbox": bot_info["is_sandbox"],
            "pending_linking": active_token_info,
        }

    def validate_and_link_whatsapp(
        self,
        raw_code: str,
        incoming_from_number: str,
    ) -> Tuple[bool, Optional[User], str]:
        """
        Validates linking code submitted via WhatsApp bot incoming message.
        Confirms sender phone matches the authenticated user's verified phone number.
        """
        clean_code = (raw_code or "").strip().upper()
        if not clean_code or not clean_code.startswith("LINK-"):
            return False, None, "Invalid linking code format. Code must begin with LINK-."

        token_record = self._linking_tokens.get(clean_code)
        if not token_record:
            return False, None, "Linking code is invalid or has already been used."

        now = time.time()
        if now > token_record["expires_at"]:
            self._linking_tokens.pop(clean_code, None)
            self._user_linking_tokens.pop(token_record["user_id"], None)
            return False, None, "Linking code has expired. Please initiate a new link on SatyaSetu."

        # Normalize incoming WhatsApp sender to strict E.164
        clean_sender_raw = incoming_from_number.replace("whatsapp:", "").strip()
        try:
            normalized_sender = self.normalize_phone(clean_sender_raw)
        except Exception:
            normalized_sender = clean_sender_raw

        expected_phone = token_record["phone_number"]

        # SECURITY: Strictly ensure incoming sender matches the user's verified phone number
        if normalized_sender != expected_phone:
            logger.warning(
                "WhatsApp linking identity mismatch: token user expects %s, but message arrived from %s",
                expected_phone,
                normalized_sender,
            )
            return (
                False,
                None,
                f"Sender number '{normalized_sender}' does not match the account's verified login number '{expected_phone}'.",
            )

        # Successful match! Update user profile in repository
        user_id = token_record["user_id"]
        linked_at = datetime.now(timezone.utc)
        updated_user = self.user_repo.update_whatsapp_link(
            user_id=user_id,
            linked=True,
            whatsapp_phone=normalized_sender,
            linked_at=linked_at,
        )

        # Clean up token (single-use)
        self._linking_tokens.pop(clean_code, None)
        self._user_linking_tokens.pop(user_id, None)

        logger.info(
            "User %s successfully linked WhatsApp account with verified phone %s",
            user_id,
            normalized_sender,
        )
        return True, updated_user, "WhatsApp account successfully linked."

    def unlink_whatsapp(self, current_user: User) -> Dict[str, Any]:
        """
        Disconnects the user's linked WhatsApp account.
        """
        updated_user = self.user_repo.update_whatsapp_link(
            user_id=current_user.user_id,
            linked=False,
            whatsapp_phone=None,
            linked_at=None,
        )
        return {
            "success": True,
            "message": "WhatsApp account unlinked successfully.",
            "status": self.get_whatsapp_link_status(updated_user or current_user),
        }


auth_service = AuthService()

