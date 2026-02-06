"""Tests for the User model."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test cases for the User model."""
    
    def test_create_user(self):
        """Test creating a user with valid data."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        
        assert user.email == 'test@example.com'
        assert user.username == 'testuser'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password('TestPass123!')
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='AdminPass123!'
        )
        
        assert admin.email == 'admin@example.com'
        assert admin.is_active
        assert admin.is_staff
        assert admin.is_superuser
    
    def test_user_str_method(self):
        """Test the string representation of a user."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        assert str(user) == 'test@example.com'
    
    def test_user_get_full_name(self):
        """Test get_full_name method."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='John',
            last_name='Doe'
        )
        
        assert user.get_full_name() == 'John Doe'
    
    def test_user_get_full_name_without_names(self):
        """Test get_full_name returns username when no names set."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        assert user.get_full_name() == 'testuser'
    
    def test_user_get_short_name(self):
        """Test get_short_name method."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='John'
        )
        
        assert user.get_short_name() == 'John'
    
    def test_user_email_unique(self):
        """Test that email must be unique."""
        User.objects.create_user(
            email='test@example.com',
            username='testuser1',
            password='TestPass123!'
        )
        
        with pytest.raises(Exception):
            User.objects.create_user(
                email='test@example.com',
                username='testuser2',
                password='TestPass123!'
            )
    
    def test_user_username_unique(self):
        """Test that username must be unique."""
        User.objects.create_user(
            email='test1@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        with pytest.raises(Exception):
            User.objects.create_user(
                email='test2@example.com',
                username='testuser',
                password='TestPass123!'
            )
