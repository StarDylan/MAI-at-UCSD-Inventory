"""
Authentication and authorization views for the inventory application.

This module handles user authentication, logout functionality, and
account recognition for social authentication.
"""

from typing import Any
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.conf import settings


def logout_view(request):
    """
    Handle user logout and redirect to home page.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponseRedirect: Redirect to home page after logout
    """
    logout(request)
    return redirect('home')


class AccountNotRecognizedView(TemplateView):
    """
    View displayed when a user's account is not recognized during authentication.
    
    This is typically shown when a user tries to log in with a social account
    that hasn't been registered in the system.
    """
    template_name = 'auth/not_found.html'


class GoogleLoginView(TemplateView):
    """
    View for Google OAuth login page.
    
    Provides the Google OAuth client ID to the template for authentication.
    """
    template_name = 'registration/google_login.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Add Google OAuth client ID to template context.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            dict: Template context with Google client ID
        """
        context = super().get_context_data(**kwargs)
        context['google_client_id'] = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
        return context