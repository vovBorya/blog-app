"""Admin configuration for blog models."""

from django.contrib import admin

from .models import Author, BlogPost, Comment


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """Admin interface for Author model."""

    list_display = ("user", "bio_preview", "post_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email", "bio")
    readonly_fields = ("created_at", "updated_at")

    def bio_preview(self, obj):
        """Return a truncated bio for list display."""
        return obj.bio[:50] + "..." if len(obj.bio) > 50 else obj.bio

    bio_preview.short_description = "Bio"


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """Admin interface for BlogPost model."""

    list_display = (
        "title",
        "author",
        "status",
        "comment_count",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "author", "created_at", "published_at")
    search_fields = ("title", "content", "author__user__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "content", "excerpt")}),
        ("Media", {"fields": ("featured_image_url",), "classes": ("collapse",)}),
        ("Publication", {"fields": ("status", "published_at")}),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    actions = ["publish_posts", "unpublish_posts"]

    @admin.action(description="Publish selected posts")
    def publish_posts(self, request, queryset):
        """Publish selected blog posts."""
        count = 0
        for post in queryset:
            post.publish()
            count += 1
        self.message_user(request, f"{count} post(s) published.")

    @admin.action(description="Unpublish selected posts")
    def unpublish_posts(self, request, queryset):
        """Unpublish selected blog posts."""
        queryset.update(status=BlogPost.Status.DRAFT)
        self.message_user(request, f"{queryset.count()} post(s) unpublished.")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comment model."""

    list_display = (
        "content_preview",
        "author",
        "post",
        "is_approved",
        "is_reply",
        "created_at",
    )
    list_filter = ("is_approved", "created_at")
    search_fields = ("content", "author__username", "post__title")
    readonly_fields = ("created_at", "updated_at")

    actions = ["approve_comments", "disapprove_comments"]

    def content_preview(self, obj):
        """Return a truncated content for list display."""
        return obj.content[:75] + "..." if len(obj.content) > 75 else obj.content

    content_preview.short_description = "Content"

    def is_reply(self, obj):
        """Return whether the comment is a reply."""
        return obj.is_reply

    is_reply.boolean = True
    is_reply.short_description = "Reply"

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        """Approve selected comments."""
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} comment(s) approved.")

    @admin.action(description="Disapprove selected comments")
    def disapprove_comments(self, request, queryset):
        """Disapprove selected comments."""
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} comment(s) disapproved.")
