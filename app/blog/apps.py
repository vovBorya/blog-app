from django.apps import AppConfig


class BlogConfig(AppConfig):
    """Configuration for the blog application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'
    verbose_name = 'Blog Management'
