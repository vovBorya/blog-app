"""GraphQL mutations for the blog app."""

import graphene
from django.utils import timezone
from django.utils.text import slugify
from graphql_jwt.decorators import login_required, staff_member_required

from blog.models import Author, BlogPost, Comment

from .types import AuthorType, BlogPostType, CommentType


# ============================================
# Author Mutations
# ============================================

class CreateAuthorInput(graphene.InputObjectType):
    """Input type for creating an author profile."""
    
    bio = graphene.String(description='Author biography')
    avatar_url = graphene.String(description='Avatar URL')
    website = graphene.String(description='Personal website URL')


class CreateAuthor(graphene.Mutation):
    """
    Create an author profile for the current user.
    
    Requires authentication. Creates a new Author linked to the user.
    """
    
    class Arguments:
        input = CreateAuthorInput(required=True)
    
    author = graphene.Field(AuthorType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        user = info.context.user
        
        # Check if user already has an author profile
        if hasattr(user, 'author_profile'):
            return CreateAuthor(
                author=None,
                success=False,
                errors=['You already have an author profile.']
            )
        
        author = Author.objects.create(
            user=user,
            bio=input.get('bio', ''),
            avatar_url=input.get('avatar_url'),
            website=input.get('website'),
        )
        
        return CreateAuthor(author=author, success=True, errors=None)


class UpdateAuthor(graphene.Mutation):
    """
    Update the current user's author profile.
    
    Requires authentication.
    """
    
    class Arguments:
        bio = graphene.String(description='Author biography')
        avatar_url = graphene.String(description='Avatar URL')
        website = graphene.String(description='Personal website URL')
    
    author = graphene.Field(AuthorType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, **kwargs):
        user = info.context.user
        
        try:
            author = user.author_profile
        except Author.DoesNotExist:
            return UpdateAuthor(
                author=None,
                success=False,
                errors=['You do not have an author profile. Create one first.']
            )
        
        if 'bio' in kwargs and kwargs['bio'] is not None:
            author.bio = kwargs['bio']
        if 'avatar_url' in kwargs and kwargs['avatar_url'] is not None:
            author.avatar_url = kwargs['avatar_url']
        if 'website' in kwargs and kwargs['website'] is not None:
            author.website = kwargs['website']
        
        author.save()
        return UpdateAuthor(author=author, success=True, errors=None)


# ============================================
# Blog Post Mutations
# ============================================

class CreatePostInput(graphene.InputObjectType):
    """Input type for creating a blog post."""
    
    title = graphene.String(required=True, description='Post title')
    content = graphene.String(required=True, description='Post content')
    excerpt = graphene.String(description='Post excerpt/summary')
    status = graphene.String(description='Post status (draft or published)')
    featured_image_url = graphene.String(description='Featured image URL')


class CreatePost(graphene.Mutation):
    """
    Create a new blog post.
    
    Requires authentication and an author profile.
    """
    
    class Arguments:
        input = CreatePostInput(required=True)
    
    post = graphene.Field(BlogPostType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        user = info.context.user
        errors = []
        
        # Validate user has an author profile
        try:
            author = user.author_profile
        except Author.DoesNotExist:
            return CreatePost(
                post=None,
                success=False,
                errors=['You need an author profile to create posts.']
            )
        
        # Validate title
        if not input.title or len(input.title.strip()) == 0:
            errors.append('Title is required.')
        elif len(input.title) > 200:
            errors.append('Title must be 200 characters or less.')
        
        # Validate content
        if not input.content or len(input.content.strip()) == 0:
            errors.append('Content is required.')
        
        # Validate status
        status = input.get('status', BlogPost.Status.DRAFT)
        if status not in [BlogPost.Status.DRAFT, BlogPost.Status.PUBLISHED]:
            errors.append('Status must be either "draft" or "published".')
        
        if errors:
            return CreatePost(post=None, success=False, errors=errors)
        
        post = BlogPost.objects.create(
            title=input.title.strip(),
            content=input.content.strip(),
            excerpt=input.get('excerpt', ''),
            author=author,
            status=status,
            featured_image_url=input.get('featured_image_url'),
        )
        
        return CreatePost(post=post, success=True, errors=None)


class UpdatePostInput(graphene.InputObjectType):
    """Input type for updating a blog post."""
    
    title = graphene.String(description='Post title')
    content = graphene.String(description='Post content')
    excerpt = graphene.String(description='Post excerpt/summary')
    status = graphene.String(description='Post status (draft or published)')
    featured_image_url = graphene.String(description='Featured image URL')


class UpdatePost(graphene.Mutation):
    """
    Update an existing blog post.
    
    Requires authentication and ownership of the post.
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Post ID')
        input = UpdatePostInput(required=True)
    
    post = graphene.Field(BlogPostType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id, input):
        user = info.context.user
        errors = []
        
        # Get the post
        try:
            post = BlogPost.objects.get(pk=id)
        except BlogPost.DoesNotExist:
            return UpdatePost(
                post=None,
                success=False,
                errors=['Post not found.']
            )
        
        # Check ownership (unless staff)
        if post.author.user != user and not user.is_staff:
            return UpdatePost(
                post=None,
                success=False,
                errors=['You do not have permission to edit this post.']
            )
        
        # Validate and update title
        if input.title is not None:
            if len(input.title.strip()) == 0:
                errors.append('Title cannot be empty.')
            elif len(input.title) > 200:
                errors.append('Title must be 200 characters or less.')
            else:
                post.title = input.title.strip()
                # Regenerate slug if title changed
                post.slug = post._generate_unique_slug()
        
        # Validate and update content
        if input.content is not None:
            if len(input.content.strip()) == 0:
                errors.append('Content cannot be empty.')
            else:
                post.content = input.content.strip()
        
        # Update optional fields
        if input.excerpt is not None:
            post.excerpt = input.excerpt
        
        if input.featured_image_url is not None:
            post.featured_image_url = input.featured_image_url
        
        # Update status
        if input.status is not None:
            if input.status not in [BlogPost.Status.DRAFT, BlogPost.Status.PUBLISHED]:
                errors.append('Status must be either "draft" or "published".')
            else:
                post.status = input.status
        
        if errors:
            return UpdatePost(post=None, success=False, errors=errors)
        
        post.save()
        return UpdatePost(post=post, success=True, errors=None)


class DeletePost(graphene.Mutation):
    """
    Delete a blog post.
    
    Requires authentication and ownership (or staff status).
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Post ID')
    
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id):
        user = info.context.user
        
        try:
            post = BlogPost.objects.get(pk=id)
        except BlogPost.DoesNotExist:
            return DeletePost(success=False, errors=['Post not found.'])
        
        # Check ownership (unless staff)
        if post.author.user != user and not user.is_staff:
            return DeletePost(
                success=False,
                errors=['You do not have permission to delete this post.']
            )
        
        post.delete()
        return DeletePost(success=True, errors=None)


class PublishPost(graphene.Mutation):
    """
    Publish a blog post.
    
    Sets status to published and published_at to now.
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Post ID')
    
    post = graphene.Field(BlogPostType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id):
        user = info.context.user
        
        try:
            post = BlogPost.objects.get(pk=id)
        except BlogPost.DoesNotExist:
            return PublishPost(
                post=None,
                success=False,
                errors=['Post not found.']
            )
        
        # Check ownership (unless staff)
        if post.author.user != user and not user.is_staff:
            return PublishPost(
                post=None,
                success=False,
                errors=['You do not have permission to publish this post.']
            )
        
        post.publish()
        return PublishPost(post=post, success=True, errors=None)


class UnpublishPost(graphene.Mutation):
    """
    Unpublish a blog post (set to draft).
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Post ID')
    
    post = graphene.Field(BlogPostType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id):
        user = info.context.user
        
        try:
            post = BlogPost.objects.get(pk=id)
        except BlogPost.DoesNotExist:
            return UnpublishPost(
                post=None,
                success=False,
                errors=['Post not found.']
            )
        
        if post.author.user != user and not user.is_staff:
            return UnpublishPost(
                post=None,
                success=False,
                errors=['You do not have permission to unpublish this post.']
            )
        
        post.unpublish()
        return UnpublishPost(post=post, success=True, errors=None)


# ============================================
# Comment Mutations
# ============================================

class CreateCommentInput(graphene.InputObjectType):
    """Input type for creating a comment."""
    
    post_id = graphene.ID(required=True, description='Post ID to comment on')
    content = graphene.String(required=True, description='Comment content')
    parent_id = graphene.ID(description='Parent comment ID for replies')


class CreateComment(graphene.Mutation):
    """
    Create a comment on a blog post.
    
    Requires authentication.
    """
    
    class Arguments:
        input = CreateCommentInput(required=True)
    
    comment = graphene.Field(CommentType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        user = info.context.user
        errors = []
        
        # Get the post
        try:
            post = BlogPost.objects.get(pk=input.post_id)
        except BlogPost.DoesNotExist:
            return CreateComment(
                comment=None,
                success=False,
                errors=['Post not found.']
            )
        
        # Validate content
        if not input.content or len(input.content.strip()) == 0:
            errors.append('Comment content is required.')
        elif len(input.content) > 2000:
            errors.append('Comment must be 2000 characters or less.')
        
        # Validate parent comment if provided
        parent = None
        if input.parent_id:
            try:
                parent = Comment.objects.get(pk=input.parent_id, post=post)
            except Comment.DoesNotExist:
                errors.append('Parent comment not found.')
        
        if errors:
            return CreateComment(comment=None, success=False, errors=errors)
        
        comment = Comment.objects.create(
            post=post,
            author=user,
            content=input.content.strip(),
            parent=parent,
        )
        
        return CreateComment(comment=comment, success=True, errors=None)


class UpdateComment(graphene.Mutation):
    """
    Update an existing comment.
    
    Requires authentication and ownership of the comment.
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Comment ID')
        content = graphene.String(required=True, description='New content')
    
    comment = graphene.Field(CommentType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id, content):
        user = info.context.user
        
        try:
            comment = Comment.objects.get(pk=id)
        except Comment.DoesNotExist:
            return UpdateComment(
                comment=None,
                success=False,
                errors=['Comment not found.']
            )
        
        # Check ownership
        if comment.author != user:
            return UpdateComment(
                comment=None,
                success=False,
                errors=['You can only edit your own comments.']
            )
        
        # Validate content
        if not content or len(content.strip()) == 0:
            return UpdateComment(
                comment=None,
                success=False,
                errors=['Comment content is required.']
            )
        
        if len(content) > 2000:
            return UpdateComment(
                comment=None,
                success=False,
                errors=['Comment must be 2000 characters or less.']
            )
        
        comment.content = content.strip()
        comment.save()
        
        return UpdateComment(comment=comment, success=True, errors=None)


class DeleteComment(graphene.Mutation):
    """
    Delete a comment.
    
    Requires authentication and ownership, post ownership, or staff status.
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Comment ID')
    
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id):
        user = info.context.user
        
        try:
            comment = Comment.objects.select_related('post__author__user').get(pk=id)
        except Comment.DoesNotExist:
            return DeleteComment(success=False, errors=['Comment not found.'])
        
        # Check permissions: comment author, post author, or staff
        is_comment_author = comment.author == user
        is_post_author = comment.post.author.user == user
        is_staff = user.is_staff
        
        if not (is_comment_author or is_post_author or is_staff):
            return DeleteComment(
                success=False,
                errors=['You do not have permission to delete this comment.']
            )
        
        comment.delete()
        return DeleteComment(success=True, errors=None)


class ApproveComment(graphene.Mutation):
    """
    Approve or disapprove a comment.
    
    Requires staff status or post ownership.
    """
    
    class Arguments:
        id = graphene.ID(required=True, description='Comment ID')
        is_approved = graphene.Boolean(required=True, description='Approval status')
    
    comment = graphene.Field(CommentType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    @classmethod
    @login_required
    def mutate(cls, root, info, id, is_approved):
        user = info.context.user
        
        try:
            comment = Comment.objects.select_related('post__author__user').get(pk=id)
        except Comment.DoesNotExist:
            return ApproveComment(
                comment=None,
                success=False,
                errors=['Comment not found.']
            )
        
        # Check permissions: post author or staff
        is_post_author = comment.post.author.user == user
        is_staff = user.is_staff
        
        if not (is_post_author or is_staff):
            return ApproveComment(
                comment=None,
                success=False,
                errors=['You do not have permission to moderate this comment.']
            )
        
        comment.is_approved = is_approved
        comment.save()
        
        return ApproveComment(comment=comment, success=True, errors=None)


class Mutation(graphene.ObjectType):
    """Root mutation class for blog operations."""
    
    # Author mutations
    create_author = CreateAuthor.Field(description='Create an author profile')
    update_author = UpdateAuthor.Field(description='Update your author profile')
    
    # Blog post mutations
    create_post = CreatePost.Field(description='Create a new blog post')
    update_post = UpdatePost.Field(description='Update an existing blog post')
    delete_post = DeletePost.Field(description='Delete a blog post')
    publish_post = PublishPost.Field(description='Publish a blog post')
    unpublish_post = UnpublishPost.Field(description='Unpublish a blog post')
    
    # Comment mutations
    create_comment = CreateComment.Field(description='Create a comment')
    update_comment = UpdateComment.Field(description='Update a comment')
    delete_comment = DeleteComment.Field(description='Delete a comment')
    approve_comment = ApproveComment.Field(description='Approve/disapprove a comment')
