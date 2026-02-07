"""GraphQL queries for the users app."""

import graphene
from graphql_jwt.decorators import login_required, staff_member_required

from users.models import User

from .types import UserType


class Query(graphene.ObjectType):
    """User-related GraphQL queries."""

    me = graphene.Field(UserType, description="Get the currently authenticated user")

    user = graphene.Field(
        UserType,
        id=graphene.ID(required=True, description="User ID"),
        description="Get a user by ID (admin only)",
    )

    users = graphene.List(UserType, description="Get all users (admin only)")

    @login_required
    def resolve_me(self, info):
        """
        Resolve the currently authenticated user.

        Requires authentication.
        """
        return info.context.user

    @staff_member_required
    def resolve_user(self, info, id):
        """
        Resolve a user by their ID.

        Only accessible by staff members.
        """
        try:
            return User.objects.get(pk=id)
        except User.DoesNotExist:
            return None

    @staff_member_required
    def resolve_users(self, info):
        """
        Resolve all users.

        Only accessible by staff members.
        """
        return User.objects.all()
