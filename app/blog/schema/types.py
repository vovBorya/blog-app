"""GraphQL types for the blog app."""

import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from blog.models import Author, BlogPost, Comment
from users.schema.types import UserType


class AuthorType(DjangoObjectType):
    """
    GraphQL type representing an Author.
    
    Includes user relationship and post statistics.
    """
    
    post_count = graphene.Int(description='Number of published posts by this author')
    user = graphene.Field(UserType, description='The user associated with this author')
    
    class Meta:
        model = Author
        fields = (
            'id',
            'user',
            'bio',
            'avatar_url',
            'website',
            'created_at',
            'updated_at',
        )
        interfaces = (relay.Node,)
        description = 'An author who writes blog posts'
    
    def resolve_post_count(self, info):
        """Resolve the number of published posts."""
        return self.post_count


class BlogPostType(DjangoObjectType):
    """
    GraphQL type representing a BlogPost.
    
    Includes author relationship and comment count.
    """
    
    comment_count = graphene.Int(description='Number of approved comments')
    author = graphene.Field(AuthorType, description='The author of this post')
    status = graphene.String(description='Publication status of the post')
    
    class Meta:
        model = BlogPost
        fields = (
            'id',
            'title',
            'slug',
            'content',
            'excerpt',
            'author',
            'featured_image_url',
            'published_at',
            'created_at',
            'updated_at',
        )
        interfaces = (relay.Node,)
        filter_fields = {
            'status': ['exact'],
            'author': ['exact'],
            'published_at': ['exact', 'gte', 'lte'],
            'title': ['exact', 'icontains'],
        }
        description = 'A blog post with content and metadata'
    
    def resolve_comment_count(self, info):
        """Resolve the number of approved comments."""
        return self.comment_count
    
    def resolve_status(self, info):
        """Return the lowercase status value."""
        return self.status


class CommentType(DjangoObjectType):
    """
    GraphQL type representing a Comment.
    
    Includes author and post relationships.
    """
    
    author = graphene.Field(UserType, description='The user who wrote this comment')
    is_reply = graphene.Boolean(description='Whether this is a reply to another comment')
    
    class Meta:
        model = Comment
        fields = (
            'id',
            'post',
            'author',
            'content',
            'parent',
            'replies',
            'is_approved',
            'created_at',
            'updated_at',
        )
        interfaces = (relay.Node,)
        description = 'A comment on a blog post'
    
    def resolve_is_reply(self, info):
        """Resolve whether this is a reply."""
        return self.is_reply


class BlogPostConnection(relay.Connection):
    """Connection type for paginated blog posts."""
    
    class Meta:
        node = BlogPostType
    
    total_count = graphene.Int()
    
    def resolve_total_count(root, info):
        return root.length


class CommentConnection(relay.Connection):
    """Connection type for paginated comments."""
    
    class Meta:
        node = CommentType
    
    total_count = graphene.Int()
    
    def resolve_total_count(root, info):
        return root.length


class AuthorConnection(relay.Connection):
    """Connection type for paginated authors."""
    
    class Meta:
        node = AuthorType
    
    total_count = graphene.Int()
    
    def resolve_total_count(root, info):
        return root.length
