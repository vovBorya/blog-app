# Blog API with GraphQL

A modern blog API built with Django and GraphQL, featuring user authentication, blog posts, comments, and a complete CI/CD pipeline.

## Tech Stack

- **Backend**: Python 3.11, Django 4.2+
- **API**: GraphQL with Graphene-Django
- **Database**: PostgreSQL 15
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Testing**: pytest with coverage

## Features

- User registration and authentication with JWT
- CRUD operations for blog posts
- Comment system with nested replies
- Author profiles
- GraphQL queries with filtering, search, and pagination
- Comprehensive test suite
- Docker containerization
- CI/CD pipeline with linting, testing, and security checks

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd blog-app
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Start the application:
```bash
cd docker
docker-compose up --build
```

4. Run migrations (in a new terminal):
```bash
docker-compose exec web python manage.py migrate
```

5. Create a superuser (optional), used in admin app:
```bash
docker-compose exec web python manage.py createsuperuser
```

6. Seed sample data (optional):
```bash
docker-compose exec web python manage.py seed_data
```

The API is now available at:
- **GraphQL Playground**: http://localhost:8000/graphql/
- **Admin Panel**: http://localhost:8000/admin/
- **Health Check**: http://localhost:8000/health/

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `True` |
| `SECRET_KEY` | Django secret key | Required in production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `localhost,127.0.0.1` |
| `POSTGRES_DB` | PostgreSQL database name | `blog_db` |
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `postgres` |
| `POSTGRES_HOST` | PostgreSQL host | `db` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `JWT_EXPIRATION_DELTA_MINUTES` | JWT token expiration | `60` |
| `JWT_REFRESH_EXPIRATION_DAYS` | JWT refresh token expiration | `7` |

## GraphQL API Examples

### Authentication

**Sign Up:**
```graphql
mutation {
  signUp(input: {
    email: "user@example.com"
    username: "johndoe"
    password: "SecurePass123!"
    firstName: "John"
    lastName: "Doe"
  }) {
    success
    user {
      id
      email
      username
    }
    token
  }
}
```

**Sign In:**
```graphql
mutation {
  signIn(input: {
    email: "user@example.com"
    password: "SecurePass123!"
  }) {
    success
    user {
      id
      email
    }
    token
  }
}
```

**Get Current User:**
```graphql
query {
  me {
    id
    email
    username
    firstName
    lastName
  }
}
```

### Blog Posts

**Create Post:**
```graphql
mutation {
  createPost(input: {
    title: "My First Post"
    content: "This is the content..."
    status: "draft"
  }) {
    success
    post {
      id
      title
      slug
      status
    }
  }
}
```

**Query Published Posts:**
```graphql
query {
  publishedPosts(first: 10, search: "python") {
    edges {
      node {
        id
        title
        slug
        excerpt
        publishedAt
        author {
          user {
            username
          }
        }
        commentCount
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

**Get Single Post:**
```graphql
query {
  post(slug: "my-first-post") {
    id
    title
    content
    author {
      bio
      user {
        fullName
      }
    }
  }
}
```

### Comments

**Create Comment:**
```graphql
mutation {
  createComment(input: {
    postId: "1"
    content: "Great post!"
  }) {
    success
    comment {
      id
      content
      author {
        username
      }
    }
  }
}
```

## Development

### Running Tests

```bash
# Run all tests
docker-compose exec web pytest

# Run with coverage
docker-compose exec web pytest --cov=. --cov-report=html

# Run specific test file
docker-compose exec web pytest users/tests/test_auth.py -v
```

### Code Quality

```bash
# Format code with Black
docker-compose exec web black .

# Sort imports
docker-compose exec web isort .

# Lint with flake8
docker-compose exec web flake8 .

# Type checking (optional)
docker-compose exec web mypy .
```

### Database Commands

```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Seed sample data
docker-compose exec web python manage.py seed_data --users 10 --posts 50 --comments 100

# Clear and reseed
docker-compose exec web python manage.py seed_data --clear
```

## Project Structure

```
blog-app/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline
│       └── docker-build.yml    # Docker build pipeline
├── app/
│   ├── blog/
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── seed_data.py
│   │   ├── migrations/
│   │   ├── schema/
│   │   │   ├── mutations.py
│   │   │   ├── queries.py
│   │   │   └── types.py
│   │   ├── tests/
│   │   ├── admin.py
│   │   └── models.py
│   ├── core/
│   │   ├── schema.py           # Root GraphQL schema
│   │   ├── settings.py
│   │   └── urls.py
│   ├── users/
│   │   ├── migrations/
│   │   ├── schema/
│   │   │   ├── mutations.py
│   │   │   ├── queries.py
│   │   │   └── types.py
│   │   ├── tests/
│   │   ├── admin.py
│   │   └── models.py
│   ├── conftest.py
│   └── manage.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env.example
├── .gitignore
├── pyproject.toml
├── pytest.ini
└── README.md
```

## CI/CD Pipeline

The project includes GitHub Actions workflows for:

1. **CI Pipeline** (`ci.yml`):
   - Code linting (Black, isort, flake8)
   - Security scanning (Safety, Bandit)
   - Unit and integration tests with PostgreSQL
   - Coverage reporting
   - Migration validation

2. **Docker Build** (`docker-build.yml`):
   - Multi-stage Docker builds
   - Push to GitHub Container Registry
   - Automatic tagging based on branches and tags

## API Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

To get a token, use the `signIn` mutation and include the returned token in subsequent requests.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linting (`black . && isort . && flake8 .`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is for learning purposes. Feel free to use and modify as needed.
