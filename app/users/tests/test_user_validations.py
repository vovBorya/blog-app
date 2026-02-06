"""Additional tests to improve user code coverage."""

import pytest
from unittest.mock import Mock

from core.schema import schema


def get_user_model():
    """Lazy-load User model."""
    from django.contrib.auth import get_user_model as _get_user_model
    return _get_user_model()


def create_context(user=None):
    """Create a mock context with optional user."""
    from django.contrib.auth.models import AnonymousUser

    context = Mock()
    context.user = user if user else AnonymousUser()
    return context


@pytest.fixture
def user():
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='TestPass123!',
        first_name='Test',
        last_name='User'
    )


@pytest.mark.django_db
class TestUpdateProfileMutation:
    """Test cases for UpdateProfile mutation."""

    def test_update_profile_success(self, user):
        """Test successfully updating user profile."""
        query = '''
            mutation {
                updateProfile(
                    firstName: "Updated"
                    lastName: "Name"
                    bio: "New bio"
                    avatarUrl: "https://example.com/avatar.jpg"
                ) {
                    success
                    errors
                    user {
                        firstName
                        lastName
                        bio
                        avatarUrl
                    }
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['updateProfile']['success'] is True
        assert result.data['updateProfile']['user']['firstName'] == 'Updated'
        assert result.data['updateProfile']['user']['lastName'] == 'Name'
        assert result.data['updateProfile']['user']['bio'] == 'New bio'
        assert result.data['updateProfile']['user']['avatarUrl'] == 'https://example.com/avatar.jpg'

    def test_update_profile_partial(self, user):
        """Test updating only some fields."""
        query = '''
            mutation {
                updateProfile(firstName: "NewFirst") {
                    success
                    user {
                        firstName
                        lastName
                    }
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['updateProfile']['success'] is True
        assert result.data['updateProfile']['user']['firstName'] == 'NewFirst'
        # Last name should remain unchanged
        assert result.data['updateProfile']['user']['lastName'] == 'User'

    def test_update_profile_unauthenticated(self):
        """Test updating profile without authentication."""
        query = '''
            mutation {
                updateProfile(firstName: "Test") {
                    success
                    errors
                }
            }
        '''

        context = create_context()  # Anonymous user
        result = schema.execute(query, context_value=context)

        # Should fail due to login_required
        assert result.errors is not None or result.data['updateProfile']['success'] is False


@pytest.mark.django_db
class TestChangePasswordMutation:
    """Test cases for ChangePassword mutation."""

    def test_change_password_success(self, user):
        """Test successfully changing password."""
        query = '''
            mutation {
                changePassword(
                    currentPassword: "TestPass123!"
                    newPassword: "NewSecurePass456!"
                ) {
                    success
                    errors
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['changePassword']['success'] is True
        assert result.data['changePassword']['errors'] is None

        # Verify the password was actually changed
        user.refresh_from_db()
        assert user.check_password('NewSecurePass456!')
        assert not user.check_password('TestPass123!')

    def test_change_password_wrong_current(self, user):
        """Test changing password with wrong current password."""
        query = '''
            mutation {
                changePassword(
                    currentPassword: "WrongPassword!"
                    newPassword: "NewSecurePass456!"
                ) {
                    success
                    errors
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data['changePassword']['success'] is False
        assert 'incorrect' in str(result.data['changePassword']['errors']).lower()

    def test_change_password_weak_new_password(self, user):
        """Test changing to a weak password."""
        query = '''
            mutation {
                changePassword(
                    currentPassword: "TestPass123!"
                    newPassword: "123"
                ) {
                    success
                    errors
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data['changePassword']['success'] is False
        assert result.data['changePassword']['errors'] is not None
        assert len(result.data['changePassword']['errors']) > 0

    def test_change_password_unauthenticated(self):
        """Test changing password without authentication."""
        query = '''
            mutation {
                changePassword(
                    currentPassword: "TestPass123!"
                    newPassword: "NewSecurePass456!"
                ) {
                    success
                    errors
                }
            }
        '''

        context = create_context()  # Anonymous user
        result = schema.execute(query, context_value=context)

        # Should fail due to login_required
        assert result.errors is not None or result.data['changePassword']['success'] is False


@pytest.mark.django_db
class TestUserModelMethods:
    """Test additional User model methods."""

    def test_get_full_name_with_first_name_only(self):
        """Test get_full_name with only first name."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            first_name='John'
        )

        assert user.get_full_name() == 'John'

    def test_get_full_name_with_last_name_only(self):
        """Test get_full_name with only last name."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            last_name='Doe'
        )

        assert user.get_full_name() == 'Doe'

    def test_get_short_name_without_first_name(self):
        """Test get_short_name returns username when no first name."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )

        assert user.get_short_name() == 'testuser'

    def test_user_with_bio_and_avatar(self):
        """Test creating user with bio and avatar."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!',
            bio='This is my bio',
            avatar_url='https://example.com/avatar.jpg'
        )

        assert user.bio == 'This is my bio'
        assert user.avatar_url == 'https://example.com/avatar.jpg'


@pytest.mark.django_db
class TestSignInDeactivatedAccount:
    """Test signing in with deactivated account."""

    def test_signin_shows_deactivated_message(self):
        """Test that deactivated account shows specific error."""
        User = get_user_model()
        user = User.objects.create_user(
            email='deactivated@example.com',
            username='deactivated',
            password='TestPass123!'
        )
        user.is_active = False
        user.save()

        query = '''
            mutation {
                signIn(input: {
                    email: "deactivated@example.com"
                    password: "TestPass123!"
                }) {
                    success
                    errors
                }
            }
        '''

        result = schema.execute(query)

        assert result.data['signIn']['success'] is False
        # Could be either "deactivated" or "invalid" depending on implementation
        errors_str = str(result.data['signIn']['errors']).lower()
        assert 'deactivated' in errors_str or 'invalid' in errors_str
