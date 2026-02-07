"""Additional tests to improve code coverage."""

from unittest.mock import Mock

from django.utils import timezone

import pytest

from blog.models import Author, BlogPost, Comment
from core.schema import schema


def get_user_model():
    """Lazy-load User model."""
    from django.contrib.auth import get_user_model as _get_user_model

    return _get_user_model()


def create_context(user=None):
    """Create a mock context with optional user."""
    from django.contrib.auth.models import AnonymousUser

    context = Mock()
    context.user = user if user else AnonymousUser()
    return context


@pytest.fixture
def user():
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email="test@example.com",
        username="testuser",
        password="TestPass123!",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def author(user):
    """Create a test author."""
    return Author.objects.create(user=user, bio="Test bio", website="https://example.com")


@pytest.fixture
def blog_post(author):
    """Create a test blog post."""
    return BlogPost.objects.create(
        title="Test Post",
        content="Test content.",
        author=author,
        status=BlogPost.Status.DRAFT,
    )


@pytest.mark.django_db
class TestUpdateAuthorMutation:
    """Test cases for UpdateAuthor mutation."""

    def test_update_author_success(self, author):
        """Test successfully updating author profile."""
        query = """
            mutation {
                updateAuthor(
                    bio: "Updated bio"
                    website: "https://newsite.com"
                ) {
                    success
                    errors
                    author {
                        bio
                        website
                    }
                }
            }
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["updateAuthor"]["success"] is True
        assert result.data["updateAuthor"]["author"]["bio"] == "Updated bio"
        assert result.data["updateAuthor"]["author"]["website"] == "https://newsite.com"

    def test_update_author_no_profile(self, user):
        """Test updating when no author profile exists."""
        query = """
            mutation {
                updateAuthor(bio: "New bio") {
                    success
                    errors
                }
            }
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["updateAuthor"]["success"] is False
        assert "do not have an author profile" in str(result.data["updateAuthor"]["errors"]).lower()


@pytest.mark.django_db
class TestUnpublishPostMutation:
    """Test cases for UnpublishPost mutation."""

    def test_unpublish_post_success(self, author):
        """Test successfully unpublishing a post."""
        # Create a published post
        post = BlogPost.objects.create(
            title="Published Post",
            content="Content",
            author=author,
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )

        query = f"""
            mutation {{
                unpublishPost(id: "{post.id}") {{
                    success
                    errors
                    post {{
                        status
                    }}
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["unpublishPost"]["success"] is True
        assert result.data["unpublishPost"]["post"]["status"] == "draft"

    def test_unpublish_post_not_found(self, author):
        """Test unpublishing non-existent post."""
        query = """
            mutation {
                unpublishPost(id: "99999") {
                    success
                    errors
                }
            }
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["unpublishPost"]["success"] is False
        assert "not found" in str(result.data["unpublishPost"]["errors"]).lower()

    def test_unpublish_post_no_permission(self, blog_post):
        """Test unpublishing post without permission."""
        User = get_user_model()
        other_user = User.objects.create_user(
            email="other@example.com", username="otheruser", password="TestPass123!"
        )

        query = f"""
            mutation {{
                unpublishPost(id: "{blog_post.id}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(other_user)
        result = schema.execute(query, context_value=context)

        assert result.data["unpublishPost"]["success"] is False
        assert "permission" in str(result.data["unpublishPost"]["errors"]).lower()


@pytest.mark.django_db
class TestUpdateCommentMutation:
    """Test cases for UpdateComment mutation."""

    def test_update_comment_success(self, user, blog_post):
        """Test successfully updating a comment."""
        comment = Comment.objects.create(post=blog_post, author=user, content="Original comment")

        query = f"""
            mutation {{
                updateComment(
                    id: "{comment.id}"
                    content: "Updated comment"
                ) {{
                    success
                    errors
                    comment {{
                        content
                    }}
                }}
            }}
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["updateComment"]["success"] is True
        assert result.data["updateComment"]["comment"]["content"] == "Updated comment"

    def test_update_comment_not_found(self, user):
        """Test updating non-existent comment."""
        query = """
            mutation {
                updateComment(id: "99999" content: "New") {
                    success
                    errors
                }
            }
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["updateComment"]["success"] is False
        assert "not found" in str(result.data["updateComment"]["errors"]).lower()

    def test_update_comment_not_owner(self, user, blog_post):
        """Test updating comment as non-owner."""
        User = get_user_model()
        other_user = User.objects.create_user(
            email="other@example.com", username="otheruser", password="TestPass123!"
        )

        comment = Comment.objects.create(post=blog_post, author=other_user, content="Original")

        query = f"""
            mutation {{
                updateComment(id: "{comment.id}" content: "Hacked") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["updateComment"]["success"] is False
        assert "your own" in str(result.data["updateComment"]["errors"]).lower()

    def test_update_comment_empty_content(self, user, blog_post):
        """Test updating comment with empty content."""
        comment = Comment.objects.create(post=blog_post, author=user, content="Original")

        query = f"""
            mutation {{
                updateComment(id: "{comment.id}" content: "") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["updateComment"]["success"] is False
        assert "required" in str(result.data["updateComment"]["errors"]).lower()

    def test_update_comment_too_long(self, user, blog_post):
        """Test updating comment with content too long."""
        comment = Comment.objects.create(post=blog_post, author=user, content="Original")

        long_content = "x" * 2001  # Over 2000 char limit

        query = f"""
            mutation {{
                updateComment(id: "{comment.id}" content: "{long_content}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["updateComment"]["success"] is False
        assert "2000" in str(result.data["updateComment"]["errors"])


@pytest.mark.django_db
class TestApproveCommentMutation:
    """Test cases for ApproveComment mutation."""

    def test_approve_comment_as_post_author(self, author, blog_post, user):
        """Test approving comment as post author."""
        User = get_user_model()
        commenter = User.objects.create_user(
            email="commenter@example.com", username="commenter", password="TestPass123!"
        )

        comment = Comment.objects.create(
            post=blog_post, author=commenter, content="Test comment", is_approved=False
        )

        query = f"""
            mutation {{
                approveComment(id: "{comment.id}" isApproved: true) {{
                    success
                    errors
                    comment {{
                        isApproved
                    }}
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["approveComment"]["success"] is True
        assert result.data["approveComment"]["comment"]["isApproved"] is True

    def test_approve_comment_no_permission(self, blog_post):
        """Test approving comment without permission."""
        User = get_user_model()
        random_user = User.objects.create_user(
            email="random@example.com", username="randomuser", password="TestPass123!"
        )

        commenter = User.objects.create_user(
            email="commenter@example.com", username="commenter", password="TestPass123!"
        )

        comment = Comment.objects.create(post=blog_post, author=commenter, content="Test comment")

        query = f"""
            mutation {{
                approveComment(id: "{comment.id}" isApproved: false) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(random_user)
        result = schema.execute(query, context_value=context)

        assert result.data["approveComment"]["success"] is False
        assert "permission" in str(result.data["approveComment"]["errors"]).lower()

    def test_approve_comment_not_found(self, author):
        """Test approving non-existent comment."""
        query = """
            mutation {
                approveComment(id: "99999" isApproved: true) {
                    success
                    errors
                }
            }
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["approveComment"]["success"] is False
        assert "not found" in str(result.data["approveComment"]["errors"]).lower()


@pytest.mark.django_db
class TestDeleteCommentPermissions:
    """Test cases for delete comment permissions."""

    def test_delete_comment_as_post_author(self, author, blog_post):
        """Test deleting comment as post author."""
        User = get_user_model()
        commenter = User.objects.create_user(
            email="commenter@example.com", username="commenter", password="TestPass123!"
        )

        comment = Comment.objects.create(post=blog_post, author=commenter, content="Test comment")

        query = f"""
            mutation {{
                deleteComment(id: "{comment.id}") {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.errors is None
        assert result.data["deleteComment"]["success"] is True


@pytest.mark.django_db
class TestCreatePostValidations:
    """Test additional create post validations."""

    def test_create_post_title_too_long(self, author):
        """Test creating post with title too long."""
        long_title = "x" * 201  # Over 200 char limit

        query = f"""
            mutation {{
                createPost(input: {{
                    title: "{long_title}"
                    content: "Content"
                }}) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["createPost"]["success"] is False
        assert "200" in str(result.data["createPost"]["errors"])

    def test_create_post_invalid_status(self, author):
        """Test creating post with invalid status."""
        query = """
            mutation {
                createPost(input: {
                    title: "Test"
                    content: "Content"
                    status: "invalid"
                }) {
                    success
                    errors
                }
            }
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["createPost"]["success"] is False
        assert "status" in str(result.data["createPost"]["errors"]).lower()


@pytest.mark.django_db
class TestUpdatePostValidations:
    """Test additional update post validations."""

    def test_update_post_title_too_long(self, author, blog_post):
        """Test updating post with title too long."""
        long_title = "x" * 201

        query = f"""
            mutation {{
                updatePost(
                    id: "{blog_post.id}"
                    input: {{
                        title: "{long_title}"
                    }}
                ) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["updatePost"]["success"] is False
        assert "200" in str(result.data["updatePost"]["errors"])

    def test_update_post_empty_content(self, author, blog_post):
        """Test updating post with empty content."""
        query = f"""
            mutation {{
                updatePost(
                    id: "{blog_post.id}"
                    input: {{
                        content: ""
                    }}
                ) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["updatePost"]["success"] is False
        assert "content" in str(result.data["updatePost"]["errors"]).lower()

    def test_update_post_invalid_status(self, author, blog_post):
        """Test updating post with invalid status."""
        query = f"""
            mutation {{
                updatePost(
                    id: "{blog_post.id}"
                    input: {{
                        status: "invalid"
                    }}
                ) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(author.user)
        result = schema.execute(query, context_value=context)

        assert result.data["updatePost"]["success"] is False
        assert "status" in str(result.data["updatePost"]["errors"]).lower()


@pytest.mark.django_db
class TestBlogPostSaveMethod:
    """Test BlogPost save method edge cases."""

    def test_auto_publish_date_on_first_publish(self, author):
        """Test that published_at is set automatically."""
        post = BlogPost.objects.create(
            title="Test", content="Content", author=author, status=BlogPost.Status.DRAFT
        )

        assert post.published_at is None

        # Change to published
        post.status = BlogPost.Status.PUBLISHED
        post.save()

        # Reload from DB
        post.refresh_from_db()
        assert post.published_at is not None

    def test_published_at_not_changed_on_resave(self, author):
        """Test that published_at is not changed on re-saving."""
        original_time = timezone.now()
        post = BlogPost.objects.create(
            title="Test",
            content="Content",
            author=author,
            status=BlogPost.Status.PUBLISHED,
            published_at=original_time,
        )

        # Update something else
        post.content = "New content"
        post.save()

        post.refresh_from_db()
        assert post.published_at == original_time


@pytest.mark.django_db
class TestCreateCommentValidations:
    """Test additional create comment validations."""

    def test_create_comment_with_invalid_parent(self, user, author):
        """Test creating comment with parent from different post."""
        post1 = BlogPost.objects.create(
            title="Post 1",
            content="Content",
            author=author,
            status=BlogPost.Status.PUBLISHED,
        )

        post2 = BlogPost.objects.create(
            title="Post 2",
            content="Content",
            author=author,
            status=BlogPost.Status.PUBLISHED,
        )

        parent_comment = Comment.objects.create(post=post1, author=user, content="Parent")

        query = f"""
            mutation {{
                createComment(input: {{
                    postId: "{post2.id}"
                    content: "Reply"
                    parentId: "{parent_comment.id}"
                }}) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["createComment"]["success"] is False
        assert "parent comment not found" in str(result.data["createComment"]["errors"]).lower()

    def test_create_comment_too_long(self, user, author):
        """Test creating comment with content too long."""
        post = BlogPost.objects.create(
            title="Test",
            content="Content",
            author=author,
            status=BlogPost.Status.PUBLISHED,
        )

        long_content = "x" * 2001

        query = f"""
            mutation {{
                createComment(input: {{
                    postId: "{post.id}"
                    content: "{long_content}"
                }}) {{
                    success
                    errors
                }}
            }}
        """

        context = create_context(user)
        result = schema.execute(query, context_value=context)

        assert result.data["createComment"]["success"] is False
        assert "2000" in str(result.data["createComment"]["errors"])
