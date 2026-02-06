"""GraphQL types for the users app."""

import graphene
from graphene_django import DjangoObjectType

from users.models import User


class UserType(DjangoObjectType):
    """
    GraphQL type representing a User.
    
    Exposes user fields through GraphQL while hiding sensitive data
    like password hashes.
    """
    
    full_name = graphene.String(description='User full name')
    
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'bio',
            'avatar_url',
            'is_active',
            'is_staff',
            'date_joined',
        )
        description = 'A user of the blog application'
    
    def resolve_full_name(self, info):
        """Resolve the full name of the user."""
        return self.get_full_name()
