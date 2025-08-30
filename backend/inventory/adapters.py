from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class SocialAccountRequiresLocalAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # If the social account is already linked to a user, nothing to do
        if sociallogin.is_existing:
            return

        # Try to get an email (some providers may not return one)
        email = sociallogin.user.email

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ImmediateHttpResponse(redirect("account_not_recognized"))

        # Link the social account to the existing local user
        sociallogin.connect(request, user)
