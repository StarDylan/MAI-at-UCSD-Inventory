"""
Search and quantity management views for the inventory application.

This module handles search functionality and quantity management operations
such as checking items in and out of inventory, with proper validation
and audit logging.
"""

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import FormView

from inventory.forms import Search_QuantityAdd, Search_QuantityRemove
from inventory.models import Item
from .utils import audit_log_state, audit_log_event


class SearchCheckInView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View for checking items into inventory (increasing quantity).
    
    Provides a form-based interface for adding quantity to existing items
    with validation and audit logging.
    """
    template_name = 'search/updateqty.html'
    form_class = Search_QuantityAdd
    permission_required = 'inventory.change_item'

    def get_context_data(self, **kwargs):
        """
        Add extra context data to the template.
        
        Provides the action type, default quantity, and list of available items
        for the check-in form.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            dict: Template context with form-specific data
        """
        context = super().get_context_data(**kwargs)
        context['action'] = 'Check in'
        context['defaultQuantity'] = 1
        context["items"] = Item.objects.all().order_by('name')
        return context

    def form_valid(self, form):
        """
        Process valid form submission for checking in items.
        
        Increases the item's active quantity by the specified amount
        and logs the transaction in the audit trail.
        
        Args:
            form: Valid Search_QuantityAdd form instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
        """
        item = form.cleaned_data['item']
        quantity = form.cleaned_data['quantity']

        # Get the item and log current state
        item = get_object_or_404(Item, id=item.id)
        before_state = audit_log_state(item)
        
        # Update quantity
        item.quantity_active += quantity
        item.save()
        
        # Log the check-in event
        after_state = audit_log_state(item)
        audit_log_event(
            self.request.user, 
            f"Checked in {quantity} of item \"{item.name}\"", 
            before_state, 
            after_state
        )

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))

    def form_invalid(self, form):
        """
        Handle invalid form submission.
        
        Displays error messages to the user when form validation fails.
        
        Args:
            form: Invalid form instance with errors
            
        Returns:
            HttpResponse: Rendered form with error messages
        """
        messages.error(
            self.request, 
            "Form submission failed. Please check the fields below."
        )
        return super().form_invalid(form)


class SearchCheckOutView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View for checking items out of inventory (decreasing quantity).
    
    Provides a form-based interface for removing quantity from existing items
    with validation to prevent negative quantities and audit logging.
    """
    template_name = 'search/updateqty.html'
    form_class = Search_QuantityRemove
    permission_required = 'inventory.change_item'

    def get_context_data(self, **kwargs):
        """
        Add extra context data to the template.
        
        Provides the action type and list of available items for the check-out form.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            dict: Template context with form-specific data
        """
        context = super().get_context_data(**kwargs)
        context['action'] = 'Check out'
        context["items"] = Item.objects.all().order_by('name')
        return context

    def form_valid(self, form: Search_QuantityRemove):
        """
        Process valid form submission for checking out items.
        
        Decreases the item's active quantity by the specified amount after
        validating that sufficient quantity is available.
        
        Args:
            form: Valid Search_QuantityRemove form instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
            HttpResponse: Form with errors if insufficient quantity
        """
        item = form.cleaned_data['item']
        quantity = form.cleaned_data['quantity']

        # Get the item and validate availability
        item = get_object_or_404(Item, id=item.id)
        
        # Check if sufficient quantity is available
        if item.quantity_active < quantity:
            form.add_error(
                'quantity', 
                f"Cannot check out {quantity} items. Only {item.quantity_active} available."
            )
            return self.form_invalid(form)

        # Log current state before update
        before_state = audit_log_state(item)
        
        # Update quantity
        item.quantity_active -= quantity
        item.save()
        
        # Log the check-out event
        after_state = audit_log_state(item)
        audit_log_event(
            self.request.user, 
            f"Checked out {quantity} of item \"{item.name}\"", 
            before_state, 
            after_state
        )

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))