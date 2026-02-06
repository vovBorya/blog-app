"""GraphQL schema exports for blog app."""

from .mutations import Mutation
from .queries import Query
from .types import AuthorType, BlogPostType, CommentType

__all__ = ['Query', 'Mutation', 'AuthorType', 'BlogPostType', 'CommentType']
