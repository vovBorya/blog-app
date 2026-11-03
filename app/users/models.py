"""
Custom User model for the blog application.

Extends Django's AbstractUser to add custom fields and methods.
"""

import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model with email as a required unique field.

    Attributes:
        email: Unique email address (required for authentication)
        username: Unique username
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the user account is active
        is_staff: Whether the user can access admin site
        date_joined: When the user account was created
    """

    email = models.EmailField(
        "email address",
        unique=True,
        blank=True,
        null=True,
        error_messages={
            "unique": "A user with that email already exists.",
        },
    )

    phone = models.CharField(
        "phone number",
        max_length=16,
        unique=True,
        blank=True,
        null=True,
        help_text="Phone number in E.164 format.",
    )

    # Additional fields can be added here
    bio = models.TextField(
        "biography", max_length=500, blank=True, help_text="A short bio about the user."
    )

    avatar_url = models.URLField(
        "avatar URL",
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to the user avatar image.",
    )

    about_me = models.TextField(
        "about me",
        blank=True,
        help_text="Extended information about the user.",
    )

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["phone"], name="users_phone_e164_idx"),
        ]

    def save(self, *args, **kwargs):
        """Store blank email and phone as NULL so multiple phone-only users are allowed."""
        if not self.email:
            self.email = None
        if not self.phone:
            self.phone = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email or self.phone or self.username

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.username


class PasswordResetToken(models.Model):
    """
    Model for storing password reset tokens.

    Tokens are valid for 24 hours and can only be used once.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        help_text="User requesting password reset",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique token for password reset",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the token was created")
    expires_at = models.DateTimeField(help_text="When the token expires")
    used_at = models.DateTimeField(null=True, blank=True, help_text="When the token was used")
    is_active = models.BooleanField(default=True, help_text="Whether the token is still active")

    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"Password reset token for {self.user}"

    def save(self, *args, **kwargs):
        """Override save to generate token and set expiration."""
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if token is valid (not expired and not used)."""
        return self.is_active and self.used_at is None and timezone.now() < self.expires_at

    def mark_as_used(self):
        """Mark token as used."""
        self.used_at = timezone.now()
        self.is_active = False
        self.save()


class PhoneSignupTicket(models.Model):
    """
    Single-use proof that a phone number passed SMS verification.

    Issued when the code is accepted and no user exists yet. The raw token is
    returned once; only its SHA-256 hash is stored.
    """

    phone = models.CharField(max_length=16, help_text="Verified phone number in E.164 format.")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phone_signup_tickets"
        verbose_name = "Phone Signup Ticket"
        verbose_name_plural = "Phone Signup Tickets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone"], name="phone_signup_phone_idx"),
        ]

    def __str__(self):
        return f"Phone signup ticket for {self.phone}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Return whether this ticket can still create an account."""
        return self.used_at is None and timezone.now() < self.expires_at

    def mark_as_used(self):
        """Consume the ticket so it cannot create another account."""
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    @staticmethod
    def hash_token(raw_token):
        """Return the SHA-256 hex digest of a signup token."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, phone):
        """Invalidate unused tickets for this phone and return a new raw token."""
        raw_token = secrets.token_urlsafe(32)
        now = timezone.now()
        cls.objects.filter(phone=phone, used_at__isnull=True).update(used_at=now)
        cls.objects.create(
            phone=phone,
            token_hash=cls.hash_token(raw_token),
            expires_at=now + timedelta(minutes=10),
        )
        return raw_token
