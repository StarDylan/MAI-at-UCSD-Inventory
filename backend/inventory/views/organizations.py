"""
Organization management views for the inventory application.

This module handles CRUD operations for organizations which are
sources/suppliers of inventory items.
"""

from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import UpdateView, CreateView, ListView
from django.views.decorators.http import require_http_methods
import json

from inventory import models
from inventory.forms import OrganizationForm
from inventory.models import Organization, AuditEvent
from .utils import audit_log_state, audit_log_event


class OrganizationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all organizations"""
    model = Organization
    template_name = "organizations/list.html"
    context_object_name = "organizations"
    permission_required = 'inventory.view_organization'
    paginate_by = 25
    
    def get_queryset(self):
        return Organization.objects.all().order_by('name')


class OrganizationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new organization"""
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/create.html"
    permission_required = 'inventory.add_organization'
    success_url = reverse_lazy('organization_list')

    def form_valid(self, form):
        """Process valid form submission and log the creation."""
        before_state = audit_log_state(None)
        new_org = form.save(commit=True)
        after_state = audit_log_state(new_org)
        
        audit_log_event(
            self.request.user, 
            f"Created organization \"{new_org.name}\"", 
            before_state, 
            after_state
        )
        
        self.object = new_org
        messages.success(self.request, f'Organization "{new_org.name}" was successfully created.')
        return redirect(self.get_success_url())


class OrganizationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update organization information"""
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/edit.html"
    permission_required = 'inventory.change_organization'
    success_url = reverse_lazy('organization_list')

    def form_valid(self, form):
        """Process valid form submission and log the changes."""
        before_model = Organization.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        response = super().form_valid(form)
        
        after_state = audit_log_state(self.object)
        audit_log_event(
            self.request.user, 
            f"Updated organization \"{before_model.name}\"", 
            before_state, 
            after_state
        )
        
        messages.success(self.request, f'Organization "{self.object.name}" was successfully updated.')
        return response


@login_required
@permission_required('inventory.add_organization', raise_exception=True)
@require_http_methods(["POST"])
def organization_create_ajax(request):
    """
    AJAX endpoint for creating organizations from forms.
    
    Used when creating items and need to add a new organization
    without leaving the form.
    """
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        contact_email = data.get('contact_email', '').strip()
        contact_phone = data.get('contact_phone', '').strip()
        address = data.get('address', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Organization name is required'}, status=400)
        
        # Check if organization already exists
        if Organization.objects.filter(name=name).exists():
            return JsonResponse({'error': 'Organization with this name already exists'}, status=400)
        
        # Create the organization
        org = Organization.objects.create(
            name=name,
            description=description,
            contact_email=contact_email,
            contact_phone=contact_phone,
            address=address
        )
        
        # Log the creation
        audit_log_event(
            request.user, 
            f"Created organization \"{org.name}\" via AJAX", 
            audit_log_state(None), 
            audit_log_state(org)
        )
        
        return JsonResponse({
            'success': True,
            'organization': {
                'id': str(org.id),
                'name': org.name,
                'description': org.description,
                'contact_email': org.contact_email,
                'contact_phone': org.contact_phone,
                'address': org.address
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def organization_list_api(request):
    """
    API endpoint to get list of organizations for forms.
    
    Returns JSON list of organizations for use in select dropdowns.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    organizations = Organization.objects.all().order_by('name').values('id', 'name')
    return JsonResponse({'organizations': list(organizations)})