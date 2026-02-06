"""Tests for user authentication GraphQL mutations."""

import json

import pytest
from graphene_django.utils.testing import GraphQLTestCase

from core.schema import schema


def get_user_model():
    """Lazy-load User model to avoid Django configuration issues at import time."""
    from django.contrib.auth import get_user_model as _get_user_model
    return _get_user_model()


@pytest.mark.django_db
class TestSignUp:
    """Test cases for user registration."""

    def test_signup_success(self, client):
        """Test successful user registration."""
        query = '''
            mutation {
                signUp(input: {
                    email: "newuser@example.com"
                    username: "newuser"
                    password: "SecurePass123!"
                    firstName: "New"
                    lastName: "User"
                }) {
                    success
                    errors
                    user {
                        id
                        email
                        username
                        firstName
                        lastName
                    }
                    token
                }
            }
        '''

        result = schema.execute(query)

        assert result.errors is None
        assert result.data['signUp']['success'] is True
        assert result.data['signUp']['errors'] is None
        assert result.data['signUp']['user']['email'] == 'newuser@example.com'
        assert result.data['signUp']['user']['username'] == 'newuser'
        assert result.data['signUp']['token'] is not None

        # Verify user was created in database
        User = get_user_model()
        assert User.objects.filter(email='newuser@example.com').exists()

    def test_signup_duplicate_email(self, client):
        """Test registration with duplicate email fails."""
        User = get_user_model()
        # Create existing user
        User.objects.create_user(
            email='existing@example.com',
            username='existinguser',
            password='TestPass123!'
        )

        query = '''
            mutation {
                signUp(input: {
                    email: "existing@example.com"
                    username: "newuser"
                    password: "TestPass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signUp']['success'] is False
        assert 'email already exists' in str(result.data['signUp']['errors']).lower()

    def test_signup_duplicate_username(self, client):
        """Test registration with duplicate username fails."""
        User = get_user_model()
        User.objects.create_user(
            email='existing@example.com',
            username='existinguser',
            password='TestPass123!'
        )

        query = '''
            mutation {
                signUp(input: {
                    email: "new@example.com"
                    username: "existinguser"
                    password: "SecurePass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signUp']['success'] is False
        assert 'username already exists' in str(result.data['signUp']['errors']).lower()

    def test_signup_weak_password(self, client):
        """Test registration with weak password fails."""
        query = '''
            mutation {
                signUp(input: {
                    email: "test@example.com"
                    username: "testuser"
                    password: "123"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signUp']['success'] is False
        assert result.data['signUp']['errors'] is not None
        assert len(result.data['signUp']['errors']) > 0

    def test_signup_invalid_email(self, client):
        """Test registration with invalid email fails."""
        query = '''
            mutation {
                signUp(input: {
                    email: "invalid-email"
                    username: "testuser"
                    password: "SecurePass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signUp']['success'] is False
        assert 'email' in str(result.data['signUp']['errors']).lower()

    def test_signup_invalid_username(self, client):
        """Test registration with invalid username fails."""
        query = '''
            mutation {
                signUp(input: {
                    email: "test@example.com"
                    username: "ab"
                    password: "SecurePass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signUp']['success'] is False
        assert 'username' in str(result.data['signUp']['errors']).lower()


@pytest.mark.django_db
class TestSignIn:
    """Test cases for user login."""

    def test_signin_success(self, client):
        """Test successful user login."""
        User = get_user_model()
        # Create user
        User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )

        query = '''
            mutation {
                signIn(input: {
                    email: "test@example.com"
                    password: "TestPass123!"
                }) {
                    success
                    errors
                    user {
                        email
                        username
                    }
                    token
                }
            }
        '''

        result = schema.execute(query)

        assert result.errors is None
        assert result.data['signIn']['success'] is True
        assert result.data['signIn']['errors'] is None
        assert result.data['signIn']['user']['email'] == 'test@example.com'
        assert result.data['signIn']['token'] is not None

    def test_signin_wrong_password(self, client):
        """Test login with wrong password fails."""
        User = get_user_model()
        User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )

        query = '''
            mutation {
                signIn(input: {
                    email: "test@example.com"
                    password: "WrongPassword!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signIn']['success'] is False
        assert 'invalid' in str(result.data['signIn']['errors']).lower()

    def test_signin_nonexistent_user(self, client):
        """Test login with nonexistent email fails."""
        query = '''
            mutation {
                signIn(input: {
                    email: "nonexistent@example.com"
                    password: "TestPass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signIn']['success'] is False
        assert 'invalid' in str(result.data['signIn']['errors']).lower()

    def test_signin_inactive_user(self, client):
        """Test login with inactive user fails."""
        User = get_user_model()
        user = User.objects.create_user(
            email='inactive@example.com',
            username='inactiveuser',
            password='TestPass123!'
        )
        user.is_active = False
        user.save()

        query = '''
            mutation {
                signIn(input: {
                    email: "inactive@example.com"
                    password: "TestPass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signIn']['success'] is False
        assert 'invalid' in str(result.data['signIn']['errors']).lower()


@pytest.mark.django_db
class TestMeQuery:
    """Test cases for the 'me' query."""

    def test_me_authenticated(self, client):
        """Test 'me' query returns current user when authenticated."""
        from unittest.mock import Mock

        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )

        query = '''
            query {
                me {
                    id
                    email
                    username
                    firstName
                    lastName
                }
            }
        '''

        # Create mock context with authenticated user
        context = Mock()
        context.user = user

        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['me']['email'] == 'test@example.com'
        assert result.data['me']['username'] == 'testuser'
        assert result.data['me']['firstName'] == 'Test'
        assert result.data['me']['lastName'] == 'User'

    def test_me_unauthenticated(self, client):
        """Test 'me' query fails when not authenticated."""
        from django.contrib.auth.models import AnonymousUser
        from unittest.mock import Mock

        query = '''
            query {
                me {
                    id
                    email
                }
            }
        '''

        context = Mock()
        context.user = AnonymousUser()

        result = schema.execute(query, context_value=context)

        # Should return error or None for unauthenticated user
        assert result.errors is not None or result.data['me'] is None
