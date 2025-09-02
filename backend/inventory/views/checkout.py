"""
Advanced checkout views for selecting specific stock items.
"""

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import FormView
from django.http import JsonResponse
import json

from inventory.forms import StockItemCheckoutForm
from inventory.models import Item, StockItem
from .utils import audit_log_state, audit_log_event


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_item_select(request, item_uuid):
    """
    View for selecting which stock items to check out from a specific item.
    """
    item = get_object_or_404(Item, id=item_uuid)
    stock_items = item.stock_items.filter(quantity__gt=0).order_by('expiration_date', 'date_received')
    
    context = {
        'item': item,
        'stock_items': stock_items,
    }
    
    return render(request, 'search/checkout_select.html', context)


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_item_process(request, item_uuid):
    """
    Process the checkout request for selected stock items.
    """
    if request.method != 'POST':
        return redirect('checkout_item_select', item_uuid=item_uuid)
    
    item = get_object_or_404(Item, id=item_uuid)
    
    # Get selected stock items and quantities from form data
    selected_stock_ids = request.POST.getlist('stock_items')
    quantities = {}
    for stock_id in selected_stock_ids:
        qty_key = f'quantity_{stock_id}'
        if qty_key in request.POST:
            quantities[stock_id] = int(request.POST[qty_key])
    
    notes = request.POST.get('notes', '')
    
    # Validate that all selected stock items exist and have sufficient quantity
    stock_items = StockItem.objects.filter(id__in=selected_stock_ids, quantity__gt=0)
    total_to_remove = sum(quantities.values())
    
    before_states = []
    after_states = []
    items_removed = []
    locations = []

    # Log current state before update
    
    
    for stock_item in stock_items:
        stock_id = str(stock_item.id)
        quantity_to_remove = quantities.get(stock_id, 0)
        
        if quantity_to_remove <= 0:
            continue
            

        if stock_item.quantity < quantity_to_remove:
            # Handle error - not enough quantity
            return render(request, 'search/checkout_select.html', {
                'item': item,
                'stock_items': item.stock_items.filter(quantity__gt=0).order_by('expiration_date', 'date_received'),
                'error': f'Stock item from {stock_item.organization.name} only has {stock_item.quantity} units, but {quantity_to_remove} was requested.'
            })
        
        
        before_states.append(audit_log_state(stock_item))
        if stock_item.quantity == quantity_to_remove:
            # Set quantity to 0 to mark as inactive
            stock_item.quantity = 0
            stock_item.save()
            items_removed.append(stock_item.quantity)
            locations.append(stock_item.location)
        else:
            # Reduce quantity of this stock item
            stock_item.quantity -= quantity_to_remove
            stock_item.save()
            items_removed.append(quantity_to_remove)
            locations.append(stock_item.location)

        after_states.append(audit_log_state(stock_item))
    
    # Log the check-out event
    if notes:
        notes_end_tag = f" - User Notes: {notes}"
    else:
        notes_end_tag = ""

    for before_state, after_state, quantity, location in zip(before_states, after_states, items_removed, locations):
        audit_log_event(
            request.user, 
            f"Checked out {quantity} of item \"{item.name}\"{notes_end_tag} from {location}", 
            before_state, 
            after_state
        )

    return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))