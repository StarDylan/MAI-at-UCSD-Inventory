"""
Subcategory management views for the inventory application.

This module handles CRUD operations for inventory subcategories,
including subcategory listing, creation, editing, and deletion functionality.
Subcategories are organizational units within categories.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView

from inventory import models
from inventory.forms import SubcategoryForm
from inventory.models import Subcategory
from .utils import audit_log_state, audit_log_event


@login_required
@permission_required('inventory.delete_subcategory', raise_exception=True)
def subcategory_delete_list_view(request):
    """
    Display a list of subcategories that can be deleted.
    
    Only shows subcategories that have no items, as subcategories
    with items cannot be safely deleted without data loss.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with deletable subcategories
        
    Raises:
        PermissionDenied: If user doesn't have delete_subcategory permission
    """
    # Fetch subcategories without items, including related category data
    subcategories = (Subcategory.objects
                    .select_related('category')
                    .filter(items__isnull=True)
                    .order_by('category__name', 'name'))

    context = {
        'subcategories': subcategories
    }
    
    template = loader.get_template("subcategories/delete.html")
    return HttpResponse(template.render(context, request))


@login_required
@permission_required('inventory.delete_subcategory', raise_exception=True)
def subcategory_delete_view(request, uuid):
    """
    Delete a specific subcategory by UUID.
    
    Performs a hard delete of the subcategory and logs the action in the audit trail.
    
    Args:
        request: HTTP request object
        uuid: UUID of the subcategory to delete
        
    Returns:
        HttpResponseRedirect: Redirect to dashboard after deletion
        
    Raises:
        Http404: If subcategory with given UUID doesn't exist
        PermissionDenied: If user doesn't have delete_subcategory permission
    """
    subcategory = get_object_or_404(Subcategory, pk=uuid)
    
    # Log the state before deletion for audit trail
    before_state = audit_log_state(subcategory)
    subcategory_name = subcategory.name
    
    # Perform the deletion
    subcategory.delete()
    
    # Log the deletion event
    after_state = audit_log_state(None)
    audit_log_event(
        request.user, 
        f"Deleted subcategory {subcategory_name}", 
        before_state, 
        after_state
    )
    
    messages.success(request, f'Subcategory "{subcategory_name}" was successfully deleted.')
    return redirect('dashboard')


class SubcategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Class-based view for creating new subcategories.
    
    Provides a form for creating new subcategories within existing categories
    and handles the creation process with proper audit logging.
    """
    model = models.Subcategory
    form_class = SubcategoryForm
    template_name = "subcategories/create.html"
    success_url = reverse_lazy('dashboard')
    permission_required = 'inventory.add_subcategory'

    def form_valid(self, form):
        """
        Process valid form submission and log the creation.
        
        Args:
            form: Valid SubcategoryForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to success URL
        """
        # Log the creation event
        before_state = audit_log_state(None)
        new_subcategory = form.save(commit=False)
        after_state = audit_log_state(new_subcategory)
        
        audit_log_event(
            self.request.user, 
            f"Created subcategory \"{new_subcategory.name}\"", 
            before_state, 
            after_state
        )
        
        response = super().form_valid(form)
        messages.success(self.request, f'Subcategory "{self.object.name}" was successfully created.')
        return response