"""GraphQL mutations for user authentication."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest

import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required

from users.models import PhoneSignupTicket
from users.verification import (
    DeliveryError,
    PhoneVerificationError,
    get_verification_backend,
    mark_send_cooldown,
    normalize_phone,
    send_cooldown_active,
)

from .types import UserType

User = get_user_model()


def _stash_jwt_cookie(info, token):
    """Attach the JWT to the Django request for the HttpOnly cookie wrapper.

    ``schema.execute`` has no request, so that path skips the assignment and the
    token stays out of the JSON body either way.
    """
    context = getattr(info, "context", None)
    if isinstance(context, HttpRequest):
        context.jwt_token = token


class SignUpInput(graphene.InputObjectType):
    """Input type for user registration."""

    email = graphene.String(required=True, description="User email address")
    username = graphene.String(required=True, description="Unique username")
    password = graphene.String(required=True, description="User password")
    first_name = graphene.String(description="User first name")
    last_name = graphene.String(description="User last name")


class SignUp(graphene.Mutation):
    """
    User registration mutation.

    Creates a new user account and sets an HttpOnly JWT cookie.
    The token is not returned in the response body.
    """

    class Arguments:
        input = SignUpInput(required=True)

    user = graphene.Field(UserType)
    token = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        errors = []

        # Validate email format
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, input.email):
            errors.append("Invalid email format.")

        # Check if email already exists
        if User.objects.filter(email=input.email).exists():
            errors.append("A user with this email already exists.")

        # Check if username already exists
        if User.objects.filter(username=input.username).exists():
            errors.append("A user with this username already exists.")

        # Validate username format (alphanumeric, underscore, hyphen)
        username_regex = r"^[a-zA-Z0-9_-]{3,30}$"
        if not re.match(username_regex, input.username):
            errors.append(
                "Username must be 3-30 characters and contain only "
                "letters, numbers, underscores, and hyphens."
            )

        # Validate password strength
        try:
            validate_password(input.password)
        except ValidationError as e:
            errors.extend(list(e.messages))

        if errors:
            return SignUp(user=None, token=None, success=False, errors=errors)

        # Create the user
        user = User.objects.create_user(
            email=input.email,
            username=input.username,
            password=input.password,
            first_name=input.get("first_name", ""),
            last_name=input.get("last_name", ""),
        )

        # Generate JWT token
        from graphql_jwt.shortcuts import get_token

        token = get_token(user)
        _stash_jwt_cookie(info, token)

        return SignUp(user=user, token=None, success=True, errors=None)


class SignInInput(graphene.InputObjectType):
    """Input type for user login."""

    email = graphene.String(required=True, description="User email address")
    password = graphene.String(required=True, description="User password")


class SignIn(graphene.Mutation):
    """
    User login mutation.

    Authenticates user credentials and sets an HttpOnly JWT cookie.
    The token is not returned in the response body.
    """

    class Arguments:
        input = SignInInput(required=True)

    user = graphene.Field(UserType)
    token = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        from django.contrib.auth import authenticate

        # Try to find user by email
        try:
            user_obj = User.objects.get(email=input.email)
            username = user_obj.username
        except User.DoesNotExist:
            return SignIn(
                user=None,
                token=None,
                success=False,
                errors=["Invalid email or password."],
            )

        # Authenticate user
        user = authenticate(username=username, password=input.password)

        if user is None:
            return SignIn(
                user=None,
                token=None,
                success=False,
                errors=["Invalid email or password."],
            )

        if not user.is_active:
            return SignIn(
                user=None,
                token=None,
                success=False,
                errors=["This account has been deactivated."],
            )

        # Generate JWT token
        from graphql_jwt.shortcuts import get_token

        token = get_token(user)
        _stash_jwt_cookie(info, token)

        return SignIn(user=user, token=None, success=True, errors=None)


class UpdateProfile(graphene.Mutation):
    """
    Update current user's profile information.

    Requires authentication.
    """

    class Arguments:
        first_name = graphene.String(description="User first name")
        last_name = graphene.String(description="User last name")
        bio = graphene.String(description="User biography")
        avatar_url = graphene.String(description="Avatar URL")

    user = graphene.Field(UserType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    @login_required
    def mutate(cls, root, info, **kwargs):
        user = info.context.user

        # Update fields if provided
        if "first_name" in kwargs and kwargs["first_name"] is not None:
            user.first_name = kwargs["first_name"]

        if "last_name" in kwargs and kwargs["last_name"] is not None:
            user.last_name = kwargs["last_name"]

        if "bio" in kwargs and kwargs["bio"] is not None:
            user.bio = kwargs["bio"]

        if "avatar_url" in kwargs and kwargs["avatar_url"] is not None:
            user.avatar_url = kwargs["avatar_url"]

        try:
            user.save()
            return UpdateProfile(user=user, success=True, errors=None)
        except Exception as e:
            return UpdateProfile(user=None, success=False, errors=[str(e)])


class ChangePassword(graphene.Mutation):
    """
    Change the current user's password.

    Requires authentication and the current password.
    """

    class Arguments:
        current_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    @login_required
    def mutate(cls, root, info, current_password, new_password):
        user = info.context.user

        # Verify current password
        if not user.check_password(current_password):
            return ChangePassword(success=False, errors=["Current password is incorrect."])

        # Validate new password
        errors = []
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            errors.extend(list(e.messages))

        if errors:
            return ChangePassword(success=False, errors=errors)

        # Set new password
        user.set_password(new_password)
        user.save()

        return ChangePassword(success=True, errors=None)


class RequestPasswordResetInput(graphene.InputObjectType):
    """Input type for requesting password reset."""

    email = graphene.String(required=True, description="User email address")


class RequestPasswordReset(graphene.Mutation):
    """
    Request a password reset token.

    Sends an email with a password reset link to the user.
    """

    class Arguments:
        input = RequestPasswordResetInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        from django.conf import settings
        from django.core.mail import send_mail

        from ..models import PasswordResetToken

        try:
            user = User.objects.get(email=input.email)
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            return RequestPasswordReset(
                success=True,
                message=(
                    "If an account with this email exists, " "a password reset link has been sent."
                ),
                errors=None,
            )

        # Deactivate any existing active tokens for this user
        PasswordResetToken.objects.filter(user=user, is_active=True).update(is_active=False)

        # Create new token
        reset_token = PasswordResetToken.objects.create(user=user)

        # Send email
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token.token}"

        try:
            send_mail(
                subject="Password Reset Request",
                message=f"Hello {user.get_full_name()},\n\n"
                f"You requested a password reset. Click the link below to reset your password:\n\n"
                f"{reset_url}\n\n"
                f"This link will expire in 24 hours.\n\n"
                f"If you didn't request this, please ignore this email.\n\n"
                f"Best regards,\nThe Blog Team",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return RequestPasswordReset(
                success=False,
                message=None,
                errors=[f"Failed to send email: {str(e)}"],
            )

        return RequestPasswordReset(
            success=True,
            message="If an account with this email exists, a password reset link has been sent.",
            errors=None,
        )


class ConfirmPasswordResetInput(graphene.InputObjectType):
    """Input type for confirming password reset."""

    token = graphene.String(required=True, description="Password reset token")
    new_password = graphene.String(required=True, description="New password")


class ConfirmPasswordReset(graphene.Mutation):
    """
    Confirm password reset with token.

    Validates the token and sets a new password for the user.
    """

    class Arguments:
        input = ConfirmPasswordResetInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        from ..models import PasswordResetToken

        try:
            reset_token = PasswordResetToken.objects.get(token=input.token)
        except PasswordResetToken.DoesNotExist:
            return ConfirmPasswordReset(
                success=False, message=None, errors=["Invalid or expired token."]
            )

        # Validate token
        if not reset_token.is_valid():
            return ConfirmPasswordReset(
                success=False, message=None, errors=["Invalid or expired token."]
            )

        # Validate new password
        errors = []
        try:
            validate_password(input.new_password, user=reset_token.user)
        except ValidationError as e:
            errors.extend(list(e.messages))

        if errors:
            return ConfirmPasswordReset(success=False, message=None, errors=errors)

        # Set new password
        reset_token.user.set_password(input.new_password)
        reset_token.user.save()

        # Mark token as used
        reset_token.mark_as_used()

        return ConfirmPasswordReset(
            success=True,
            message="Password has been reset successfully.",
            errors=None,
        )


class PhoneAuthStatus(graphene.Enum):
    """Result of checking a phone verification code."""

    AUTHENTICATED = "authenticated"
    NEEDS_USERNAME = "needs_username"


class RequestPhoneCode(graphene.Mutation):
    """Send a verification code without revealing whether the number is registered."""

    class Arguments:
        phone = graphene.String(required=True, description="Phone number, preferably E.164")

    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, phone):
        try:
            normalized = normalize_phone(phone)
        except PhoneVerificationError as exc:
            return RequestPhoneCode(success=False, errors=[str(exc)])

        if send_cooldown_active(normalized):
            return RequestPhoneCode(
                success=False,
                errors=["Please wait before requesting another code."],
            )

        try:
            get_verification_backend().send_code(normalized)
        except DeliveryError:
            return RequestPhoneCode(
                success=False,
                errors=["Could not send a verification code."],
            )

        mark_send_cooldown(normalized)
        return RequestPhoneCode(success=True, errors=None)


class VerifyPhoneCode(graphene.Mutation):
    """
    Check a verification code.

    An existing active user is signed in. A new number receives a single-use
    signup token and no session cookie.
    """

    class Arguments:
        phone = graphene.String(required=True, description="Phone number the code was sent to")
        code = graphene.String(required=True, description="Verification code")

    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    status = PhoneAuthStatus()
    signup_token = graphene.String()
    user = graphene.Field(UserType)
    token = graphene.String()

    @classmethod
    def mutate(cls, root, info, phone, code):
        try:
            normalized = normalize_phone(phone)
        except PhoneVerificationError as exc:
            return VerifyPhoneCode(
                success=False,
                errors=[str(exc)],
                status=None,
                signup_token=None,
                user=None,
                token=None,
            )

        if not get_verification_backend().check_code(normalized, code):
            return VerifyPhoneCode(
                success=False,
                errors=["Invalid verification code."],
                status=None,
                signup_token=None,
                user=None,
                token=None,
            )

        user = User.objects.filter(phone=normalized).first()
        if user is not None:
            if not user.is_active:
                return VerifyPhoneCode(
                    success=False,
                    errors=["This account has been deactivated."],
                    status=None,
                    signup_token=None,
                    user=None,
                    token=None,
                )

            from graphql_jwt.shortcuts import get_token

            jwt_token = get_token(user)
            _stash_jwt_cookie(info, jwt_token)
            return VerifyPhoneCode(
                success=True,
                errors=None,
                status=PhoneAuthStatus.AUTHENTICATED,
                signup_token=None,
                user=user,
                token=None,
            )

        signup_token = PhoneSignupTicket.issue(normalized)
        return VerifyPhoneCode(
            success=True,
            errors=None,
            status=PhoneAuthStatus.NEEDS_USERNAME,
            signup_token=signup_token,
            user=None,
            token=None,
        )


class CompletePhoneSignUpInput(graphene.InputObjectType):
    """Input for creating an account after phone verification."""

    signup_token = graphene.String(required=True, description="Token from verifyPhoneCode")
    username = graphene.String(required=True, description="Unique username")
    first_name = graphene.String(description="User first name")
    last_name = graphene.String(description="User last name")


class CompletePhoneSignUp(graphene.Mutation):
    """Create a passwordless account for a phone number that just passed verification."""

    class Arguments:
        input = CompletePhoneSignUpInput(required=True)

    user = graphene.Field(UserType)
    token = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        username = (input.username or "").strip()
        username_regex = r"^[a-zA-Z0-9_-]{3,30}$"
        if not re.match(username_regex, username):
            return CompletePhoneSignUp(
                user=None,
                token=None,
                success=False,
                errors=[
                    "Username must be 3-30 characters and contain only "
                    "letters, numbers, underscores, and hyphens."
                ],
            )

        if User.objects.filter(username=username).exists():
            return CompletePhoneSignUp(
                user=None,
                token=None,
                success=False,
                errors=["A user with this username already exists."],
            )

        token_hash = PhoneSignupTicket.hash_token(input.signup_token or "")
        invalid_ticket = CompletePhoneSignUp(
            user=None,
            token=None,
            success=False,
            errors=["This signup session is invalid or has expired."],
        )

        with transaction.atomic():
            try:
                ticket = PhoneSignupTicket.objects.select_for_update().get(token_hash=token_hash)
            except PhoneSignupTicket.DoesNotExist:
                return invalid_ticket

            if not ticket.is_valid():
                return invalid_ticket

            if User.objects.filter(phone=ticket.phone).exists():
                ticket.mark_as_used()
                return CompletePhoneSignUp(
                    user=None,
                    token=None,
                    success=False,
                    errors=["A user with this phone number already exists."],
                )

            if User.objects.filter(username=username).exists():
                return CompletePhoneSignUp(
                    user=None,
                    token=None,
                    success=False,
                    errors=["A user with this username already exists."],
                )

            user = User(
                username=username,
                email=None,
                phone=ticket.phone,
                first_name=(input.get("first_name") or "").strip(),
                last_name=(input.get("last_name") or "").strip(),
            )
            user.set_unusable_password()
            try:
                user.save()
            except IntegrityError:
                return CompletePhoneSignUp(
                    user=None,
                    token=None,
                    success=False,
                    errors=["A user with this username already exists."],
                )
            ticket.mark_as_used()

        from graphql_jwt.shortcuts import get_token

        jwt_token = get_token(user)
        _stash_jwt_cookie(info, jwt_token)
        return CompletePhoneSignUp(user=user, token=None, success=True, errors=None)


class Mutation(graphene.ObjectType):
    """Root mutation class for user operations."""

    # Authentication mutations
    sign_up = SignUp.Field(description="Register a new user account")
    sign_in = SignIn.Field(description="Sign in with email and password")
    request_phone_code = RequestPhoneCode.Field(description="Send a phone verification code")
    verify_phone_code = VerifyPhoneCode.Field(
        description="Verify a phone code and sign in or start signup"
    )
    complete_phone_sign_up = CompletePhoneSignUp.Field(
        description="Create an account after phone verification"
    )
    delete_token_cookie = graphql_jwt.DeleteJSONWebTokenCookie.Field(
        description="Clear the HttpOnly JWT cookie"
    )

    # JWT mutations from graphql_jwt
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    # Profile mutations
    update_profile = UpdateProfile.Field(description="Update user profile")
    change_password = ChangePassword.Field(description="Change user password")

    # Password reset mutations
    request_password_reset = RequestPasswordReset.Field(
        description="Request a password reset token"
    )
    confirm_password_reset = ConfirmPasswordReset.Field(
        description="Confirm password reset with token"
    )
