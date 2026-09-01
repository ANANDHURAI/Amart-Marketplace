"""Project-level custom 404 Function."""

from django.shortcuts import render


def custom_404(request, exception):
    """Render project-wide 404 page."""
    return render(request, "home/404.html", {})
