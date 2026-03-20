"""Project-level helper views (next-url helper, custom 404)."""

from django.shortcuts import render
from django.http import HttpResponse

def get_next_url(request):
    """Return the referring URL if available, otherwise home."""
    return request.META.get("HTTP_REFERER") or "/"

# def custom_404(request, exception):
#     return HttpResponse("Custom 404 working")

def custom_404(request, exception):
    """Render project-wide 404 page."""
    return render(request, "home/404.html", {})
