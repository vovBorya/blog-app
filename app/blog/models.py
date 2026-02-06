"""
Blog models for the blog application.

Contains Author, BlogPost, and Comment models with proper relationships.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Author(models.Model):
    """
    Author profile linked to a User.

    Extends user information with author-specific fields like bio and avatar.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="author_profile",
        help_text="The user associated with this author profile.",
    )
    bio = models.TextField(
        "biography",
        max_length=1000,
        blank=True,
        help_text="A short biography of the author.",
    )
    avatar_url = models.URLField(
        "avatar URL",
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to the author avatar image.",
    )
    website = models.URLField(
        "website",
        max_length=200,
        blank=True,
        null=True,
        help_text="Author personal website or portfolio.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "authors"
        verbose_name = "Author"
        verbose_name_plural = "Authors"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username})"

    @property
    def post_count(self):
        """Return the number of published posts by this author."""
        return self.posts.filter(status=BlogPost.Status.PUBLISHED).count()


class BlogPost(models.Model):
    """
    Blog post model.

    Represents a blog article with title, content, author, and status.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField("title", max_length=200, help_text="The title of the blog post.")
    slug = models.SlugField(
        "slug",
        max_length=250,
        unique=True,
        help_text="URL-friendly version of the title.",
    )
    content = models.TextField("content", help_text="The main content of the blog post.")
    excerpt = models.TextField(
        "excerpt", max_length=500, blank=True, help_text="A short summary of the post."
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="posts",
        help_text="The author of this blog post.",
    )
    status = models.CharField(
        "status",
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Publication status of the post.",
    )
    featured_image_url = models.URLField(
        "featured image URL",
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to the featured image for the post.",
    )
    published_at = models.DateTimeField(
        "published at",
        null=True,
        blank=True,
        db_index=True,
        help_text="When the post was published.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blog_posts"
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["author", "status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save to auto-generate slug and set published_at."""
        if not self.slug:
            self.slug = self._generate_unique_slug()

        # Set published_at when status changes to published
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        """Generate a unique slug from the title."""
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1

        while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    @property
    def comment_count(self):
        """Return the number of approved comments on this post."""
        return self.comments.filter(is_approved=True).count()

    def publish(self):
        """Publish the blog post."""
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.save()

    def unpublish(self):
        """Unpublish the blog post (set to draft)."""
        self.status = self.Status.DRAFT
        self.save()


class Comment(models.Model):
    """
    Comment model for blog posts.

    Allows users to comment on blog posts with moderation support.
    """

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="The blog post this comment belongs to.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="The user who wrote this comment.",
    )
    content = models.TextField("content", max_length=2000, help_text="The comment content.")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent comment for nested replies.",
    )
    is_approved = models.BooleanField(
        "approved",
        default=True,
        db_index=True,
        help_text="Whether the comment is approved for display.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["post", "is_approved", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def __str__(self):
        return f'Comment by {self.author.username} on "{self.post.title}"'

    @property
    def is_reply(self):
        """Check if this comment is a reply to another comment."""
        return self.parent is not None
