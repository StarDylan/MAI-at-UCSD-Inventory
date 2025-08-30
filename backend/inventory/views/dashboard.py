"""
Dashboard and main navigation views for the inventory application.

This module contains views that handle the main dashboard, home page,
and general navigation functionality of the inventory system.
"""

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import loader
from django.conf import settings


def index_view(request):
    """
    Home page view that redirects to the dashboard.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponseRedirect: Redirect to dashboard page
    """
    return HttpResponseRedirect(reverse("dashboard"))


def dashboard_view(request):
    """
    Main dashboard view for the inventory system.
    
    Displays the main dashboard interface with different functionality
    based on whether the system is in DEBUG mode and configured properly.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered dashboard template
    """
    # Check if system is in DEBUG mode and Google OAuth is configured
    if settings.DEBUG and settings.SOCIALACCOUNT_PROVIDERS.get('google')["APP"]["client_id"] == "":
        context = {
            "always_admin": True
        }
    else:
        context = {
            "always_admin": False
        }
    
    template = loader.get_template("dashboard/index.html")
    return HttpResponse(template.render(context, request))


def profile_view(request):
    """
    User profile view that redirects to dashboard.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponseRedirect: Redirect to dashboard page
    """
    return HttpResponseRedirect(reverse("dashboard"))