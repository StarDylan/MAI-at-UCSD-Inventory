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
        for the check-in form. If an item_uuid is provided in the URL, pre-select that item.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            dict: Template context with form-specific data
        """
        context = super().get_context_data(**kwargs)
        context['action'] = 'Check in'
        context['defaultQuantity'] = 1
        context["items"] = Item.active_objects.all().order_by('name')
        
        # Pre-select item if item_uuid is provided in URL
        item_uuid = self.kwargs.get('item_uuid')
        if item_uuid:
            try:
                selected_item = Item.active_objects.get(id=item_uuid)
                context['selected_item'] = selected_item
            except Item.DoesNotExist:
                pass
                
        return context

    def get_form_kwargs(self):
        """
        Add the initial_item to form kwargs if item_uuid is provided.
        """
        kwargs = super().get_form_kwargs()
        
        item_uuid = self.kwargs.get('item_uuid')
        if item_uuid:
            try:
                selected_item = Item.active_objects.get(id=item_uuid)
                kwargs['initial_item'] = selected_item
            except Item.DoesNotExist:
                pass
                
        return kwargs

    def get_initial(self):
        """
        Get initial form data.
        
        If an item_uuid is provided in the URL, pre-populate the item field.
        
        Returns:
            dict: Initial form data
        """
        initial = super().get_initial()
        
        item_uuid = self.kwargs.get('item_uuid')
        if item_uuid:
            try:
                selected_item = Item.active_objects.get(id=item_uuid)
                initial['item'] = selected_item
            except Item.DoesNotExist:
                pass
                
        return initial

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
        location = form.cleaned_data['location']
        gtin = form.cleaned_data['gtin']
        detail = form.cleaned_data['detail']
        date_received = form.cleaned_data['date_received']
        expiration_date = form.cleaned_data['expiration_date']
        lot_number = form.cleaned_data['lot_number']
        notes = form.cleaned_data['notes']

        # Get the item and log current state
        item = get_object_or_404(Item, id=item.id)
        before_state = audit_log_state(None)
        
        # Create new StockItem
        stock_item = StockItem.objects.create(
            item=item,
            organization=organization,
            quantity=quantity,
            location=location,
            gtin=gtin,
            detail=detail,
            date_received=date_received,
            expiration_date=expiration_date,
            lot_number=lot_number,
            notes=notes
        )
        
        # Log the check-in event
        after_state = audit_log_state(stock_item)
        audit_log_event(
            self.request.user, 
            f"Checked-in {quantity} of \"{item.name}\" into location \"{location}\"", 
            before_state,
            after_state
        )

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))