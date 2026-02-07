"""
Management command to seed the database with sample data.

Creates sample users, authors, blog posts, and comments for development and testing.
"""

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from faker import Faker

from blog.models import Author, BlogPost, Comment

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    """Seed database with sample data for development."""

    help = "Seed database with sample users, authors, posts, and comments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=5,
            help="Number of users to create (default: 5)",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=20,
            help="Number of blog posts to create (default: 20)",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=50,
            help="Number of comments to create (default: 50)",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing data before seeding"
        )

    def handle(self, *args, **options):
        num_users = options["users"]
        num_posts = options["posts"]
        num_comments = options["comments"]
        clear = options["clear"]

        if clear:
            self.stdout.write("Clearing existing data...")
            Comment.objects.all().delete()
            BlogPost.objects.all().delete()
            Author.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS("Data cleared!"))

        # Create users and authors
        self.stdout.write(f"Creating {num_users} users and authors...")
        authors = self._create_users_and_authors(num_users)
        self.stdout.write(self.style.SUCCESS(f"Created {len(authors)} authors"))

        # Create blog posts
        self.stdout.write(f"Creating {num_posts} blog posts...")
        posts = self._create_posts(authors, num_posts)
        self.stdout.write(self.style.SUCCESS(f"Created {len(posts)} posts"))

        # Create comments
        self.stdout.write(f"Creating {num_comments} comments...")
        comments = self._create_comments(posts, num_comments)
        self.stdout.write(self.style.SUCCESS(f"Created {len(comments)} comments"))

        self.stdout.write(self.style.SUCCESS("\nSeeding completed successfully!"))
        self._print_summary(authors, posts, comments)

    def _create_users_and_authors(self, count):
        """Create sample users with author profiles."""
        authors = []

        for i in range(count):
            # Create unique username and email
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
            email = f"{username}@example.com"

            # Skip if user already exists
            if User.objects.filter(username=username).exists():
                continue
            if User.objects.filter(email=email).exists():
                continue

            user = User.objects.create_user(
                username=username,
                email=email,
                password="TestPass123!",
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )

            author = Author.objects.create(
                user=user,
                bio=fake.paragraph(nb_sentences=3),
                avatar_url=f"https://i.pravatar.cc/150?u={username}",
                website=fake.url() if random.random() > 0.5 else None,
            )
            authors.append(author)

            self.stdout.write(f"  Created author: {user.get_full_name()} ({username})")

        return authors

    def _create_posts(self, authors, count):
        """Create sample blog posts."""
        posts = []

        if not authors:
            # Get existing authors if none were created
            authors = list(Author.objects.all())

        if not authors:
            self.stdout.write(self.style.WARNING("No authors found. Cannot create posts."))
            return posts

        statuses = [BlogPost.Status.DRAFT, BlogPost.Status.PUBLISHED]
        status_weights = [0.3, 0.7]  # 70% published, 30% draft

        for i in range(count):
            author = random.choice(authors)
            status = random.choices(statuses, weights=status_weights)[0]

            # Generate a realistic blog post
            title = fake.sentence(nb_words=random.randint(4, 8)).rstrip(".")

            # Generate multiple paragraphs for content
            paragraphs = [
                fake.paragraph(nb_sentences=random.randint(3, 7))
                for _ in range(random.randint(3, 6))
            ]
            content = "\n\n".join(paragraphs)

            # Set published_at for published posts
            published_at = None
            if status == BlogPost.Status.PUBLISHED:
                # Random date in the past year
                days_ago = random.randint(1, 365)
                published_at = timezone.now() - timezone.timedelta(days=days_ago)

            post = BlogPost.objects.create(
                title=title,
                content=content,
                excerpt=fake.paragraph(nb_sentences=2),
                author=author,
                status=status,
                featured_image_url=f"https://picsum.photos/seed/{fake.uuid4()}/800/400",
                published_at=published_at,
            )
            posts.append(post)

        return posts

    def _create_comments(self, posts, count):
        """Create sample comments on posts."""
        comments = []

        if not posts:
            # Get existing published posts if none were created
            posts = list(BlogPost.objects.filter(status=BlogPost.Status.PUBLISHED))

        if not posts:
            self.stdout.write(self.style.WARNING("No posts found. Cannot create comments."))
            return comments

        # Get all users for comment authors
        users = list(User.objects.filter(is_active=True))

        if not users:
            self.stdout.write(self.style.WARNING("No users found. Cannot create comments."))
            return comments

        for i in range(count):
            post = random.choice(posts)
            author = random.choice(users)

            # 90% chance of being approved
            is_approved = random.random() > 0.1

            comment = Comment.objects.create(
                post=post,
                author=author,
                content=fake.paragraph(nb_sentences=random.randint(1, 3)),
                is_approved=is_approved,
            )
            comments.append(comment)

            # 20% chance to create a reply to this comment
            if random.random() > 0.8 and len(comments) > 1:
                reply_author = random.choice(users)
                reply = Comment.objects.create(
                    post=post,
                    author=reply_author,
                    content=fake.paragraph(nb_sentences=random.randint(1, 2)),
                    parent=comment,
                    is_approved=True,
                )
                comments.append(reply)

        return comments

    def _print_summary(self, authors, posts, comments):
        """Print a summary of created data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Users/Authors: {len(authors)}")
        self.stdout.write(f"Blog Posts: {len(posts)}")

        published_posts = len([p for p in posts if p.status == BlogPost.Status.PUBLISHED])
        draft_posts = len(posts) - published_posts
        self.stdout.write(f"  - Published: {published_posts}")
        self.stdout.write(f"  - Drafts: {draft_posts}")

        self.stdout.write(f"Comments: {len(comments)}")
        approved_comments = len([c for c in comments if c.is_approved])
        self.stdout.write(f"  - Approved: {approved_comments}")
        self.stdout.write(f"  - Pending: {len(comments) - approved_comments}")

        self.stdout.write("\nTest Credentials:")
        self.stdout.write("  Password for all seeded users: TestPass123!")
        self.stdout.write("=" * 50)
