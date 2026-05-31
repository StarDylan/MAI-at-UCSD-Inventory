"""
Stock item management views for updating and deleting individual stock items.
"""

from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import UpdateView
from django.db import transaction

from inventory.models import Item, StockItem, CheckOutItem
from inventory.forms import StockItemEditForm, StockTransferForm
from ..utils import audit_log_state, audit_log_event


class StockItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Class-based view for updating individual stock item information.
    
    Provides a form for editing stock item details and handles the update process
    with proper audit logging of changes.
    """
    model = StockItem
    form_class = StockItemEditForm
    template_name = "items/edit_stock.html"
    permission_required = 'inventory.change_stockitem'

    def form_valid(self, form):
        """
        Process valid form submission and log the changes.
        
        Args:
            form: Valid StockItemEditForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
        """
        # Get the current state before changes for audit logging
        before_model = StockItem.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(self.object)
        location_display = self.object.location_new.name
        audit_log_event(
            self.request.user, 
            f"Updated \"{self.object.item.name}\" stock in location \"{location_display}\"", 
            before_state, 
            after_state
        )
        
        messages.success(self.request, f'Stock for "{self.object.item.name}" in location "{location_display}" was successfully updated.')
        return response

    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the item's detail view
        """
        return reverse_lazy('view_item', kwargs={'uuid': self.object.item.pk})


@login_required
@permission_required('inventory.delete_stockitem', raise_exception=True)
def stock_item_delete_view(request, uuid):
    """
    Delete a stock item.
    
    Completely removes the stock item from the database.
    
    Args:
        request: HTTP request object
        uuid: UUID of the stock item to delete
        
    Returns:
        HttpResponseRedirect: Redirect to item detail view after deletion
        
    Raises:
        Http404: If stock item with given UUID doesn't exist
        PermissionDenied: If user doesn't have delete_stockitem permission
    """
    stock_item = get_object_or_404(StockItem, id=uuid)
    item_uuid = stock_item.item.pk

    # Check if this stock item is referenced by any checkout
    if CheckOutItem.objects.filter(stock_item=stock_item).exists():
        # Use extra_tags to set Bootstrap alert-danger for red error
        messages.error(request, "This stock entry is referenced by a checkout and cannot be deleted. Set its quantity to 0 instead.")
        return redirect('view_item', uuid=item_uuid)

    # Store info for success message before deletion
    quantity = stock_item.quantity
    item_name = stock_item.item.name
    location = stock_item.location_new.name

    # Log the state before deletion
    before_state = audit_log_state(stock_item)

    # Log the deletion event
    audit_log_event(
        request.user,
        f"Deleted {stock_item.quantity} of \"{stock_item.item.name}\" from location \"{stock_item.location_new.name}\"",
        before_state,
        audit_log_state(None),
        entity_id=str(stock_item.item.id)
    )

    # Perform deletion
    stock_item.delete()

    messages.success(request, f'Removed {quantity} of "{item_name}" from location "{location}".')
    return redirect('view_item', uuid=item_uuid)


@login_required
@permission_required('inventory.change_stockitem', raise_exception=True)
def transfer_stock_from_item_view(request, item_uuid):
    """
    Transfer stock items from one location to another from the item detail page.
    
    Allows users to select multiple stock items with individual quantities and transfer them to a destination location.
    If the full quantity is transferred, the original stock item location is changed. If only part of the quantity
    is transferred, a new stock item is created at the destination location with the transferred quantity,
    and the original stock item's quantity is reduced accordingly.
    
    Args:
        request: HTTP request object
        item_uuid: UUID of the item to transfer stock for
        
    Returns:
        HttpResponse: Rendered template with transfer form or redirect on success
    """
    item = get_object_or_404(Item, id=item_uuid)
    form = StockTransferForm()  # Initialize form for all code paths
    
    if request.method == 'POST':
        destination_location_id = request.POST.get('destination_location')
        stock_item_ids = request.POST.getlist('stock_item_ids')
        transfer_reason = request.POST.get('transfer_reason', '')
        
        if not destination_location_id:
            messages.error(request, 'Please select a destination location.')
        elif not stock_item_ids:
            messages.error(request, 'Please select at least one stock item to transfer.')
        else:
            try:
                from inventory.models import Location
                destination_location = Location.objects.get(id=destination_location_id)
            except Location.DoesNotExist:
                messages.error(request, 'Invalid destination location.')
                stock_items = item.stock_items.filter(quantity__gt=0).order_by('detail', 'expiration_date', 'date_received')
                locations = Location.objects.filter(is_active=True).order_by('name')
                return render(request, 'items/transfer_stock_from_item.html', {
                    'item': item,
                    'stock_items': stock_items,
                    'form': StockTransferForm(),
                    'locations': locations,
                })
            
            stock_items_to_transfer = StockItem.objects.filter(
                id__in=stock_item_ids,
                item=item,
                quantity__gt=0
            ).select_related('location_new')
            
            if stock_items_to_transfer.count() != len(stock_item_ids):
                messages.error(request, 'One or more selected stock items are invalid or unavailable.')
            else:
                transferred_count = 0
                split_count = 0
                
                with transaction.atomic():
                    for stock_item in stock_items_to_transfer:
                        quantity_raw = request.POST.get(f'quantity_{stock_item.id}')
                        try:
                            quantity = int(quantity_raw)
                        except (TypeError, ValueError):
                            quantity = 0
                        
                        if quantity <= 0 or quantity > stock_item.quantity:
                            continue
                        
                        old_location = stock_item.location_new
                        
                        if quantity == stock_item.quantity:
                            # Transfer entire stock item - just update location
                            stock_item.location_new = destination_location
                            stock_item.location = destination_location.name
                            stock_item.save()
                            transferred_count += 1
                            
                            audit_log_event(
                                request.user,
                                f"Transferred {quantity} units of \"{item.name}\" from {old_location.name} to {destination_location.name}" + 
                                (f" ({transfer_reason})" if transfer_reason else ""),
                                audit_log_state(stock_item),
                                audit_log_state(stock_item),
                                item.id
                            )
                        else:
                            # Split the stock item - create new one at destination
                            new_stock_item = StockItem.objects.create(
                                item=item,
                                organization=stock_item.organization,
                                quantity=quantity,
                                location=destination_location.name,
                                location_new=destination_location,
                                gtin=stock_item.gtin,
                                detail=stock_item.detail,
                                date_received=stock_item.date_received,
                                expiration_date=stock_item.expiration_date,
                                lot_number=stock_item.lot_number,
                                notes=f"Transferred from {old_location.name}" + 
                                      (f" ({transfer_reason})" if transfer_reason else ""),
                                surplus_status=stock_item.surplus_status
                            )
                            
                            stock_item.quantity -= quantity
                            stock_item.save()
                            split_count += 1
                            
                            audit_log_event(
                                request.user,
                                f"Transferred {quantity} units of \"{item.name}\" from {old_location.name} to {destination_location.name}" + 
                                (f" ({transfer_reason})" if transfer_reason else ""),
                                audit_log_state(stock_item),
                                audit_log_state(new_stock_item),
                                item.id
                            )
                
                if transferred_count > 0 or split_count > 0:
                    msg_parts = []
                    if transferred_count > 0:
                        msg_parts.append(f'{transferred_count} item(s) moved')
                    if split_count > 0:
                        msg_parts.append(f'{split_count} item(s) split')
                    
                    messages.success(
                        request,
                        f'Successfully transferred stock to {destination_location.name}. {" and ".join(msg_parts)}.'
                    )
                    return redirect('view_item', uuid=item.id)
                else:
                    messages.error(request, 'Please enter a valid quantity greater than 0 for at least one stock item.')
    
    # Get stock items for the template
    stock_items = item.stock_items.filter(quantity__gt=0).order_by(
        'detail', 'expiration_date', 'date_received'
    )
    
    # Get all active locations for the form
    from inventory.models import Location
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'items/transfer_stock_from_item.html', {
        'item': item,
        'stock_items': stock_items,
        'form': form,
        'locations': locations,
    })
