"""
Category management views for the inventory application.

This module handles CRUD (Create, Read, Update, Delete) operations
for inventory categories, including category listing, creation, editing,
and deletion functionality.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import UpdateView, CreateView

from inventory import models
from inventory.forms import CategoryForm
from inventory.models import Category
from .utils import audit_log_state, audit_log_event


@login_required
@permission_required('inventory.delete_category', raise_exception=True)
def category_delete_list_view(request):
    """
    Display a list of categories that can be deleted.
    
    Only shows categories that have no subcategories, as categories
    with subcategories cannot be safely deleted.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with deletable categories
        
    Raises:
        PermissionDenied: If user doesn't have delete_category permission
    """
    # Only show categories without subcategories to prevent cascade issues
    categories = Category.objects.filter(subcategories__isnull=True).order_by('name')
    template = loader.get_template("categories/delete.html")
    return HttpResponse(template.render({'categories': categories}, request))


@login_required
@permission_required('inventory.delete_category', raise_exception=True)
def category_delete_view(request, uuid):
    """
    Delete a specific category by UUID.
    
    Performs a hard delete of the category and logs the action in the audit trail.
    
    Args:
        request: HTTP request object
        uuid: UUID of the category to delete
        
    Returns:
        HttpResponseRedirect: Redirect to dashboard after deletion
        
    Raises:
        Http404: If category with given UUID doesn't exist
        PermissionDenied: If user doesn't have delete_category permission
    """
    category = get_object_or_404(Category, pk=uuid)
    
    # Log the state before deletion for audit trail
    before_state = audit_log_state(category)
    category_name = category.name
    
    # Perform the deletion
    category.delete()
    
    # Log the deletion event
    after_state = audit_log_state(None)
    audit_log_event(request.user, f"Deleted category {category_name}", before_state, after_state)
    
    messages.success(request, f'Category "{category_name}" was successfully deleted.')
    return redirect('dashboard')


class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Class-based view for updating category information.
    
    Provides a form for editing category details and handles the update process
    with proper audit logging of changes.
    """
    model = Category
    form_class = CategoryForm
    template_name = "categories/edit.html"
    success_url = reverse_lazy('dashboard')
    permission_required = 'inventory.change_category'

    def form_valid(self, form):
        """
        Process valid form submission and log the changes.
        
        Args:
            form: Valid CategoryForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to success URL
        """
        # Get the current state before changes for audit logging
        before_model = Category.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(self.object)
        audit_log_event(
            self.request.user, 
            f"Updated category \"{before_model.name}\" to \"{self.object.name}\"", 
            before_state, 
            after_state
        )
        
        messages.success(self.request, f'Category "{self.object.name}" was successfully updated.')
        return response


class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Class-based view for creating new categories.
    
    Provides a form for creating new categories and handles the creation process
    with proper audit logging.
    """
    model = models.Category
    form_class = CategoryForm
    template_name = "categories/create.html"
    success_url = reverse_lazy('dashboard')
    permission_required = 'inventory.add_category'

    def form_valid(self, form):
        """
        Process valid form submission and log the creation.
        
        Args:
            form: Valid CategoryForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to success URL
        """
        # Log the creation event
        before_state = audit_log_state(None)
        new_category = form.save(commit=False)
        after_state = audit_log_state(new_category)
        
        audit_log_event(
            self.request.user, 
            f"Created category \"{new_category.name}\"", 
            before_state, 
            after_state
        )
        
        response = super().form_valid(form)
        messages.success(self.request, f'Category "{self.object.name}" was successfully created.')
        return response