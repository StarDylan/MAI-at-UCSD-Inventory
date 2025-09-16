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
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView
from django.db.models import Q
from inventory.models import AuditEvent


class AuditLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Display a paginated list of audit events with search functionality.
    
    Shows audit events with related user information, ordered by creation date.
    Supports searching by user, event description, or entity type.
    """
    model = AuditEvent
    template_name = 'audit/list.html'
    context_object_name = 'events'
    permission_required = 'inventory.view_auditevent'
    paginate_by = 50  # Show 50 events per page
    
    def get_queryset(self):
        search_query = self.request.GET.get('search', '').strip()
        
        # Base queryset with related user data for efficiency
        queryset = AuditEvent.objects.select_related("user").order_by('-created_at')
        
        # Add search filtering if provided
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(event__icontains=search_query) |
                Q(entity_type__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        
        # Prepare JSON data for each event
        for event in context['events']:
            event.json_data = json.dumps({
                'before': event.before,
                'after': event.after,
            })
        
        return context


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
    
    template = loader.get_template("audit/list.html")
    return HttpResponse(template.render(context, request))