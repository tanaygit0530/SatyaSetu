from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.schemas.core import User
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["User Authentication & Twilio Verify OTP"])


class RequestOtpInput(BaseModel):
    phone_number: str = Field(..., description="Mobile number with country code, e.g. +919820123456 or 10 digits")


class VerifyOtpInput(BaseModel):
    phone_number: str = Field(..., description="Mobile number with country code")
    code: str = Field(..., min_length=4, max_length=8, description="6-digit verification code received via WhatsApp")


class ChangePhoneRequestInput(BaseModel):
    new_phone_number: str = Field(..., description="New mobile number with country code")


class ChangePhoneVerifyInput(BaseModel):
    new_phone_number: str = Field(..., description="New mobile number with country code")
    code: str = Field(..., min_length=4, max_length=8, description="Verification code received on new number")


@router.post(
    "/request-otp",
    status_code=status.HTTP_200_OK,
    summary="Request verification OTP via Twilio Verify WhatsApp channel",
    description="Dispatches a 6-digit one-time password to the citizen's mobile number via Twilio Verify on WhatsApp.",
)
async def request_otp(payload: RequestOtpInput) -> Dict[str, Any]:
    return auth_service.request_otp(payload.phone_number)


@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    summary="Verify code and establish authenticated session",
    description="Validates OTP via Twilio Verify. On success, creates or loads the citizen account and returns a signed JWT access token.",
)
async def verify_otp(payload: VerifyOtpInput) -> Dict[str, Any]:
    return auth_service.verify_otp(payload.phone_number, payload.code)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated citizen profile",
    description="Returns verified user profile, assigned role, and account metadata.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {
        "user": current_user.model_dump(mode="json"),
    }


@router.post(
    "/change-phone/request-otp",
    status_code=status.HTTP_200_OK,
    summary="Request OTP to update login phone number",
    description="Sends Twilio Verify WhatsApp OTP to the new phone number for account update.",
)
async def change_phone_request_otp(
    payload: ChangePhoneRequestInput,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return auth_service.request_otp(payload.new_phone_number)


@router.post(
    "/change-phone/verify-otp",
    status_code=status.HTTP_200_OK,
    summary="Verify code and update login phone number",
    description="Confirms OTP and updates authenticated account phone number while preserving user_id, verification history, and analytics.",
)
async def change_phone_verify_otp(
    payload: ChangePhoneVerifyInput,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return auth_service.change_phone_number(current_user, payload.new_phone_number, payload.code)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Sign out user session",
    description="Terminates current session client-side.",
)
async def logout(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {"message": "Logged out successfully."}
