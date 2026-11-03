"""SMS verification backends for passwordless phone sign-in."""

import logging
import re
import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

import phonenumbers

logger = logging.getLogger(__name__)

CODE_TTL_SECONDS = 10 * 60
MAX_ATTEMPTS = 5
SEND_COOLDOWN_SECONDS = 60
_CODE_DIGITS = re.compile(r"^\d{6}$")


class PhoneVerificationError(Exception):
    """A phone number or verification code was rejected."""


class DeliveryError(PhoneVerificationError):
    """The SMS provider could not send a code."""


def normalize_phone(value):
    """Return a valid phone number in E.164, or raise PhoneVerificationError."""
    raw = (value or "").strip()
    if not raw:
        raise PhoneVerificationError("Enter a valid phone number.")
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.NumberParseException as exc:
        raise PhoneVerificationError("Enter a valid phone number.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise PhoneVerificationError("Enter a valid phone number.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def console_code_cache_key(phone_e164):
    """Cache key for a console-backend verification code."""
    return f"phone-otp:{phone_e164}"


def _attempts_cache_key(phone_e164):
    return f"phone-otp-attempts:{phone_e164}"


def _cooldown_cache_key(phone_e164):
    return f"phone-otp-cooldown:{phone_e164}"


def send_cooldown_active(phone_e164):
    """Return whether this number must wait before another code is sent."""
    return cache.get(_cooldown_cache_key(phone_e164)) is not None


def mark_send_cooldown(phone_e164):
    """Start the per-number send cooldown."""
    cache.set(_cooldown_cache_key(phone_e164), 1, SEND_COOLDOWN_SECONDS)


class ConsoleVerificationBackend:
    """Print a 6-digit code to the logs and check it from the cache."""

    def send_code(self, phone_e164):
        code = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(console_code_cache_key(phone_e164), code, CODE_TTL_SECONDS)
        cache.set(_attempts_cache_key(phone_e164), 0, CODE_TTL_SECONDS)
        logger.info("Phone verification code for %s is %s", phone_e164, code)

    def check_code(self, phone_e164, code):
        stored = cache.get(console_code_cache_key(phone_e164))
        if stored is None:
            return False

        attempts = cache.get(_attempts_cache_key(phone_e164), 0)
        if attempts >= MAX_ATTEMPTS:
            cache.delete(console_code_cache_key(phone_e164))
            cache.delete(_attempts_cache_key(phone_e164))
            return False

        submitted = (code or "").strip()
        matches = _CODE_DIGITS.fullmatch(submitted) and secrets.compare_digest(
            str(stored), submitted
        )
        if not matches:
            cache.set(_attempts_cache_key(phone_e164), attempts + 1, CODE_TTL_SECONDS)
            return False

        cache.delete(console_code_cache_key(phone_e164))
        cache.delete(_attempts_cache_key(phone_e164))
        return True


class TwilioVerificationBackend:
    """Send and check codes with Twilio Verify."""

    def send_code(self, phone_e164):
        try:
            client = self._client()
            client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
                to=phone_e164,
                channel="sms",
            )
        except PhoneVerificationError:
            raise
        except Exception as exc:
            logger.exception("Twilio Verify send failed")
            raise DeliveryError("Could not send a verification code.") from exc

    def check_code(self, phone_e164, code):
        try:
            client = self._client()
            result = client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verification_checks.create(to=phone_e164, code=(code or "").strip())
        except Exception:
            logger.exception("Twilio Verify check failed")
            return False
        return result.status == "approved"

    def _client(self):
        if not (
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_VERIFY_SERVICE_SID
        ):
            raise DeliveryError("Could not send a verification code.")
        from twilio.rest import Client

        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def get_verification_backend():
    """Return the backend selected by SMS_BACKEND."""
    backend = settings.SMS_BACKEND
    if backend == "twilio":
        return TwilioVerificationBackend()
    if backend == "console":
        return ConsoleVerificationBackend()
    raise ImproperlyConfigured(f"Unknown SMS_BACKEND: {backend}")
