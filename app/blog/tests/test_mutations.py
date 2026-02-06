"""Tests for blog GraphQL mutations."""

import pytest
from django.utils import timezone
from unittest.mock import Mock

from blog.models import Author, BlogPost, Comment
from core.schema import schema


def get_user_model():
    """Lazy-load User model to avoid Django configuration issues at import time."""
    from django.contrib.auth import get_user_model as _get_user_model
    return _get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='TestPass123!'
    )


@pytest.fixture
def author(user):
    """Create a test author."""
    return Author.objects.create(
        user=user,
        bio='Test bio'
    )


@pytest.fixture
def blog_post(author):
    """Create a test blog post."""
    return BlogPost.objects.create(
        title='Test Post',
        content='Test content.',
        author=author,
        status=BlogPost.Status.DRAFT
    )


def create_context(user=None):
    """Create a mock context with optional user."""
    from django.contrib.auth.models import AnonymousUser

    context = Mock()
    context.user = user if user else AnonymousUser()
    return context


@pytest.mark.django_db
class TestCreateAuthor:
    """Test cases for create author mutation."""

    def test_create_author_success(self, user):
        """Test creating an author profile."""
        query = '''
            mutation {
                createAuthor(input: {
                    bio: "I am a writer"
                    website: "https://mysite.com"
                }) {
                    success
                    errors
                    author {
                        bio
                        website
                    }
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['createAuthor']['success'] is True
        assert result.data['createAuthor']['author']['bio'] == 'I am a writer'
        assert result.data['createAuthor']['author']['website'] == 'https://mysite.com'

    def test_create_author_already_exists(self, author):
        """Test creating author when one already exists."""
        query = '''
            mutation {
                createAuthor(input: {
                    bio: "Another bio"
                }) {
                    success
                    errors
                }
            }
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data['createAuthor']['success'] is False
        assert 'already have an author profile' in str(result.data['createAuthor']['errors']).lower()

    def test_create_author_unauthenticated(self):
        """Test creating author without authentication."""
        query = '''
            mutation {
                createAuthor(input: {
                    bio: "Test"
                }) {
                    success
                    errors
                }
            }
        '''

        context = create_context()  # Anonymous user
        result = schema.execute(query, context_value=context)

        # Should fail due to login_required
        assert result.errors is not None or result.data['createAuthor']['success'] is False


@pytest.mark.django_db
class TestCreatePost:
    """Test cases for create post mutation."""

    def test_create_post_success(self, author):
        """Test creating a blog post."""
        query = '''
            mutation {
                createPost(input: {
                    title: "My New Post"
                    content: "This is the content of my post."
                    status: "draft"
                }) {
                    success
                    errors
                    post {
                        title
                        slug
                        content
                        status
                    }
                }
            }
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['createPost']['success'] is True
        assert result.data['createPost']['post']['title'] == 'My New Post'
        assert result.data['createPost']['post']['slug'] == 'my-new-post'
        assert result.data['createPost']['post']['status'] == 'draft'

    def test_create_post_no_author_profile(self, user):
        """Test creating post without author profile."""
        query = '''
            mutation {
                createPost(input: {
                    title: "Test"
                    content: "Content"
                }) {
                    success
                    errors
                }
            }
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data['createPost']['success'] is False
        assert 'author profile' in str(result.data['createPost']['errors']).lower()

    def test_create_post_empty_title(self, author):
        """Test creating post with empty title."""
        query = '''
            mutation {
                createPost(input: {
                    title: ""
                    content: "Content"
                }) {
                    success
                    errors
                }
            }
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data['createPost']['success'] is False
        assert 'title' in str(result.data['createPost']['errors']).lower()

    def test_create_post_empty_content(self, author):
        """Test creating post with empty content."""
        query = '''
            mutation {
                createPost(input: {
                    title: "Valid Title"
                    content: ""
                }) {
                    success
                    errors
                }
            }
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data['createPost']['success'] is False
        assert 'content' in str(result.data['createPost']['errors']).lower()


@pytest.mark.django_db
class TestUpdatePost:
    """Test cases for update post mutation."""

    def test_update_post_success(self, author, blog_post):
        """Test updating a blog post."""
        query = f'''
            mutation {{
                updatePost(
                    id: "{blog_post.id}"
                    input: {{
                        title: "Updated Title"
                        content: "Updated content."
                    }}
                ) {{
                    success
                    errors
                    post {{
                        title
                        content
                    }}
                }}
            }}
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['updatePost']['success'] is True
        assert result.data['updatePost']['post']['title'] == 'Updated Title'

    def test_update_post_not_owner(self, blog_post):
        """Test updating post as non-owner."""
        User = get_user_model()
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='TestPass123!'
        )

        query = f'''
            mutation {{
                updatePost(
                    id: "{blog_post.id}"
                    input: {{
                        title: "Hacked Title"
                    }}
                ) {{
                    success
                    errors
                }}
            }}
        '''

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.data['updatePost']['success'] is False
        assert 'permission' in str(result.data['updatePost']['errors']).lower()


@pytest.mark.django_db
class TestDeletePost:
    """Test cases for delete post mutation."""

    def test_delete_post_success(self, author, blog_post):
        """Test deleting a blog post."""
        post_id = blog_post.id

        query = f'''
            mutation {{
                deletePost(id: "{post_id}") {{
                    success
                    errors
                }}
            }}
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['deletePost']['success'] is True
        assert not BlogPost.objects.filter(id=post_id).exists()

    def test_delete_post_not_found(self, author):
        """Test deleting non-existent post."""
        query = '''
            mutation {
                deletePost(id: "99999") {
                    success
                    errors
                }
            }
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data['deletePost']['success'] is False
        assert 'not found' in str(result.data['deletePost']['errors']).lower()


@pytest.mark.django_db
class TestPublishPost:
    """Test cases for publish post mutation."""

    def test_publish_post_success(self, author, blog_post):
        """Test publishing a draft post."""
        assert blog_post.status == BlogPost.Status.DRAFT

        query = f'''
            mutation {{
                publishPost(id: "{blog_post.id}") {{
                    success
                    errors
                    post {{
                        status
                        publishedAt
                    }}
                }}
            }}
        '''

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['publishPost']['success'] is True
        assert result.data['publishPost']['post']['status'] == 'published'
        assert result.data['publishPost']['post']['publishedAt'] is not None


@pytest.mark.django_db
class TestCommentMutations:
    """Test cases for comment mutations."""

    def test_create_comment_success(self, user, blog_post):
        """Test creating a comment."""
        # Need to make post published for commenting
        blog_post.status = BlogPost.Status.PUBLISHED
        blog_post.save()

        query = f'''
            mutation {{
                createComment(input: {{
                    postId: "{blog_post.id}"
                    content: "Great post!"
                }}) {{
                    success
                    errors
                    comment {{
                        content
                        author {{
                            username
                        }}
                    }}
                }}
            }}
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['createComment']['success'] is True
        assert result.data['createComment']['comment']['content'] == 'Great post!'

    def test_create_comment_empty_content(self, user, blog_post):
        """Test creating comment with empty content."""
        query = f'''
            mutation {{
                createComment(input: {{
                    postId: "{blog_post.id}"
                    content: ""
                }}) {{
                    success
                    errors
                }}
            }}
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data['createComment']['success'] is False
        assert 'content' in str(result.data['createComment']['errors']).lower()

    def test_delete_comment_as_author(self, user, blog_post):
        """Test deleting own comment."""
        comment = Comment.objects.create(
            post=blog_post,
            author=user,
            content='My comment'
        )

        query = f'''
            mutation {{
                deleteComment(id: "{comment.id}") {{
                    success
                    errors
                }}
            }}
        '''

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data['deleteComment']['success'] is True
        assert not Comment.objects.filter(id=comment.id).exists()
