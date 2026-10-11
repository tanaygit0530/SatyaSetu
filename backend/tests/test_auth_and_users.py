from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.core import User, UserRole, Check, Input, VerificationResult
from app.schemas.enums import InputType, ProcessingStatus, Verdict, ConfidenceLevel
from app.services.auth_service import auth_service
from app.repositories.user_repository import UserRepository
from app.jobs import job_manager

client = TestClient(app)


def test_phone_normalization():
    assert auth_service.normalize_phone("+919820123456") == "+919820123456"
    assert auth_service.normalize_phone("9820123456") == "+919820123456"
    assert auth_service.normalize_phone("+1 415 555 2671") == "+14155552671"
    assert auth_service.normalize_phone(" +91-98201-23456 ") == "+919820123456"

    with pytest.raises(Exception):
        auth_service.normalize_phone("123")  # too short

    with pytest.raises(Exception):
        auth_service.normalize_phone("abcdefghijk")  # non-numeric


def test_auth_request_otp_invalid_number():
    res = client.post("/api/v1/auth/request-otp", json={"phone_number": "invalid"})
    assert res.status_code == 400


def test_auth_request_and_verify_otp_flow():
    test_phone = "+919999988888"

    # Mock Twilio client
    with patch("app.services.auth_service.Client") as mock_twilio_client:
        mock_instance = MagicMock()
        mock_twilio_client.return_value = mock_instance

        # 1. Mock Request OTP
        mock_verif = MagicMock()
        mock_verif.status = "pending"
        mock_instance.verify.v2.services.return_value.verifications.create.return_value = mock_verif

        req_res = client.post("/api/v1/auth/request-otp", json={"phone_number": test_phone})
        assert req_res.status_code == 200
        data = req_res.json()
        assert data["status"] == "pending"
        assert data["phone_number"] == test_phone

        # 2. Mock Verify OTP (invalid code)
        mock_bad_check = MagicMock()
        mock_bad_check.status = "canceled"
        mock_instance.verify.v2.services.return_value.verification_checks.create.return_value = mock_bad_check

        bad_res = client.post("/api/v1/auth/verify-otp", json={"phone_number": test_phone, "code": "000000"})
        assert bad_res.status_code == 400

        # 3. Mock Verify OTP (valid code)
        mock_good_check = MagicMock()
        mock_good_check.status = "approved"
        mock_instance.verify.v2.services.return_value.verification_checks.create.return_value = mock_good_check

        good_res = client.post("/api/v1/auth/verify-otp", json={"phone_number": test_phone, "code": "123456"})
        assert good_res.status_code == 200
        auth_data = good_res.json()
        assert "access_token" in auth_data
        assert auth_data["user"]["phone_number"] == test_phone
        token = auth_data["access_token"]

        # 4. Test /api/v1/auth/me with Bearer token
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["user"]["phone_number"] == test_phone
        user_id = me_data["user"]["user_id"]

        # 5. Test /api/v1/users/me/analytics (fresh user = clean zero state)
        analytics_res = client.get("/api/v1/users/me/analytics", headers={"Authorization": f"Bearer {token}"})
        assert analytics_res.status_code == 200
        an_data = analytics_res.json()
        assert an_data["totalChecks"] == 0
        assert an_data["verdictCounts"]["verified"] == 0

        # 6. Add a real check for this user and verify analytics update
        test_check = Check(
            check_id="chk_user_test_01",
            user_id=user_id,
            input=Input(input_id="inp_01", input_type=InputType.TEXT, raw_content="NPCI created UPI."),
            status=ProcessingStatus.COMPLETED,
            result=VerificationResult(
                check_id="chk_user_test_01",
                overall_verdict=Verdict.VERIFIED,
                summary="NPCI launched UPI in 2016.",
                confidence=ConfidenceLevel.HIGH,
            ),
        )
        job_manager.check_repo.create_check(test_check)

        # Re-fetch analytics
        an_updated = client.get("/api/v1/users/me/analytics", headers={"Authorization": f"Bearer {token}"}).json()
        assert an_updated["totalChecks"] == 1
        assert an_updated["verdictCounts"]["verified"] == 1
        assert len(an_updated["recentChecks"]) == 1
        assert an_updated["recentChecks"][0]["verdict"] == "VERIFIED"

        # 7. Test /api/v1/users/me/checks
        my_checks = client.get("/api/v1/users/me/checks", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(my_checks) == 1
        assert my_checks[0]["check_id"] == "chk_user_test_01"


def test_protected_routes_reject_unauthenticated():
    res1 = client.get("/api/v1/auth/me")
    assert res1.status_code == 401

    res2 = client.get("/api/v1/users/me/analytics")
    assert res2.status_code == 401

    res3 = client.get("/api/v1/users/me/checks")
    assert res3.status_code == 401


def test_root_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_whatsapp_linking_security_and_flow():
    # 1. Create authenticated user
    test_user = User(
        user_id="usr_whatsapp_test",
        phone_number="+918591000000",
        role=UserRole.CITIZEN,
    )
    auth_service.user_repo.save_user(test_user)
    token = auth_service.create_access_token(test_user)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial status (unlinked)
    status_res = client.get("/api/v1/auth/whatsapp/status", headers=headers)
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["verified_login_number"] == "+918591000000"
    assert st_data["whatsapp_account_identity"] == "+918591000000"
    assert st_data["whatsapp_linked"] is False
    assert "bot_tipline_number" in st_data

    # 3. Initiate linking (generates single-use short-lived token)
    init_res = client.post("/api/v1/auth/whatsapp/initiate-link", headers=headers)
    assert init_res.status_code == 200
    init_data = init_res.json()
    code = init_data["linking_code"]
    assert code.startswith("LINK-")
    assert init_data["verified_phone_number"] == "+918591000000"
    assert "deep_link" in init_data

    # 4. Attempt validation from WRONG sender (Security: User B cannot link User A's token)
    impostor_phone = "whatsapp:+919876543210"
    ok, usr, msg = auth_service.validate_and_link_whatsapp(code, impostor_phone)
    assert ok is False
    assert usr is None
    assert "does not match" in msg

    # Re-verify account is STILL not linked
    status_check = client.get("/api/v1/auth/whatsapp/status", headers=headers).json()
    assert status_check["whatsapp_linked"] is False

    # 5. Validate from CORRECT verified sender
    legit_phone = "whatsapp:+918591000000"
    ok2, usr2, msg2 = auth_service.validate_and_link_whatsapp(code, legit_phone)
    assert ok2 is True
    assert usr2 is not None
    assert usr2.whatsapp_linked is True
    assert usr2.whatsapp_phone_number == "+918591000000"

    # Status API now reports linked
    status_after = client.get("/api/v1/auth/whatsapp/status", headers=headers).json()
    assert status_after["whatsapp_linked"] is True
    assert status_after["whatsapp_phone_number"] == "+918591000000"
    assert status_after["whatsapp_account_identity"] == "+918591000000"

    # 6. Single-use token check (same code cannot be reused)
    ok3, usr3, msg3 = auth_service.validate_and_link_whatsapp(code, legit_phone)
    assert ok3 is False
    assert "already been used" in msg3 or "invalid" in msg3

    # 7. Unlink WhatsApp
    unlink_res = client.post("/api/v1/auth/whatsapp/unlink", headers=headers)
    assert unlink_res.status_code == 200
    assert unlink_res.json()["status"]["whatsapp_linked"] is False

    # 8. Re-link and test change_phone_number resets WhatsApp linking
    auth_service.user_repo.update_whatsapp_link("usr_whatsapp_test", linked=True, whatsapp_phone="+918591000000")
    updated_phone_user = auth_service.user_repo.update_phone_number("usr_whatsapp_test", "+918591111111")
    assert updated_phone_user.phone_number == "+918591111111"
    assert updated_phone_user.whatsapp_linked is False
    assert updated_phone_user.whatsapp_phone_number is None

