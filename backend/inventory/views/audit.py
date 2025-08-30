"""
Audit logging views for the inventory application.

This module handles displaying and managing audit logs that track
all changes made to inventory items, categories, and user accounts.
"""

import json
from typing import Any, cast
from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required, permission_required
from inventory.models import AuditEvent


@login_required
@permission_required('inventory.view_auditevent', raise_exception=True)
def audit_log_list_view(request):
    """
    Display a list of all audit events in the system.
    
    Shows all audit events with related user information, ordered by creation date.
    Each event includes before/after state data serialized as JSON.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered audit log template with events list
        
    Raises:
        PermissionDenied: If user doesn't have view_auditevent permission
    """
    # Fetch all audit events with related user data for efficiency
    events = AuditEvent.objects.all().select_related("user").order_by('-created_at')
    events = cast(list[Any], events)

    # Prepare data for the template by serializing event data
    for event in events:
        event.json_data = json.dumps({
            'before': event.before,
            'after': event.after,
        })
        
    context = {
        'events': events,
    }
    
    template = loader.get_template("audit.html")
    return HttpResponse(template.render(context, request))