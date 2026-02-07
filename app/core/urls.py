"""
URL configuration for blog_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import GraphQLView


def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    Returns service status and database connectivity.
    """
    from django.db import connection

    status = {
        "status": "healthy",
        "service": "blog-api",
    }

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["database"] = "connected"
    except Exception as e:
        status["status"] = "unhealthy"
        status["database"] = f"error: {str(e)}"
        return JsonResponse(status, status=503)

    return JsonResponse(status)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path("health/", health_check, name="health_check"),
]
