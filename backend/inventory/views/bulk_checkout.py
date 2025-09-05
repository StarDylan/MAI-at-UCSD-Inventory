"""
Bulk checkout views for managing multi-item checkouts with organization tracking.
"""

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import json

from inventory.forms import CheckOutForm, CheckOutItemForm, CheckOutCompleteForm, AddToCheckOutForm
from inventory.models import CheckOut, CheckOutItem, Item, StockItem, Organization
from .utils import audit_log_state, audit_log_event


class BulkCheckoutListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Main bulk checkout page with Active and Completed tabs.
    """
    model = CheckOut
    template_name = 'checkout/bulk_checkout_list.html'
    context_object_name = 'checkouts'
    permission_required = 'inventory.change_item'
    paginate_by = 20
    
    def get_queryset(self):
        tab = self.request.GET.get('tab', 'active')
        if tab == 'completed':
            return CheckOut.objects.filter(is_completed=True).order_by('-completed_at')
        else:
            return CheckOut.objects.filter(is_completed=False).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = self.request.GET.get('tab', 'active')
        context['active_count'] = CheckOut.objects.filter(is_completed=False).count()
        context['completed_count'] = CheckOut.objects.filter(is_completed=True).count()
        return context


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_create_view(request):
    """
    Create a new active checkout.
    """
    if request.method == 'POST':
        form = CheckOutForm(request.POST)
        if form.is_valid():
            checkout = form.save(commit=False)
            checkout.created_by = request.user
            checkout.save()
            
            # Log the creation
            audit_log_event(
                request.user,
                f"Created new checkout for {checkout.organization.name}",
                audit_log_state(None),
                audit_log_state(checkout)
            )
            
            messages.success(request, f'New checkout created for {checkout.organization.name}')
            return redirect('checkout_detail', checkout_id=checkout.id)
    else:
        form = CheckOutForm()
    
    return render(request, 'checkout/checkout_create.html', {
        'form': form
    })


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_detail_view(request, checkout_id):
    """
    View and edit individual checkout details.
    """
    checkout = get_object_or_404(CheckOut, id=checkout_id)
    checkout_items = checkout.checkout_items.all().select_related(
        'stock_item__item', 'stock_item__organization'
    )
    
    context = {
        'checkout': checkout,
        'checkout_items': checkout_items,
        'can_edit': not checkout.is_completed,
    }
    
    return render(request, 'checkout/checkout_detail.html', context)


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_add_item_view(request, checkout_id):
    """
    Add an item to an existing checkout.
    """
    checkout = get_object_or_404(CheckOut, id=checkout_id)
    
    if checkout.is_completed:
        messages.error(request, 'Cannot add items to completed checkout')
        return redirect('checkout_detail', checkout_id=checkout.id)
    
    if request.method == 'POST':
        # Handle AJAX request for adding item
        stock_item_id = request.POST.get('stock_item_id')
        quantity = int(request.POST.get('quantity', 1))
        cost_per_item = request.POST.get('cost_per_item')
        notes = request.POST.get('notes', '')
        
        try:
            stock_item = StockItem.objects.get(id=stock_item_id)
            
            # Check if already exists
            existing_item = CheckOutItem.objects.filter(
                checkout=checkout, 
                stock_item=stock_item
            ).first()
            
            if existing_item:
                return JsonResponse({
                    'success': False, 
                    'error': 'This stock item is already in the checkout'
                })
            
            # Check quantity availability
            if quantity > stock_item.quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {stock_item.quantity} units available'
                })
            
            # Create the checkout item
            checkout_item = CheckOutItem.objects.create(
                checkout=checkout,
                stock_item=stock_item,
                quantity=quantity,
                cost_per_item=float(cost_per_item) if cost_per_item else None,
                notes=notes
            )
            
            # Log the addition
            audit_log_event(
                request.user,
                f"Added {quantity}x {stock_item.item.name} to checkout for {checkout.organization.name}",
                audit_log_state(None),
                audit_log_state(checkout_item)
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Added {quantity}x {stock_item.item.name} to checkout'
            })
            
        except StockItem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Stock item not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    # GET request - show form to add items
    items = Item.active_objects.all().order_by('name')
    return render(request, 'checkout/checkout_add_item.html', {
        'checkout': checkout,
        'items': items,
    })


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_remove_item_view(request, checkout_id, item_id):
    """
    Remove an item from a checkout.
    """
    checkout = get_object_or_404(CheckOut, id=checkout_id)
    checkout_item = get_object_or_404(CheckOutItem, id=item_id, checkout=checkout)
    
    if checkout.is_completed:
        messages.error(request, 'Cannot remove items from completed checkout')
        return redirect('checkout_detail', checkout_id=checkout.id)
    
    if request.method == 'POST':
        item_description = str(checkout_item)
        
        # Log the removal
        audit_log_event(
            request.user,
            f"Removed {item_description} from checkout for {checkout.organization.name}",
            audit_log_state(checkout_item),
            audit_log_state(None)
        )
        
        checkout_item.delete()
        messages.success(request, f'Removed {item_description} from checkout')
    
    return redirect('checkout_detail', checkout_id=checkout.id)


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_complete_view(request, checkout_id):
    """
    Complete a checkout - subtract stock quantities and mark as completed.
    """
    checkout = get_object_or_404(CheckOut, id=checkout_id)
    
    if checkout.is_completed:
        messages.error(request, 'Checkout is already completed')
        return redirect('checkout_detail', checkout_id=checkout.id)
    
    if not checkout.checkout_items.exists():
        messages.error(request, 'Cannot complete checkout with no items')
        return redirect('checkout_detail', checkout_id=checkout.id)
    
    if request.method == 'POST':
        form = CheckOutCompleteForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Process each checkout item
                for checkout_item in checkout.checkout_items.all():
                    stock_item = checkout_item.stock_item
                    
                    # Check if still enough quantity available
                    if stock_item.quantity < checkout_item.quantity:
                        messages.error(
                            request, 
                            f'Insufficient stock for {stock_item.item.name} from {stock_item.location}. '
                            f'Available: {stock_item.quantity}, Required: {checkout_item.quantity}'
                        )
                        return redirect('checkout_detail', checkout_id=checkout.id)
                    
                    # Log state before changes
                    before_state = audit_log_state(stock_item)
                    
                    # Subtract quantity
                    stock_item.quantity -= checkout_item.quantity
                    stock_item.save()
                    
                    # Log the stock change
                    audit_log_event(
                        request.user,
                        f"Bulk checkout: {checkout_item.quantity} of {stock_item.item.name} "
                        f"checked out to {checkout.organization.name} from {stock_item.location}",
                        before_state,
                        audit_log_state(stock_item)
                    )
                
                # Mark checkout as completed
                checkout.is_completed = True
                checkout.completed_by = request.user
                checkout.completed_at = timezone.now()
                checkout.total_weight = form.cleaned_data.get('total_weight')
                
                completion_notes = form.cleaned_data.get('notes')
                if completion_notes:
                    checkout.notes = f"{checkout.notes}\n\nCompletion notes: {completion_notes}".strip()
                
                checkout.save()
                
                # Log checkout completion
                audit_log_event(
                    request.user,
                    f"Completed bulk checkout for {checkout.organization.name} "
                    f"with {checkout.total_items_count} total items",
                    audit_log_state(None),
                    audit_log_state(checkout)
                )
                
                messages.success(
                    request, 
                    f'Checkout completed successfully! {checkout.total_items_count} items '
                    f'checked out to {checkout.organization.name}'
                )
                
                return redirect('bulk_checkout_list')
    else:
        form = CheckOutCompleteForm()
    
    return render(request, 'checkout/checkout_complete.html', {
        'checkout': checkout,
        'form': form,
    })


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def checkout_undo_view(request, checkout_id):
    """
    Undo a completed checkout - restore stock quantities.
    """
    checkout = get_object_or_404(CheckOut, id=checkout_id)
    
    if not checkout.is_completed:
        messages.error(request, 'Cannot undo checkout that is not completed')
        return redirect('checkout_detail', checkout_id=checkout.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Restore stock quantities
            for checkout_item in checkout.checkout_items.all():
                stock_item = checkout_item.stock_item
                
                # Log state before changes
                before_state = audit_log_state(stock_item)
                
                # Restore quantity
                stock_item.quantity += checkout_item.quantity
                stock_item.save()
                
                # Log the restoration
                audit_log_event(
                    request.user,
                    f"Undo bulk checkout: {checkout_item.quantity} of {stock_item.item.name} "
                    f"restored to {stock_item.location} (was checked out to {checkout.organization.name})",
                    before_state,
                    audit_log_state(stock_item)
                )
            
            # Mark checkout as not completed (revert to active)
            checkout.is_completed = False
            checkout.completed_by = None
            checkout.completed_at = None
            checkout.save()
            
            # Log the undo
            audit_log_event(
                request.user,
                f"Undid completed checkout for {checkout.organization.name}",
                audit_log_state(checkout),
                audit_log_state(None)
            )
            
            messages.success(
                request, 
                f'Checkout undone successfully! Stock quantities restored for '
                f'{checkout.total_items_count} items'
            )
    
    return redirect('checkout_detail', checkout_id=checkout.id)


@login_required
@permission_required('inventory.change_item', raise_exception=True)
def add_to_checkout_from_item_view(request, item_uuid):
    """
    Add stock items to an existing checkout from the item detail page.
    """
    item = get_object_or_404(Item, id=item_uuid)
    
    if request.method == 'POST':
        form = AddToCheckOutForm(request.POST, item=item, user=request.user)
        if form.is_valid():
            checkout = form.cleaned_data['checkout']
            stock_item = form.cleaned_data['stock_item']
            quantity = form.cleaned_data['quantity']
            cost_per_item = form.cleaned_data.get('cost_per_item')
            
            # Create the checkout item
            checkout_item = CheckOutItem.objects.create(
                checkout=checkout,
                stock_item=stock_item,
                quantity=quantity,
                cost_per_item=cost_per_item
            )
            
            # Log the addition
            audit_log_event(
                request.user,
                f"Added {quantity}x {item.name} to checkout for {checkout.organization.name} from item detail page",
                audit_log_state(None),
                audit_log_state(checkout_item)
            )
            
            messages.success(
                request, 
                f'Added {quantity}x {item.name} to checkout for {checkout.organization.name}'
            )
            
            return redirect('view_item', uuid=item.id)
    else:
        form = AddToCheckOutForm(item=item, user=request.user)
    
    return render(request, 'checkout/add_to_checkout_from_item.html', {
        'form': form,
        'item': item,
    })


def get_stock_items_api(request, item_uuid):
    """
    API endpoint to get stock items for a specific item (for AJAX).
    """
    item = get_object_or_404(Item, id=item_uuid)
    stock_items = item.stock_items.filter(quantity__gt=0).order_by(
        'detail', 'expiration_date', 'date_received'
    )
    
    data = []
    for stock_item in stock_items:
        data.append({
            'id': str(stock_item.id),
            'detail': stock_item.detail,
            'location': stock_item.location,
            'quantity': stock_item.quantity,
            'organization': stock_item.organization.name,
            'expiration_date': stock_item.expiration_date.strftime('%Y-%m-%d') if stock_item.expiration_date else None,
            'display_name': f"{stock_item.detail} - {stock_item.location} ({stock_item.quantity} available)"
        })
    
    return JsonResponse({'stock_items': data})