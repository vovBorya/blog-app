"""GraphQL queries for the blog app."""

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from blog.models import Author, BlogPost, Comment

from .types import (
    AuthorConnection,
    AuthorType,
    BlogPostConnection,
    BlogPostType,
    CommentConnection,
    CommentType,
)


class Query(graphene.ObjectType):
    """Blog-related GraphQL queries."""
    
    # Single item queries
    post = graphene.Field(
        BlogPostType,
        id=graphene.ID(description='Post ID'),
        slug=graphene.String(description='Post slug'),
        description='Get a single blog post by ID or slug'
    )
    
    author = graphene.Field(
        AuthorType,
        id=graphene.ID(required=True, description='Author ID'),
        description='Get an author by ID'
    )
    
    comment = graphene.Field(
        CommentType,
        id=graphene.ID(required=True, description='Comment ID'),
        description='Get a comment by ID'
    )
    
    # List queries with filtering and pagination
    all_posts = graphene.ConnectionField(
        BlogPostConnection,
        status=graphene.String(description='Filter by status (draft, published)'),
        author_id=graphene.ID(description='Filter by author ID'),
        search=graphene.String(description='Search in title and content'),
        description='Get all blog posts with filtering and pagination'
    )
    
    all_authors = graphene.ConnectionField(
        AuthorConnection,
        description='Get all authors with pagination'
    )
    
    all_comments = graphene.ConnectionField(
        CommentConnection,
        post_id=graphene.ID(description='Filter by post ID'),
        is_approved=graphene.Boolean(description='Filter by approval status'),
        description='Get all comments with filtering and pagination'
    )
    
    # Published posts only (public query)
    published_posts = graphene.ConnectionField(
        BlogPostConnection,
        author_id=graphene.ID(description='Filter by author ID'),
        search=graphene.String(description='Search in title and content'),
        description='Get all published blog posts'
    )
    
    def resolve_post(self, info, id=None, slug=None):
        """
        Resolve a single blog post by ID or slug.
        
        At least one of id or slug must be provided.
        """
        if id:
            try:
                return BlogPost.objects.select_related('author', 'author__user').get(pk=id)
            except BlogPost.DoesNotExist:
                return None
        
        if slug:
            try:
                return BlogPost.objects.select_related('author', 'author__user').get(slug=slug)
            except BlogPost.DoesNotExist:
                return None
        
        return None
    
    def resolve_author(self, info, id):
        """Resolve an author by ID."""
        try:
            return Author.objects.select_related('user').get(pk=id)
        except Author.DoesNotExist:
            return None
    
    def resolve_comment(self, info, id):
        """Resolve a comment by ID."""
        try:
            return Comment.objects.select_related('author', 'post').get(pk=id)
        except Comment.DoesNotExist:
            return None
    
    def resolve_all_posts(self, info, status=None, author_id=None, search=None, **kwargs):
        """
        Resolve all blog posts with optional filtering.
        
        Optimizes queries with select_related and prefetch_related.
        """
        queryset = BlogPost.objects.select_related(
            'author', 'author__user'
        ).prefetch_related('comments')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        return queryset
    
    def resolve_all_authors(self, info, **kwargs):
        """
        Resolve all authors.
        
        Includes prefetch for posts to optimize post_count.
        """
        return Author.objects.select_related('user').prefetch_related('posts')
    
    def resolve_all_comments(self, info, post_id=None, is_approved=None, **kwargs):
        """
        Resolve all comments with optional filtering.
        """
        queryset = Comment.objects.select_related('author', 'post')
        
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        
        if is_approved is not None:
            queryset = queryset.filter(is_approved=is_approved)
        
        return queryset
    
    def resolve_published_posts(self, info, author_id=None, search=None, **kwargs):
        """
        Resolve only published blog posts.
        
        This is a public query that only returns published content.
        """
        queryset = BlogPost.objects.select_related(
            'author', 'author__user'
        ).prefetch_related('comments').filter(
            status=BlogPost.Status.PUBLISHED
        )
        
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        return queryset
