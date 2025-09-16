"""
Template tags to fix compatibility issues with crispy forms and Django 5.x
"""
from django import template
from django.forms import CheckboxInput

register = template.Library()

@register.filter
def is_checkbox_safe(field):
    """
    Safe version of is_checkbox that works with Django 5.x
    """
    try:
        # Try the standard way first
        if hasattr(field, 'field') and hasattr(field.field, 'widget'):
            return isinstance(field.field.widget, CheckboxInput)
        # For BoundWidget objects
        elif hasattr(field, 'widget'):
            return isinstance(field.widget, CheckboxInput)
        # Fallback
        else:
            return False
    except AttributeError:
        return False