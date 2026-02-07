"""
Root GraphQL schema for the blog API.

Combines all queries and mutations from different apps into a single schema.
"""

import graphene

from blog.schema import Mutation as BlogMutation
from blog.schema import Query as BlogQuery
from users.schema import Mutation as UserMutation
from users.schema import Query as UserQuery


class Query(UserQuery, BlogQuery, graphene.ObjectType):
    """
    Root Query class.

    Combines all app-specific queries into a single GraphQL query.
    """


class Mutation(UserMutation, BlogMutation, graphene.ObjectType):
    """
    Root Mutation class.

    Combines all app-specific mutations into a single GraphQL mutation.
    """


schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
)
