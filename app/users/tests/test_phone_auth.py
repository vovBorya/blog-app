"""Tests for passwordless phone authentication."""

import json

from django.core.cache import cache

import pytest

from users.models import PhoneSignupTicket
from users.verification import console_code_cache_key

PHONE = "+14155552671"
OTHER_PHONE = "+442071838750"


def get_user_model():
    """Lazy-load User model to avoid Django configuration issues at import time."""
    from django.contrib.auth import get_user_model as _get_user_model

    return _get_user_model()


def graphql(client, query, variables=None):
    """Post a GraphQL operation through the Django test client."""
    body = {"query": query}
    if variables is not None:
        body["variables"] = variables
    return client.post(
        "/graphql/",
        data=json.dumps(body),
        content_type="application/json",
        HTTP_HOST="localhost",
    )


REQUEST_CODE = """
    mutation Request($phone: String!) {
        requestPhoneCode(phone: $phone) {
            success
            errors
        }
    }
"""

VERIFY_CODE = """
    mutation Verify($phone: String!, $code: String!) {
        verifyPhoneCode(phone: $phone, code: $code) {
            success
            errors
            status
            signupToken
            token
            user {
                username
                email
                phone
            }
        }
    }
"""

COMPLETE_SIGN_UP = """
    mutation Complete($input: CompletePhoneSignUpInput!) {
        completePhoneSignUp(input: $input) {
            success
            errors
            token
            user {
                username
                email
                phone
            }
        }
    }
"""


@pytest.fixture(autouse=True)
def use_console_sms(settings):
    """Keep phone tests on the log-only sender."""
    settings.SMS_BACKEND = "console"


@pytest.fixture(autouse=True)
def clear_phone_cache():
    """Drop cached codes so tests do not share a cooldown or OTP."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def forbid_twilio(monkeypatch):
    """Phone tests stay on the console backend and must not call Twilio."""

    def fail(self, phone_e164, code=None):
        raise AssertionError("Twilio should not be called")

    monkeypatch.setattr("users.verification.TwilioVerificationBackend.send_code", fail)
    monkeypatch.setattr("users.verification.TwilioVerificationBackend.check_code", fail)


def request_code(client, phone=PHONE):
    """Send a code and return the 6-digit value stored by the console backend."""
    response = graphql(client, REQUEST_CODE, {"phone": phone})
    payload = response.json()["data"]["requestPhoneCode"]
    assert payload["success"] is True, payload
    code = cache.get(console_code_cache_key(phone))
    assert code
    return code


@pytest.mark.django_db
class TestPhoneAuth:
    """Console-backend coverage for send, verify, and phone signup."""

    def test_invalid_phone_number(self, client):
        """A number that is not valid E.164 is rejected before a code is stored."""
        response = graphql(client, REQUEST_CODE, {"phone": "123"})
        payload = response.json()["data"]["requestPhoneCode"]

        assert payload["success"] is False
        assert "valid phone" in payload["errors"][0].lower()
        assert cache.get(console_code_cache_key("123")) is None

    def test_send_cooldown(self, client):
        """A second send for the same number is refused inside the cooldown."""
        code = request_code(client)
        response = graphql(client, REQUEST_CODE, {"phone": PHONE})
        payload = response.json()["data"]["requestPhoneCode"]

        assert payload["success"] is False
        assert "wait" in payload["errors"][0].lower()
        assert cache.get(console_code_cache_key(PHONE)) == code

    def test_wrong_code_does_not_set_cookie(self, client):
        """A wrong code is rejected and does not start a session."""
        code = request_code(client)
        wrong = "000000" if code != "000000" else "111111"
        response = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": wrong})
        payload = response.json()["data"]["verifyPhoneCode"]

        assert payload["success"] is False
        assert "invalid" in payload["errors"][0].lower()
        assert payload["signupToken"] is None
        assert "JWT" not in response.cookies
        assert PhoneSignupTicket.objects.count() == 0

    def test_existing_user_signs_in_with_cookie(self, client):
        """A known phone number receives an HttpOnly cookie and no token body."""
        User = get_user_model()
        user = User(username="phoneuser", email=None, phone=PHONE, first_name="Phone")
        user.set_unusable_password()
        user.save()
        code = request_code(client)

        response = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": code})
        payload = response.json()["data"]["verifyPhoneCode"]

        assert response.status_code == 200
        assert payload["success"] is True
        assert payload["status"] == "AUTHENTICATED"
        assert payload["token"] is None
        assert payload["signupToken"] is None
        assert payload["user"]["username"] == "phoneuser"
        assert payload["user"]["email"] is None
        assert "JWT" in response.cookies
        assert response.cookies["JWT"].value
        assert response.cookies["JWT"]["httponly"]
        assert not user.has_usable_password()

    def test_new_number_needs_username(self, client):
        """An unknown number returns a signup token and does not set a cookie."""
        code = request_code(client)
        response = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": code})
        payload = response.json()["data"]["verifyPhoneCode"]

        assert payload["success"] is True
        assert payload["status"] == "NEEDS_USERNAME"
        assert payload["signupToken"]
        assert payload["user"] is None
        assert payload["token"] is None
        assert "JWT" not in response.cookies
        assert PhoneSignupTicket.objects.count() == 1

    def test_complete_signup_creates_passwordless_user(self, client):
        """Completing signup stores a null email, an unusable password, and a cookie."""
        User = get_user_model()
        User.objects.create_user(
            username="already",
            email=None,
            password=None,
            phone=OTHER_PHONE,
        )
        code = request_code(client)
        verified = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": code})
        signup_token = verified.json()["data"]["verifyPhoneCode"]["signupToken"]

        response = graphql(
            client,
            COMPLETE_SIGN_UP,
            {
                "input": {
                    "signupToken": signup_token,
                    "username": "newphone",
                    "firstName": "New",
                    "lastName": "Phone",
                }
            },
        )
        payload = response.json()["data"]["completePhoneSignUp"]
        user = User.objects.get(username="newphone")

        assert payload["success"] is True
        assert payload["errors"] is None
        assert payload["token"] is None
        assert payload["user"]["email"] is None
        assert payload["user"]["phone"] == PHONE
        assert user.email is None
        assert user.phone == PHONE
        assert user.first_name == "New"
        assert not user.has_usable_password()
        assert "JWT" in response.cookies
        assert response.cookies["JWT"]["httponly"]
        assert User.objects.filter(email__isnull=True).count() == 2

    def test_reused_ticket_is_rejected(self, client):
        """A signup token cannot create a second account."""
        User = get_user_model()
        code = request_code(client)
        verified = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": code})
        signup_token = verified.json()["data"]["verifyPhoneCode"]["signupToken"]
        variables = {
            "input": {
                "signupToken": signup_token,
                "username": "newphone",
            }
        }

        first = graphql(client, COMPLETE_SIGN_UP, variables)
        second = graphql(
            client,
            COMPLETE_SIGN_UP,
            {"input": {"signupToken": signup_token, "username": "another"}},
        )

        assert first.json()["data"]["completePhoneSignUp"]["success"] is True
        second_payload = second.json()["data"]["completePhoneSignUp"]
        assert second_payload["success"] is False
        assert "expired" in second_payload["errors"][0].lower()
        assert User.objects.filter(phone=PHONE).count() == 1
        assert "JWT" not in second.cookies

    def test_inactive_user_is_rejected(self, client):
        """A deactivated phone account does not get a session or a signup ticket."""
        User = get_user_model()
        user = User.objects.create_user(
            username="inactivephone",
            email="inactive-phone@example.com",
            password="TestPass123!",
            phone=PHONE,
        )
        user.is_active = False
        user.save()
        code = request_code(client)

        response = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": code})
        payload = response.json()["data"]["verifyPhoneCode"]

        assert payload["success"] is False
        assert "deactivated" in payload["errors"][0].lower()
        assert payload["signupToken"] is None
        assert PhoneSignupTicket.objects.count() == 0
        assert "JWT" not in response.cookies

    def test_taken_username_keeps_ticket(self, client):
        """A conflicting username does not consume the signup token."""
        User = get_user_model()
        User.objects.create_user(
            username="taken",
            email="taken@example.com",
            password="TestPass123!",
        )
        code = request_code(client)
        verified = graphql(client, VERIFY_CODE, {"phone": PHONE, "code": code})
        signup_token = verified.json()["data"]["verifyPhoneCode"]["signupToken"]

        rejected = graphql(
            client,
            COMPLETE_SIGN_UP,
            {"input": {"signupToken": signup_token, "username": "taken"}},
        )
        created = graphql(
            client,
            COMPLETE_SIGN_UP,
            {"input": {"signupToken": signup_token, "username": "available"}},
        )

        assert rejected.json()["data"]["completePhoneSignUp"]["success"] is False
        assert created.json()["data"]["completePhoneSignUp"]["success"] is True
        assert User.objects.get(username="available").phone == PHONE
