"""
Search and quantity management views for the inventory application.

This module handles search functionality and quantity management operations
such as checking items in and out of inventory, with proper validation
and audit logging.
"""

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import FormView

from inventory.forms import Search_QuantityAdd, Search_QuantityRemove
from inventory.models import Item, StockItem
from .utils import audit_log_state, audit_log_event


class SearchCheckInView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View for checking items into inventory (increasing quantity).
    
    Provides a form-based interface for adding quantity to existing items
    with validation and audit logging.
    """
    template_name = 'search/update_quantity.html'
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
        context["items"] = Item.active_objects.all().order_by('name')
        return context

    def form_valid(self, form):
        """
        Process valid form submission for checking in items.
        
        Creates a new StockItem record for the incoming stock and logs
        the transaction in the audit trail.
        
        Args:
            form: Valid Search_QuantityAdd form instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
        """
        item = form.cleaned_data['item']
        quantity = form.cleaned_data['quantity']
        organization = form.cleaned_data['organization']
        date_received = form.cleaned_data['date_received']
        expiration_date = form.cleaned_data['expiration_date']
        lot_number = form.cleaned_data['lot_number']
        notes = form.cleaned_data['notes']

        # Get the item and log current state
        item = get_object_or_404(Item, id=item.id)
        before_state = audit_log_state(item)
        
        # Create new StockItem
        stock_item = StockItem.objects.create(
            item=item,
            organization=organization,
            quantity=quantity,
            date_received=date_received,
            expiration_date=expiration_date,
            lot_number=lot_number,
            notes=notes
        )
        
        # Log the check-in event
        after_state = audit_log_state(item)
        audit_log_event(
            self.request.user, 
            f"Checked in {quantity} of item \"{item.name}\" from {organization.name}", 
            before_state, 
            after_state
        )

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))


class SearchCheckOutView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View for checking items out of inventory (decreasing quantity).
    
    Provides a form-based interface for removing quantity from existing items
    with validation to prevent negative quantities and audit logging.
    """
    template_name = 'search/update_quantity.html'
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
        context["items"] = Item.active_objects.all().order_by('name')
        return context

    def form_valid(self, form: Search_QuantityRemove):
        """
        Process valid form submission for checking out items.
        
        Reduces quantities from existing StockItem records by marking them as 
        inactive or reducing their quantities (FIFO - First expiring first).
        
        Args:
            form: Valid Search_QuantityRemove form instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
            HttpResponse: Form with errors if insufficient quantity
        """
        item = form.cleaned_data['item']
        quantity_to_remove = form.cleaned_data['quantity']
        notes = form.cleaned_data['notes']

        # Get the item and validate availability
        item = get_object_or_404(Item, id=item.id)
        
        # Check if sufficient quantity is available
        total_available = item.total_stock_quantity
        if total_available < quantity_to_remove:
            form.add_error(
                'quantity', 
                f"Cannot check out {quantity_to_remove} items. Only {total_available} available."
            )
            return self.form_invalid(form)

        # Log current state before update
        before_state = audit_log_state(item)
        
        # Get active stock items ordered by expiration date (FIFO)
        stock_items = item.stock_items.filter(is_active=True).order_by('expiration_date', 'date_received')
        
        remaining_to_remove = quantity_to_remove
        removed_items = []
        
        for stock_item in stock_items:
            if remaining_to_remove <= 0:
                break
                
            if stock_item.quantity <= remaining_to_remove:
                # Mark entire stock item as inactive
                remaining_to_remove -= stock_item.quantity
                stock_item.is_active = False
                stock_item.notes += f"\n[Checkout] {notes}" if notes else ""
                stock_item.save()
                removed_items.append(f"{stock_item.quantity} from {stock_item.organization.name}")
            else:
                # Reduce quantity of this stock item
                quantity_taken = remaining_to_remove
                stock_item.quantity -= quantity_taken
                stock_item.notes += f"\n[Checkout] Removed {quantity_taken}: {notes}" if notes else f"\n[Checkout] Removed {quantity_taken}"
                stock_item.save()
                remaining_to_remove = 0
                removed_items.append(f"{quantity_taken} from {stock_item.organization.name}")
        
        # Log the check-out event
        after_state = audit_log_state(item)
        removed_details = ", ".join(removed_items)
        audit_log_event(
            self.request.user, 
            f"Checked out {quantity_to_remove} of item \"{item.name}\" ({removed_details})", 
            before_state, 
            after_state
        )

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))