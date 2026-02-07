"""Tests for blog GraphQL queries."""

from django.utils import timezone

import pytest

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
        email="test@example.com", username="testuser", password="TestPass123!"
    )


@pytest.fixture
def author(user):
    """Create a test author."""
    return Author.objects.create(user=user, bio="Test bio")


@pytest.fixture
def published_post(author):
    """Create a published blog post."""
    return BlogPost.objects.create(
        title="Published Post",
        content="This is published content.",
        author=author,
        status=BlogPost.Status.PUBLISHED,
        published_at=timezone.now(),
    )


@pytest.fixture
def draft_post(author):
    """Create a draft blog post."""
    return BlogPost.objects.create(
        title="Draft Post",
        content="This is draft content.",
        author=author,
        status=BlogPost.Status.DRAFT,
    )


@pytest.mark.django_db
class TestPostQueries:
    """Test cases for blog post queries."""

    def test_query_post_by_id(self, published_post):
        """Test querying a post by ID."""
        query = f"""
            query {{
                post(id: "{published_post.id}") {{
                    id
                    title
                    content
                    status
                }}
            }}
        """

        result = schema.execute(query)

        assert result.errors is None
        assert result.data["post"]["title"] == "Published Post"
        assert result.data["post"]["status"] == "published"

    def test_query_post_by_slug(self, published_post):
        """Test querying a post by slug."""
        query = f"""
            query {{
                post(slug: "{published_post.slug}") {{
                    id
                    title
                    slug
                }}
            }}
        """

        result = schema.execute(query)

        assert result.errors is None
        assert result.data["post"]["title"] == "Published Post"
        assert result.data["post"]["slug"] == published_post.slug

    def test_query_nonexistent_post(self):
        """Test querying a post that doesn't exist."""
        query = """
            query {
                post(id: "99999") {
                    id
                    title
                }
            }
        """

        result = schema.execute(query)

        assert result.errors is None
        assert result.data["post"] is None

    def test_query_published_posts(self, published_post, draft_post):
        """Test querying only published posts."""
        query = """
            query {
                publishedPosts {
                    edges {
                        node {
                            id
                            title
                            status
                        }
                    }
                }
            }
        """

        result = schema.execute(query)

        assert result.errors is None
        posts = result.data["publishedPosts"]["edges"]

        # Should only contain published posts
        titles = [p["node"]["title"] for p in posts]
        assert "Published Post" in titles
        assert "Draft Post" not in titles

    def test_query_all_posts_with_status_filter(self, published_post, draft_post):
        """Test filtering posts by status."""
        query = """
            query {
                allPosts(status: "draft") {
                    edges {
                        node {
                            title
                            status
                        }
                    }
                }
            }
        """

        result = schema.execute(query)

        assert result.errors is None
        posts = result.data["allPosts"]["edges"]

        for post in posts:
            assert post["node"]["status"] == "draft"

    def test_query_posts_with_search(self, author):
        """Test searching posts by title and content."""
        # Create posts with specific content
        BlogPost.objects.create(
            title="Python Tutorial",
            content="Learn Python programming.",
            author=author,
            status=BlogPost.Status.PUBLISHED,
        )
        BlogPost.objects.create(
            title="JavaScript Guide",
            content="JavaScript for beginners.",
            author=author,
            status=BlogPost.Status.PUBLISHED,
        )

        query = """
            query {
                publishedPosts(search: "Python") {
                    edges {
                        node {
                            title
                        }
                    }
                }
            }
        """

        result = schema.execute(query)

        assert result.errors is None
        posts = result.data["publishedPosts"]["edges"]
        assert len(posts) == 1
        assert posts[0]["node"]["title"] == "Python Tutorial"


@pytest.mark.django_db
class TestAuthorQueries:
    """Test cases for author queries."""

    def test_query_author_by_id(self, author):
        """Test querying an author by ID."""
        query = f"""
            query {{
                author(id: "{author.id}") {{
                    id
                    bio
                    user {{
                        username
                    }}
                }}
            }}
        """

        result = schema.execute(query)

        assert result.errors is None
        assert result.data["author"]["bio"] == "Test bio"
        assert result.data["author"]["user"]["username"] == "testuser"

    def test_query_all_authors(self, author):
        """Test querying all authors."""
        query = """
            query {
                allAuthors {
                    edges {
                        node {
                            id
                            bio
                        }
                    }
                }
            }
        """

        result = schema.execute(query)

        assert result.errors is None
        assert len(result.data["allAuthors"]["edges"]) >= 1

    def test_query_author_with_post_count(self, author, published_post, draft_post):
        """Test author post count includes only published posts."""
        query = f"""
            query {{
                author(id: "{author.id}") {{
                    id
                    postCount
                }}
            }}
        """

        result = schema.execute(query)

        assert result.errors is None
        # Should only count the published post
        assert result.data["author"]["postCount"] == 1


@pytest.mark.django_db
class TestCommentQueries:
    """Test cases for comment queries."""

    def test_query_comments_by_post(self, published_post, user):
        """Test querying comments for a specific post."""
        # Create comments
        Comment.objects.create(post=published_post, author=user, content="Comment 1")
        Comment.objects.create(post=published_post, author=user, content="Comment 2")

        query = f"""
            query {{
                allComments(postId: "{published_post.id}") {{
                    edges {{
                        node {{
                            content
                            author {{
                                username
                            }}
                        }}
                    }}
                }}
            }}
        """

        result = schema.execute(query)

        assert result.errors is None
        comments = result.data["allComments"]["edges"]
        assert len(comments) == 2

    def test_query_approved_comments_only(self, published_post, user):
        """Test filtering comments by approval status."""
        Comment.objects.create(
            post=published_post, author=user, content="Approved", is_approved=True
        )
        Comment.objects.create(
            post=published_post, author=user, content="Not Approved", is_approved=False
        )

        query = """
            query {
                allComments(isApproved: true) {
                    edges {
                        node {
                            content
                            isApproved
                        }
                    }
                }
            }
        """

        result = schema.execute(query)

        assert result.errors is None
        comments = result.data["allComments"]["edges"]

        for comment in comments:
            assert comment["node"]["isApproved"] is True
