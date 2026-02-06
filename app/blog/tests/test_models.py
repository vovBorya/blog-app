"""Tests for blog models."""

import pytest
from django.utils import timezone

from blog.models import Author, BlogPost, Comment


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
        password='TestPass123!',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def author(user):
    """Create a test author."""
    return Author.objects.create(
        user=user,
        bio='Test author bio',
        website='https://example.com'
    )


@pytest.fixture
def blog_post(author):
    """Create a test blog post."""
    return BlogPost.objects.create(
        title='Test Blog Post',
        content='This is the content of the test blog post.',
        author=author,
        status=BlogPost.Status.PUBLISHED,
        published_at=timezone.now()
    )


@pytest.mark.django_db
class TestAuthorModel:
    """Test cases for the Author model."""

    def test_create_author(self, user):
        """Test creating an author profile."""
        author = Author.objects.create(
            user=user,
            bio='This is my bio',
            website='https://mysite.com'
        )

        assert author.user == user
        assert author.bio == 'This is my bio'
        assert author.website == 'https://mysite.com'
        assert author.created_at is not None

    def test_author_str_method(self, author):
        """Test the string representation of an author."""
        expected = f'{author.user.get_full_name()} ({author.user.username})'
        assert str(author) == expected

    def test_author_post_count(self, author):
        """Test the post_count property."""
        # Create some posts
        BlogPost.objects.create(
            title='Post 1',
            content='Content 1',
            author=author,
            status=BlogPost.Status.PUBLISHED
        )
        BlogPost.objects.create(
            title='Post 2',
            content='Content 2',
            author=author,
            status=BlogPost.Status.DRAFT
        )
        BlogPost.objects.create(
            title='Post 3',
            content='Content 3',
            author=author,
            status=BlogPost.Status.PUBLISHED
        )

        # Only published posts should be counted
        assert author.post_count == 2


@pytest.mark.django_db
class TestBlogPostModel:
    """Test cases for the BlogPost model."""

    def test_create_blog_post(self, author):
        """Test creating a blog post."""
        post = BlogPost.objects.create(
            title='My First Post',
            content='This is the content.',
            author=author,
            status=BlogPost.Status.DRAFT
        )

        assert post.title == 'My First Post'
        assert post.author == author
        assert post.status == BlogPost.Status.DRAFT
        assert post.slug == 'my-first-post'

    def test_blog_post_auto_slug_generation(self, author):
        """Test automatic slug generation from title."""
        post = BlogPost.objects.create(
            title='This Is A Test Title',
            content='Content',
            author=author
        )

        assert post.slug == 'this-is-a-test-title'

    def test_blog_post_unique_slug(self, author):
        """Test that slugs are unique."""
        post1 = BlogPost.objects.create(
            title='Same Title',
            content='Content 1',
            author=author
        )
        post2 = BlogPost.objects.create(
            title='Same Title',
            content='Content 2',
            author=author
        )

        assert post1.slug == 'same-title'
        assert post2.slug == 'same-title-1'

    def test_blog_post_str_method(self, blog_post):
        """Test the string representation of a blog post."""
        assert str(blog_post) == blog_post.title

    def test_blog_post_publish(self, author):
        """Test publishing a blog post."""
        post = BlogPost.objects.create(
            title='Draft Post',
            content='Content',
            author=author,
            status=BlogPost.Status.DRAFT
        )

        assert post.status == BlogPost.Status.DRAFT
        assert post.published_at is None

        post.publish()

        assert post.status == BlogPost.Status.PUBLISHED
        assert post.published_at is not None

    def test_blog_post_unpublish(self, blog_post):
        """Test unpublishing a blog post."""
        assert blog_post.status == BlogPost.Status.PUBLISHED

        blog_post.unpublish()

        assert blog_post.status == BlogPost.Status.DRAFT

    def test_blog_post_comment_count(self, blog_post, user):
        """Test the comment_count property."""
        # Create some comments
        Comment.objects.create(
            post=blog_post,
            author=user,
            content='Comment 1',
            is_approved=True
        )
        Comment.objects.create(
            post=blog_post,
            author=user,
            content='Comment 2',
            is_approved=False
        )
        Comment.objects.create(
            post=blog_post,
            author=user,
            content='Comment 3',
            is_approved=True
        )

        # Only approved comments should be counted
        assert blog_post.comment_count == 2


@pytest.mark.django_db
class TestCommentModel:
    """Test cases for the Comment model."""

    def test_create_comment(self, blog_post, user):
        """Test creating a comment."""
        comment = Comment.objects.create(
            post=blog_post,
            author=user,
            content='This is a test comment.'
        )

        assert comment.post == blog_post
        assert comment.author == user
        assert comment.content == 'This is a test comment.'
        assert comment.is_approved is True

    def test_comment_str_method(self, blog_post, user):
        """Test the string representation of a comment."""
        comment = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Test comment'
        )

        expected = f'Comment by {user.username} on "{blog_post.title}"'
        assert str(comment) == expected

    def test_comment_is_reply_false(self, blog_post, user):
        """Test is_reply property for top-level comment."""
        comment = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Top level comment'
        )

        assert comment.is_reply is False

    def test_comment_is_reply_true(self, blog_post, user):
        """Test is_reply property for reply comment."""
        parent = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Parent comment'
        )
        reply = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Reply comment',
            parent=parent
        )

        assert reply.is_reply is True
        assert reply.parent == parent

    def test_comment_replies_relationship(self, blog_post, user):
        """Test that replies are accessible from parent."""
        parent = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Parent comment'
        )
        reply1 = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Reply 1',
            parent=parent
        )
        reply2 = Comment.objects.create(
            post=blog_post,
            author=user,
            content='Reply 2',
            parent=parent
        )

        replies = parent.replies.all()
        assert reply1 in replies
        assert reply2 in replies
        assert replies.count() == 2
