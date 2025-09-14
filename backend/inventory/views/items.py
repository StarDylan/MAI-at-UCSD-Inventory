"""
Item management views for the inventory application.

This module handles CRUD operations for inventory items, including
item creation, viewing, editing, deletion (soft delete), and restoration.
Items are the core entities in the inventory system.
"""

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import UpdateView, CreateView

from inventory import models
from inventory.forms import StockItemEditForm
from inventory.forms_tags import TaggedItemForm, TaggedItemWithStockForm
from inventory.models import Item, AuditEvent, StockItem, CheckOutItem, Tag, TagGroup
from .utils import audit_log_state, audit_log_event

def view_item_detail(request, uuid):
    """
    Display detailed information for a specific item.
    
    Shows item details, stock items with expiration dates, associated images, and audit history.
    Handles permissions for viewing deleted items. For non-authenticated users, only shows
    surplus-approved stock items.
    
    Args:
        request: HTTP request object
        uuid: UUID of the item to view
        
    Returns:
        HttpResponse: Rendered template with item details
        HttpResponseForbidden: If user doesn't have permission to view deleted item
        
    Raises:
        Http404: If item with given UUID doesn't exist
    """
    # Use all_objects manager to include deleted items
    item = get_object_or_404(
        Item.objects.select_related('category', 'subcategory'),
        id=uuid
    )

    # Check permissions for viewing deleted items
    if (item.is_deleted and 
        (not request.user.is_authenticated or 
         not request.user.has_perm('inventory.view_deleteditem'))):
        return HttpResponseForbidden()

    # Fetch related images, stock items, and audit events
    images = item.images.all().order_by('id')
    
    # Filter stock items based on authentication status and surplus approval
    stock_items_query = item.stock_items.select_related('organization')
    if not request.user.is_authenticated:
        # Non-authenticated users only see surplus-approved stock items
        stock_items_query = stock_items_query.filter(surplus_status__in=['not_wanted'])
    
    stock_items = stock_items_query.order_by('detail', 'expiration_date', 'date_received')
    
    # Get audit events for the item and its stock items in a single query
    entity_ids = [str(uuid)] + list(stock_items.values_list('id', flat=True))
    all_events = AuditEvent.objects.filter(entity_id__in=entity_ids).select_related("user").order_by('-created_at')

    # Prepare audit events for template display
    for event in all_events:
        event.json_data = {
            'before': event.before,
            'after': event.after,
        }

    context = {
        'item': item,
        'images': images,
        'stock_items': stock_items,
        'audit': all_events,
        'total_items': sum(si.quantity for si in stock_items),
    }
    
    template = loader.get_template("items/detail.html")
    return HttpResponse(template.render(context, request))


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
    from django.db.models import Sum, Case, When, IntegerField
    
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
        'category': {"name": "Deleted Items"}, 
        'items': deleted_items
    }
    
    return render(request, 'items/list.html', context)


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Class-based view for updating item information.
    
    Provides a form for editing item details and handles the update process
    with proper audit logging of changes.
    """
    model = models.Item
    form_class = TaggedItemForm
    template_name = "items/edit.html"
    permission_required = 'inventory.change_item'

    def form_valid(self, form):
        """
        Process valid form submission and log the changes.
        
        Args:
            form: Valid ItemForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
        """
        # Get the current state before changes for audit logging
        before_model = models.Item.active_objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(self.object)
        audit_log_event(
            self.request.user, 
            f"Updated item \"{before_model.name}\"", 
            before_state, 
            after_state
        )
        
        messages.success(self.request, f'Item "{self.object.name}" was successfully updated.')
        return response

    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the updated item's detail view
        """
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Class-based view for creating new items with initial stock.
    
    Provides a form for creating new inventory items along with their initial
    stock information including organization, expiration date, and quantity.
    """
    model = models.Item
    form_class = TaggedItemWithStockForm
    template_name = "items/create.html"
    permission_required = 'inventory.add_item'

    def form_valid(self, form):
        """
        Process valid form submission and log the creation.
        
        Creates both Item and initial StockItem, then logs separate creation events.
        
        Args:
            form: Valid ItemWithStockForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to new item's detail view
        """
        # Call the custom save method on the form.
        # It returns a tuple of (item, stock_item).
        new_item, stock_item = form.save()

        # Set the view's object to the new Item instance.
        # This is crucial for get_success_url to work correctly.
        self.object = new_item

        # Log item creation event
        audit_log_event(
            self.request.user, 
            f"Created item \"{new_item.name}\"", 
            audit_log_state(None), 
            audit_log_state(new_item)
        )
            
        # Log stock item creation event
        if stock_item:
            audit_log_event(
                self.request.user, 
                f"Checked-in {stock_item.quantity} of \"{new_item.name}\" into location \"{stock_item.location}\" (initial stock from {stock_item.organization.name})", 
                audit_log_state(None), 
                audit_log_state(stock_item)
            )
            messages.success(self.request, f'Item "{new_item.name}" was successfully created and checked in with {stock_item.quantity} units.')
        else:
            messages.success(self.request, f'Item "{new_item.name}" was successfully created.')
        
        # The parent class handles the redirection to success_url.
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """
        Handle form validation errors, with special handling for GTIN duplicates.
        
        If the form has a GTIN duplicate error, redirect to check-in for the existing item.
        Otherwise, show the form with validation errors.
        
        Args:
            form: Invalid ItemWithStockForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to check-in view if GTIN duplicate
            HttpResponse: Rendered form with errors otherwise
        """
        # Check if there's a GTIN duplicate error
        gtin_errors = form.errors.get('gtin', [])
        for error in gtin_errors:
            if hasattr(error, 'code') and error.code == 'duplicate_gtin':
                # Find the existing stock item with this GTIN
                gtin = form.cleaned_data.get('gtin', '').strip()
                if gtin:
                    existing_stock_item = models.StockItem.objects.filter(gtin=gtin).first()
                    if existing_stock_item:
                        # Redirect to check-in view for the existing item
                        return redirect('search_check_in_item', item_uuid=existing_stock_item.item.id)
        
        # Fall back to default form_invalid behavior
        return super().form_invalid(form)
    
    def get_form_kwargs(self):
        """
        Overrides the default method to remove the 'instance' argument,
        which is not compatible with our custom forms.Form.
        """

        kwargs = super().get_form_kwargs()

        if 'instance' in kwargs:
            del kwargs['instance']

        return kwargs 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the new item's detail view
        """
        # self.object is now properly set to the new Item instance
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})
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
        audit_log_event(
            self.request.user, 
            f"Updated \"{self.object.item.name}\" stock in location \"{self.object.location}\"", 
            before_state, 
            after_state
        )
        
        messages.success(self.request, f'Stock for "{self.object.item.name}" in location "{self.object.location}" was successfully updated.')
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
    location = stock_item.location

    # Log the state before deletion
    before_state = audit_log_state(stock_item)

    # Log the deletion event
    audit_log_event(
        request.user,
        f"Deleted {stock_item.quantity} of \"{stock_item.item.name}\" from location \"{stock_item.location}\"",
        before_state,
        audit_log_state(None),
        entity_id=str(stock_item.item.id)
    )

    # Perform deletion
    stock_item.delete()

    messages.success(request, f'Removed {quantity} of "{item_name}" from location "{location}".')
    return redirect('view_item', uuid=item_uuid)


def manufacturer_autocomplete_api(request):
    """
    API endpoint to get list of manufacturers for autocomplete.
    
    Returns JSON list of distinct manufacturers from existing items
    for use in autocomplete functionality.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse: JSON response with manufacturers list
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Get distinct manufacturers that are not empty, limited to active items
    manufacturers = (models.Item.active_objects
                    .exclude(manufacturer='')
                    .values_list('manufacturer', flat=True)
                    .distinct()
                    .order_by('manufacturer'))
    
    return JsonResponse({'manufacturers': list(manufacturers)})


def stock_location_autocomplete_api(request):
    """
    API endpoint to get list of stock locations for autocomplete.
    
    Returns JSON list of distinct stock locations from existing stock items
    for use in autocomplete functionality.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse: JSON response with stock locations list
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Get distinct stock locations that are not empty
    locations = (models.StockItem.objects
                .exclude(location='')
                .values_list('location', flat=True)
                .distinct()
                .order_by('location'))
    
    return JsonResponse({'locations': list(locations)})


def items_search_api(request):
    """
    API endpoint to search items by name, manufacturer, or GTIN.
    
    Performs a search across item names, manufacturers, and GTINs (both item and stock item GTINs)
    and returns matching items with their details for autocomplete functionality.
    
    Query Parameters:
        q: General search query (searches all fields)
        name: Search by item name only
        manufacturer: Search by manufacturer only
        gtin: Search by GTIN only
        limit: Maximum number of results to return (default: 10)
    
    Args:
        request: HTTP request object with query parameters
        
    Returns:
        JsonResponse: JSON response with matching items list and total count
    """
    
    # Get individual search parameters
    general_query = request.GET.get('q', '').strip()
    name_query = request.GET.get('name', '').strip()
    manufacturer_query = request.GET.get('manufacturer', '').strip()
    gtin_query = request.GET.get('gtin', '').strip()
    
    # Get limit parameter with default value
    try:
        limit = int(request.GET.get('limit', 10))
        limit = max(1, min(limit, 50))  # Ensure limit is between 1 and 50
    except (ValueError, TypeError):
        limit = 10
    
    # Check if any query is provided and meets minimum length
    if not any([general_query, name_query, manufacturer_query, gtin_query]):
        return JsonResponse({'items': [], 'total_count': 0, 'has_more': False})
    
    # Check minimum length for any provided query
    queries_to_check = [q for q in [general_query, name_query, manufacturer_query, gtin_query] if q]
    if all(len(q) < 2 for q in queries_to_check):
        return JsonResponse({'items': [], 'total_count': 0, 'has_more': False})
    
    from django.db.models import Q, Sum, Case, When, IntegerField
    
    # Build search conditions (AND logic - all conditions must match)
    search_conditions = Q()
    
    if general_query:
        # General search across all fields (OR within this condition)
        search_conditions &= (
            Q(name__icontains=general_query) | 
            Q(manufacturer__icontains=general_query) |
            Q(gtin__exact=general_query)  # Exact match for GTIN
        )
    
    if name_query:
        search_conditions &= Q(name__icontains=name_query)
    
    if manufacturer_query:
        search_conditions &= Q(manufacturer__icontains=manufacturer_query)
    
    if gtin_query:
        search_conditions &= Q(gtin__exact=gtin_query)  # Exact match for GTIN
    
    
    # Build the base queryset similar to view_subcategory_items
    items_query = models.Item.active_objects.select_related('category', 'subcategory')
    if not request.user.has_perm('inventory.view_internalstockingdetails'):
        items_query = items_query.filter(stock_items__surplus_status__in=['not_wanted'])

    # Search items by the built conditions
    items_qs = (items_query
                .filter(search_conditions)
                .annotate(
                    annotated_total_stock_quantity=Sum(
                        Case(
                            When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                            default=0,
                            output_field=IntegerField()
                        )
                    )
                )
                .filter(annotated_total_stock_quantity__gt=0)  # Only return items with stock
                .values('id', 'name', 'manufacturer', 'gtin', 'category__name', 'subcategory__name', 'annotated_total_stock_quantity'))
    # Also search by stock item GTINs if GTIN queries are provided
    # These items must also match other non-GTIN criteria
    stock_item_matches = []
    if general_query or gtin_query:
        stock_gtin_conditions = Q()
        
        if general_query:
            stock_gtin_conditions |= Q(gtin__exact=general_query)  # Exact match for GTIN
        
        if gtin_query:
            stock_gtin_conditions |= Q(gtin__exact=gtin_query)  # Exact match for GTIN
        
        if stock_gtin_conditions:
            # Build additional conditions for items found via stock GTIN
            additional_item_conditions = Q()
            
            # Apply name and manufacturer filters to stock item matches too
            if name_query:
                additional_item_conditions &= Q(item__name__icontains=name_query)
            
            if manufacturer_query:
                additional_item_conditions &= Q(item__manufacturer__icontains=manufacturer_query)
            
            # If general query exists, it should match name/manufacturer on the item level
            if general_query:
                additional_item_conditions &= (
                    Q(item__name__icontains=general_query) |
                    Q(item__manufacturer__icontains=general_query) |
                    Q(item__gtin__exact=general_query)  # Exact match for GTIN
                )
            
            stock_item_matches = (models.StockItem.objects
                                 .select_related('item', 'item__category', 'item__subcategory')
                                 .filter(stock_gtin_conditions, additional_item_conditions, item__is_deleted=False)
                                 .values_list('item_id', flat=True)
                                 .distinct())
    
    if stock_item_matches:
        # Use the same filtering logic as items_query above for permission checks
        subcategory = None
        if manufacturer_query or name_query:
            # Try to infer subcategory from other filters if needed (optional)
            pass  # No-op, as subcategory is not available in this context

        # Build items_query as in view_subcategory_items
        items_query = models.Item.active_objects.select_related('category', 'subcategory')
        if not request.user.has_perm('inventory.view_internalstockingdetails'):
            items_query = items_query.filter(stock_items__surplus_status__in=['not_wanted'])

        additional_items = (
            items_query
            .filter(id__in=stock_item_matches)
            .annotate(
            annotated_total_stock_quantity=Sum(
                Case(
                When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                default=0,
                output_field=IntegerField()
                )
            )
            )
            .filter(annotated_total_stock_quantity__gt=0)
            .values('id', 'name', 'manufacturer', 'gtin', 'category__name', 'subcategory__name', 'annotated_total_stock_quantity')
        )
        
        # Combine results and remove duplicates
        items_qs = items_qs.union(additional_items)
    
    # Only get GTINs for the items we intend to show (apply limit first)
    limited_item_ids = [item['id'] for item in items_qs[:limit]]
    # Prefetch all stock items for the limited set of items in one query
    stock_items = list(models.StockItem.objects.filter(item_id__in=limited_item_ids))
    # Build lookup tables for GTINs and locations
    stock_gtins_by_item = {}
    locations_by_item = {}
    for stock_item in stock_items:
        item_id = getattr(stock_item, 'item_id', None)
        # GTINs
        if stock_item.gtin:
            stock_gtins_by_item.setdefault(item_id, []).append(stock_item.gtin)
        # Locations (for aggregated_locations logic, if needed)
        if item_id not in locations_by_item:
            locations_by_item[item_id] = set()
        if stock_item.location:
            locations_by_item[item_id].add(stock_item.location)

    # Get total count before applying limit
    total_count = len(items_qs)

    # Build response with GTINs and locations
    items_list = []
    for item in items_qs[:limit]:  # Apply the requested limit
        gtins = []
        if item['gtin']:
            gtins.append(item['gtin'])
        gtins.extend(stock_gtins_by_item.get(item['id'], []))
        # Aggregate locations for this item
        locations = locations_by_item.get(item['id'], set())
        location_str = ", ".join(sorted(locations)) if locations else ""
        items_list.append({
            'id': str(item['id']),
            'name': item['name'],
            'manufacturer': item['manufacturer'],
            'gtins': gtins,
            'category__name': item['category__name'],
            'subcategory__name': item['subcategory__name'],
            'total_stock_quantity': item['annotated_total_stock_quantity'] or 0,
            'location': location_str,
        })
    
    return JsonResponse({
        'items': items_list,
        'total_count': total_count,
        'has_more': total_count > limit,
        'limit': limit
    })


def public_search_view(request):
    """
    Public search page that displays all items in a store-like interface.
    
    Provides a comprehensive view of inventory items with filtering and sorting options.
    Shows all items by default, sorted by last added first, with filtering options for:
    - Tag groups and specific tags
    - Expired vs non-expired items
    - Include zero quantity items
    - View modes: tile view or table view with customizable columns
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with search interface
    """
    # Get all active tag groups and their tags for filter dropdown
    tag_groups = models.TagGroup.objects.filter(is_active=True).prefetch_related(
        models.Prefetch(
            'tags',
            queryset=models.Tag.objects.filter(is_active=True).order_by('sort_order', 'name')
        )
    ).order_by('sort_order', 'name')
    
    context = {
        'tag_groups': tag_groups,
    }
    
    template = loader.get_template("items/public_search.html")
    return HttpResponse(template.render(context, request))


def public_search_api(request):
    """
    API endpoint for the public search functionality with tag-based filtering.
    
    Returns items with comprehensive filtering and pagination support.
    
    Query Parameters:
        offset: Starting position for pagination (default: 0)
        limit: Maximum number of results to return (default: 20, max: 100)
        search: General search query across name, manufacturer, GTIN, and tags
        tag_groups: Comma-separated list of tag group IDs to filter by
        tags: Comma-separated list of tag IDs to filter by
        exclude_expired: Exclude expired items (true/false, default: false)
        include_zero_qty: Include items with zero quantity (true/false, default: false)
        sort_by: Sort field (date_added, name, manufacturer, tags, quantity)
        sort_order: Sort order (asc/desc, default: desc for date_added, asc for others)
        
    Returns:
        JsonResponse: JSON response with items data and pagination info
    """
    from django.db.models import Q, Sum, Case, When, IntegerField, Max, Count
    from django.utils import timezone
    
    # Get pagination parameters
    try:
        offset = int(request.GET.get('offset', 0))
        offset = max(0, offset)
    except (ValueError, TypeError):
        offset = 0
    
    try:
        limit = int(request.GET.get('limit', 20))
        limit = max(1, min(limit, 100))  # Ensure limit is between 1 and 100
    except (ValueError, TypeError):
        limit = 20
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    tag_group_ids = request.GET.get('tag_groups', '').strip()
    tag_ids = request.GET.get('tags', '').strip()
    exclude_expired_param = request.GET.get('exclude_expired', 'false')
    exclude_expired = exclude_expired_param.lower() == 'true' if isinstance(exclude_expired_param, str) else bool(exclude_expired_param)
    include_zero_qty_param = request.GET.get('include_zero_qty', 'false')
    include_zero_qty = include_zero_qty_param.lower() == 'true' if isinstance(include_zero_qty_param, str) else bool(include_zero_qty_param)
    sort_by = request.GET.get('sort_by', 'date_added')
    sort_order = request.GET.get('sort_order', 'desc' if sort_by == 'date_added' else 'asc')
    
    # Build the base queryset with tag prefetching
    items_query = models.Item.active_objects.prefetch_related(
        'tags__tag_group'
    ).select_related()  # Remove category/subcategory as they will be deprecated
    
    # Filter for permission-based access - only show surplus-approved items for public users
    if not request.user.has_perm('inventory.view_internalstockingdetails'):
        items_query = items_query.filter(stock_items__surplus_status__in=['not_wanted'])
    
    # Apply search filter (now includes tags)
    if search_query and len(search_query) >= 2:
        search_conditions = (
            Q(name__icontains=search_query) | 
            Q(manufacturer__icontains=search_query) |
            Q(gtin__exact=search_query) |  # Exact match for GTIN
            Q(tags__name__icontains=search_query) |  # Search in tag names
            Q(tags__tag_group__name__icontains=search_query)  # Search in tag group names
        )
        items_query = items_query.filter(search_conditions)
    
    # Apply tag group filter
    if tag_group_ids:
        try:
            tag_group_list = [tg_id.strip() for tg_id in tag_group_ids.split(',') if tg_id.strip()]
            if tag_group_list:
                items_query = items_query.filter(tags__tag_group__id__in=tag_group_list)
        except (ValueError, TypeError):
            pass
    
    # Apply specific tag filter
    if tag_ids:
        try:
            tag_list = [tag_id.strip() for tag_id in tag_ids.split(',') if tag_id.strip()]
            if tag_list:
                items_query = items_query.filter(tags__id__in=tag_list)
        except (ValueError, TypeError):
            pass
    
    # Annotate with stock information
    today = timezone.now().date()
    items_query = items_query.annotate(
        annotated_total_stock_quantity=Sum(
            Case(
                When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                default=0,
                output_field=IntegerField()
            )
        ),
        expired_stock_quantity=Sum(
            Case(
                When(
                    stock_items__quantity__gt=0,
                    stock_items__expiration_date__lt=today,
                    then='stock_items__quantity'
                ),
                default=0,
                output_field=IntegerField()
            )
        ),
        variant_count=Count('stock_items__detail', distinct=True),
        latest_stock_date=Max('stock_items__date_received')
    )
    
    # Apply quantity filter
    if not include_zero_qty:
        items_query = items_query.filter(annotated_total_stock_quantity__gt=0)
    
    # Apply expiration filter
    if exclude_expired:
        # Only exclude items where ALL stock is expired (no valid stock remaining)
        from django.db.models import F
        items_query = items_query.exclude(
            Q(annotated_total_stock_quantity=F('expired_stock_quantity')) &
            Q(annotated_total_stock_quantity__gt=0)
        )
    
    # Apply sorting
    sort_field = 'name'  # default
    if sort_by == 'date_added':
        sort_field = 'latest_stock_date'
    elif sort_by == 'name':
        sort_field = 'name'
    elif sort_by == 'manufacturer':
        sort_field = 'manufacturer'
    elif sort_by == 'tags':
        # Sort by tag group name, then tag name
        sort_field = 'tags__tag_group__name'
    elif sort_by == 'quantity':
        sort_field = 'annotated_total_stock_quantity'
    
    if sort_order == 'desc':
        sort_field = f'-{sort_field}'
    
    items_query = items_query.order_by(sort_field).distinct()
    
    # Get total count for pagination
    total_count = items_query.count()
    
    # Apply pagination
    items = items_query[offset:offset + limit]
    
    # Prepare response data
    items_list = []
    for item in items:
        # Get the first image URL if available
        first_image = item.images.first()
        image_url = first_image.image_url if first_image else None
        
        # Calculate expiration info
        has_expired_stock = item.expired_stock_quantity > 0 if item.expired_stock_quantity else False
        
        # Get locations
        locations = item.aggregated_locations
        
        # Get tags information
        item_tags = []
        tag_groups_display = []
        tags_by_group = {}
        
        for tag in item.tags.all():
            tag_info = {
                'id': str(tag.id),
                'name': tag.name,
                'color': tag.display_color,
                'text_color': tag.text_color,
                'tag_group': {
                    'id': str(tag.tag_group.id),
                    'name': tag.tag_group.name,
                    'color': tag.tag_group.color,
                    'text_color': tag.tag_group.text_color
                }
            }
            item_tags.append(tag_info)
            
            # Group tags by tag group for display
            group_name = tag.tag_group.name
            if group_name not in tags_by_group:
                tags_by_group[group_name] = []
                tag_groups_display.append(group_name)
            tags_by_group[group_name].append(tag.name)
        
        items_list.append({
            'id': str(item.id),
            'name': item.name,
            'manufacturer': item.manufacturer,
            # Keep legacy fields for backward compatibility during transition
            'category': getattr(item.category, 'name', '') if hasattr(item, 'category') and item.category else '',
            'subcategory': getattr(item.subcategory, 'name', '') if hasattr(item, 'subcategory') and item.subcategory else '',
            # New tag-based fields
            'tags': item_tags,
            'tags_display': item.tags_display,
            'tag_groups_display': ', '.join(tag_groups_display),
            'tags_by_group': tags_by_group,
            'total_stock_quantity': item.annotated_total_stock_quantity or 0,
            'expired_stock_quantity': item.expired_stock_quantity or 0,
            'has_expired_stock': has_expired_stock,
            'variant_count': item.variant_count or 0,
            'image_url': image_url,
            'locations': locations,
            'latest_stock_date': item.latest_stock_date.isoformat() if item.latest_stock_date else None,
            'notes_public': item.notes_public,
            'url': item.url,
        })
    
    return JsonResponse({
        'items': items_list,
        'total_count': total_count,
        'offset': offset,
        'limit': limit,
        'has_more': total_count > offset + limit,
    })