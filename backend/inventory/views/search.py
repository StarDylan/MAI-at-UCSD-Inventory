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

from inventory.forms import Search_QuantityAdd
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
        context['defaultQuantity'] = 1
        context["items"] = Item.active_objects.all().order_by('name')
        
        # Pre-select item if item_uuid is provided in URL
        item_uuid = self.kwargs.get('item_uuid')
        if item_uuid:
            try:
                selected_item = Item.active_objects.get(id=item_uuid)
                context['selected_item'] = selected_item
                context['item_has_gtin'] = selected_item.gtin.strip() != ""
                # Add details_gtins for JS template
                context['selected_item'].details_gtins = selected_item.get_details_gtins()
            except Item.DoesNotExist:
                pass
        
        if "item_has_gtin" not in context:
            context['item_has_gtin'] = False
                
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
        Also check for URL parameters to pre-populate other fields.
        
        Returns:
            dict: Initial form data
        """
        initial = super().get_initial()
        
        # Pre-populate item if item_uuid is provided in URL path
        item_uuid = self.kwargs.get('item_uuid')
        if item_uuid:
            try:
                selected_item = Item.active_objects.get(id=item_uuid)
                initial['item'] = selected_item
            except Item.DoesNotExist:
                pass
        
        # Check for URL query parameters to pre-populate fields
        # Expiration date
        if 'expiration_date' in self.request.GET:
            try:
                from datetime import datetime
                date_str = self.request.GET['expiration_date']
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                initial['expiration_date'] = parsed_date
            except (ValueError, TypeError):
                # If date parsing fails, ignore this parameter
                pass
        
        # Lot number
        if 'lot_number' in self.request.GET:
            initial['lot_number'] = self.request.GET['lot_number']
        
        # Detail
        if 'detail' in self.request.GET:
            initial['detail'] = self.request.GET['detail']
                
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
        location_new = form.cleaned_data['location_new']
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
            location=location_new.name if location_new else '',
            location_new=location_new,
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