"""
Item deletion and restoration views for soft deleting and restoring inventory items.
"""

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, Case, When, IntegerField

from inventory.models import Item, StockItem
from ..utils import audit_log_state, audit_log_event


@login_required
@permission_required('inventory.delete_item', raise_exception=True)
def item_soft_delete_view(request, uuid):
    """
    Soft delete an item by marking it as deleted.
    
    This preserves the item data while hiding it from normal views.
    The item can be restored later if needed.
    
    Args:
        request: HTTP request object
        uuid: UUID of the item to delete
        
    Returns:
        HttpResponseRedirect: Redirect to dashboard after deletion
        
    Raises:
        Http404: If item with given UUID doesn't exist
        PermissionDenied: If user doesn't have delete_item permission
    """
    item = get_object_or_404(Item, id=uuid)
    
    # Log the state before deletion
    before_state = audit_log_state(item)
    
    # Perform soft delete
    item.is_deleted = True
    item.save()
    
    # Log the deletion event
    after_state = audit_log_state(item)
    audit_log_event(
        request.user, 
        f"Deleted item \"{item.name}\"", 
        before_state, 
        after_state
    )
    
    messages.success(request, f'Item "{item.name}" was successfully deleted.')
    return redirect('dashboard')


@login_required
@permission_required('inventory.restore_deleteditem', raise_exception=True)
def item_restore_view(request, uuid):
    """
    Restore a previously deleted item.
    
    Undoes the soft delete operation by marking the item as active again.
    Validates that the item's name and GTIN are still unique before restoration.
    
    Args:
        request: HTTP request object
        uuid: UUID of the item to restore
        
    Returns:
        HttpResponseRedirect: Redirect to item detail view after restoration
        
    Raises:
        Http404: If item with given UUID doesn't exist
        PermissionDenied: If user doesn't have restore_deleteditem permission
    """
    item = get_object_or_404(Item.objects, id=uuid)
    
    # Validate name uniqueness before restoration
    if Item.active_objects.filter(name__iexact=item.name).exists():
        messages.error(request, f'Cannot restore item "{item.name}" because an active item with this name already exists.')
        return redirect('view_deleted_items')
    
    # Validate GTIN uniqueness before restoration (if the item has a GTIN)
    if item.gtin:
        # Check if GTIN exists on any other active item
        if Item.active_objects.filter(gtin=item.gtin).exists():
            messages.error(request, f'Cannot restore item "{item.name}" because an active item with the same GTIN already exists.')
            return redirect('view_deleted_items')
        
        # Check if GTIN exists on stock items belonging to other active items
        if StockItem.objects.filter(gtin=item.gtin, item__is_deleted=False).exclude(item=item).exists():
            messages.error(request, f'Cannot restore item "{item.name}" because a stock item with the same GTIN already exists for another active item.')
            return redirect('view_deleted_items')
    
    # Check if any of the item's stock items have GTINs that conflict with active items
    stock_items_with_gtin = StockItem.objects.filter(item=item).exclude(gtin='').values_list('gtin', flat=True)
    for stock_gtin in stock_items_with_gtin:
        # Check if this stock GTIN exists on any active item
        if Item.active_objects.filter(gtin=stock_gtin).exists():
            messages.error(request, f'Cannot restore item "{item.name}" because one of its stock items has a GTIN that matches an active item.')
            return redirect('view_deleted_items')
        
        # Check if this stock GTIN exists on stock items belonging to other active items
        if StockItem.objects.filter(gtin=stock_gtin, item__is_deleted=False).exclude(item=item).exists():
            messages.error(request, f'Cannot restore item "{item.name}" because one of its stock items has a GTIN that conflicts with another active stock item.')
            return redirect('view_deleted_items')
    
    # Log the state before restoration
    before_state = audit_log_state(item)
    
    # Restore the item
    item.is_deleted = False
    item.save()
    
    # Log the restoration event
    after_state = audit_log_state(item)
    audit_log_event(
        request.user, 
        f"Restored item \"{item.name}\"", 
        before_state, 
        after_state
    )
    
    messages.success(request, f'Item "{item.name}" was successfully restored.')
    return redirect('view_item', uuid=uuid)


@login_required
@permission_required('inventory.view_deleteditem', raise_exception=True)
def view_deleted_items(request):
    """
    Display all items that have been soft deleted.
    
    Shows a list of all deleted items for administrative review.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with deleted items
        
    Raises:
        PermissionDenied: If user doesn't have view_deleteditem permission
    """
    # Use annotations to avoid N+1 queries for total_stock_quantity
    deleted_items = Item.objects.filter(is_deleted=True).annotate(
        stock_items_quantity_annotated=Sum(
            Case(
                When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                default=0,
                output_field=IntegerField()
            )
        )
    )
    
    context = {
        'page_title': "Deleted Items", 
        'items': deleted_items
    }
    
    return render(request, 'items/list.html', context)
