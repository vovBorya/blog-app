"""Tests for blog GraphQL like/unlike mutations."""

from unittest.mock import Mock

import pytest

from blog.models import Author, BlogPost, Like
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
        email="test@example.com", username="testuser", password="TestPass123!"
    )


@pytest.fixture
def other_user():
    """A second user distinct from the post author, for liking."""
    User = get_user_model()
    return User.objects.create_user(
        email="other@example.com", username="otheruser", password="TestPass123!"
    )


@pytest.fixture
def author(user):
    """Create a test author."""
    return Author.objects.create(user=user, bio="Test bio")


@pytest.fixture
def blog_post(author):
    """Create a test blog post."""
    return BlogPost.objects.create(
        title="Test Post",
        content="Test content.",
        author=author,
        status=BlogPost.Status.PUBLISHED,
    )


def create_context(user=None):
    """Create a mock context with optional user."""
    from django.contrib.auth.models import AnonymousUser

    context = Mock()
    context.user = user if user else AnonymousUser()
    return context


@pytest.mark.django_db
class TestLikePost:
    """Test cases for like post mutation."""

    def test_like_post_success(self, other_user, blog_post):
        """Test liking a blog post successfully."""
        query = f"""
            mutation {{
                likePost(postId: "{blog_post.id}") {{
                    success
                    errors
                    post {{
                        id
                        likeCount
                        isLikedByMe
                    }}
                }}
            }}
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["likePost"]["success"] is True
        assert result.data["likePost"]["post"]["likeCount"] == 1
        assert result.data["likePost"]["post"]["isLikedByMe"] is True
        assert Like.objects.filter(post=blog_post, user=other_user).exists()

    def test_like_post_duplicate_rejected(self, other_user, blog_post):
        """Test liking a post that is already liked."""
        Like.objects.create(post=blog_post, user=other_user)

        query = f"""
            mutation {{
                likePost(postId: "{blog_post.id}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.data["likePost"]["success"] is False
        assert "already liked" in str(result.data["likePost"]["errors"]).lower()
        assert Like.objects.filter(post=blog_post, user=other_user).count() == 1

    def test_like_post_unauthenticated_rejected(self, blog_post):
        """Test liking a post without authentication."""
        query = f"""
            mutation {{
                likePost(postId: "{blog_post.id}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context()  # Anonymous user
        result = schema.execute(query, context_value=context)

        # login_required decorator should produce a GraphQL error
        assert result.errors is not None

    def test_like_post_nonexistent_post(self, other_user):
        """Test liking a non-existent post."""
        query = """
            mutation {
                likePost(postId: "999999") {
                    success
                    errors
                }
            }
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.data["likePost"]["success"] is False
        assert "not found" in str(result.data["likePost"]["errors"]).lower()

    def test_like_post_self_like(self, author, blog_post):
        """Test that authors can like their own posts."""
        query = f"""
            mutation {{
                likePost(postId: "{blog_post.id}") {{
                    success
                    errors
                    post {{
                        likeCount
                    }}
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["likePost"]["success"] is True
        assert result.data["likePost"]["post"]["likeCount"] == 1


@pytest.mark.django_db
class TestUnlikePost:
    """Test cases for unlike post mutation."""

    def test_unlike_post_success(self, other_user, blog_post):
        """Test unliking a blog post successfully."""
        Like.objects.create(post=blog_post, user=other_user)

        query = f"""
            mutation {{
                unlikePost(postId: "{blog_post.id}") {{
                    success
                    errors
                    post {{
                        id
                        likeCount
                        isLikedByMe
                    }}
                }}
            }}
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["unlikePost"]["success"] is True
        assert result.data["unlikePost"]["post"]["likeCount"] == 0
        assert result.data["unlikePost"]["post"]["isLikedByMe"] is False
        assert not Like.objects.filter(post=blog_post, user=other_user).exists()

    def test_unlike_post_without_existing_like_rejected(self, other_user, blog_post):
        """Test unliking a post that was not liked."""
        query = f"""
            mutation {{
                unlikePost(postId: "{blog_post.id}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.data["unlikePost"]["success"] is False
        assert "have not liked" in str(result.data["unlikePost"]["errors"]).lower()

    def test_unlike_post_unauthenticated_rejected(self, blog_post):
        """Test unliking a post without authentication."""
        query = f"""
            mutation {{
                unlikePost(postId: "{blog_post.id}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context()  # Anonymous user
        result = schema.execute(query, context_value=context)

        # login_required decorator should produce a GraphQL error
        assert result.errors is not None

    def test_unlike_post_nonexistent_post(self, other_user):
        """Test unliking a non-existent post."""
        query = """
            mutation {
                unlikePost(postId: "999999") {
                    success
                    errors
                }
            }
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.data["unlikePost"]["success"] is False
        assert "not found" in str(result.data["unlikePost"]["errors"]).lower()


@pytest.mark.django_db
class TestBlogPostLikeFields:
    """Test cases for blog post like count and is_liked_by_me fields."""

    def test_like_count_and_is_liked_by_me_authenticated(self, user, other_user, blog_post):
        """Test like_count and is_liked_by_me fields for authenticated users."""
        Like.objects.create(post=blog_post, user=other_user)

        query = f"""
            query {{
                post(id: "{blog_post.id}") {{
                    likeCount
                    isLikedByMe
                }}
            }}
        """

        # Query as user who didn't like
        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["post"]["likeCount"] == 1
        assert result.data["post"]["isLikedByMe"] is False

        # Query as user who did like
        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["post"]["likeCount"] == 1
        assert result.data["post"]["isLikedByMe"] is True

    def test_like_count_visible_to_anonymous(self, blog_post):
        """Test that like_count is visible to anonymous users."""
        User = get_user_model()
        liker = User.objects.create_user(
            email="liker@example.com", username="liker", password="TestPass123!"
        )
        Like.objects.create(post=blog_post, user=liker)

        query = f"""
            query {{
                post(id: "{blog_post.id}") {{
                    likeCount
                    isLikedByMe
                }}
            }}
        """

        context = create_context()  # Anonymous user
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["post"]["likeCount"] == 1
        assert result.data["post"]["isLikedByMe"] is False

    def test_multiple_likes(self, blog_post):
        """Test like_count with multiple users liking."""
        User = get_user_model()
        user1 = User.objects.create_user(
            email="user1@example.com", username="user1", password="TestPass123!"
        )
        user2 = User.objects.create_user(
            email="user2@example.com", username="user2", password="TestPass123!"
        )
        user3 = User.objects.create_user(
            email="user3@example.com", username="user3", password="TestPass123!"
        )

        Like.objects.create(post=blog_post, user=user1)
        Like.objects.create(post=blog_post, user=user2)
        Like.objects.create(post=blog_post, user=user3)

        query = f"""
            query {{
                post(id: "{blog_post.id}") {{
                    likeCount
                }}
            }}
        """

        context = create_context()
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["post"]["likeCount"] == 3
