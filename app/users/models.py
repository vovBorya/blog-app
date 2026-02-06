"""
Custom User model for the blog application.

Extends Django's AbstractUser to add custom fields and methods.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


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
        'email address',
        unique=True,
        error_messages={
            'unique': 'A user with that email already exists.',
        },
    )
    
    # Additional fields can be added here
    bio = models.TextField(
        'biography',
        max_length=500,
        blank=True,
        help_text='A short bio about the user.'
    )
    
    avatar_url = models.URLField(
        'avatar URL',
        max_length=500,
        blank=True,
        null=True,
        help_text='URL to the user avatar image.'
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.username
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.username
