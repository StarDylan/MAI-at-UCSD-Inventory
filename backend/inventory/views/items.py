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
from django.views.generic import UpdateView, CreateView

from inventory import models
from inventory.forms import ItemForm, ItemWithStockForm, StockItemEditForm
from inventory.models import Category, Item, Subcategory, AuditEvent, StockItem
from .utils import audit_log_state, audit_log_event


def view_database(request):
    """
    Display the main database view with all categories and subcategories.
    
    Shows a hierarchical view of the database structure with categories
    and their related subcategories.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with categories and subcategories
    """
    # Use prefetch_related to efficiently load subcategories
    categories = Category.objects.prefetch_related('subcategories').all().order_by('name')

    context = {
        'categories': categories,
    }

    template = loader.get_template("categories/list.html")
    return HttpResponse(template.render(context, request))


def view_all_items(request):
    """
    Display all items in the inventory system.
    
    Shows a comprehensive list of all items with their category and
    subcategory information.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with all items
    """
    from django.db.models import Sum, Case, When, IntegerField
    
    # Fetch all items with related category and subcategory data
    # Use annotations to avoid N+1 queries for total_stock_quantity
    items = (Item.active_objects
            .select_related('category', 'subcategory')
            .annotate(
                stock_items_quantity_annotated=Sum(
                    Case(
                        When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                        default=0,
                        output_field=IntegerField()
                    )
                )
            )
            .order_by('name'))

    context = {
        'items': items,
        'category': "All Items"
    }

    template = loader.get_template("items/list.html")
    return HttpResponse(template.render(context, request))


def view_category_items(request, uuid):
    """
    Display all items belonging to a specific category.
    
    Args:
        request: HTTP request object
        uuid: UUID of the category to view
        
    Returns:
        HttpResponse: Rendered template with category items
        
    Raises:
        Http404: If category with given UUID doesn't exist
    """
    from django.db.models import Sum, Case, When, IntegerField
    
    category = get_object_or_404(Category, id=uuid)
    
    # Fetch items in the category with related data
    # Use annotations to avoid N+1 queries for total_stock_quantity
    items = (Item.active_objects
            .filter(category=category)
            .select_related('category', 'subcategory')
            .annotate(
                stock_items_quantity_annotated=Sum(
                    Case(
                        When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                        default=0,
                        output_field=IntegerField()
                    )
                )
            )
            .order_by('name'))

    context = {
        'category': category,
        'items': items,
    }

    template = loader.get_template("items/list.html")
    return HttpResponse(template.render(context, request))


def view_subcategory_items(request, uuid):
    """
    Display all items belonging to a specific subcategory.
    
    Args:
        request: HTTP request object
        uuid: UUID of the subcategory to view
        
    Returns:
        HttpResponse: Rendered template with subcategory items
        
    Raises:
        Http404: If subcategory with given UUID doesn't exist
    """
    from django.db.models import Sum, Case, When, IntegerField
    
    subcategory = get_object_or_404(Subcategory, id=uuid)
    
    # Fetch items in the subcategory with related data
    # Use annotations to avoid N+1 queries for total_stock_quantity
    items = (Item.active_objects
            .filter(subcategory=subcategory)
            .select_related('category', 'subcategory')
            .annotate(
                stock_items_quantity_annotated=Sum(
                    Case(
                        When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                        default=0,
                        output_field=IntegerField()
                    )
                )
            )
            .order_by('name'))

    context = {
        'subcategory': subcategory,
        'items': items,
    }
    
    template = loader.get_template("items/list.html")
    return HttpResponse(template.render(context, request))


def view_item_detail(request, uuid):
    """
    Display detailed information for a specific item.
    
    Shows item details, stock items with expiration dates, associated images, and audit history.
    Handles permissions for viewing deleted items.
    
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
    stock_items = item.stock_items.select_related('organization').order_by('detail', 'expiration_date', 'date_received')
    
    # Get audit events for the item and its stock items in a single query
    entity_ids = [str(uuid)] + list(stock_items.values_list('id', flat=True))
    all_events = AuditEvent.objects.filter(entity_id__in=entity_ids).order_by('created_at')

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
    form_class = ItemForm
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
    form_class = ItemWithStockForm
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
                f"Added initial stock for item \"{new_item.name}\" - {stock_item.quantity} units from {stock_item.organization.name}", 
                audit_log_state(None), 
                audit_log_state(stock_item)
            )
        
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
            f"Updated stock item for \"{self.object.item.name}\" from {self.object.location}", 
            before_state, 
            after_state
        )
        
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
    
    # Log the state before deletion
    before_state = audit_log_state(stock_item)
    
    # Log the deletion event
    audit_log_event(
        request.user, 
        f"Deleted stock item for \"{stock_item.item.name}\" - {stock_item.quantity} units from {stock_item.location}", 
        before_state, 
        audit_log_state(None)
    )
    
    # Perform deletion
    stock_item.delete()
    
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
    
    # Search items by the built conditions
    items_qs = (models.Item.active_objects
                .select_related('category', 'subcategory')
                .filter(search_conditions)
                .annotate(
                    total_stock_quantity=Sum(
                        Case(
                            When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                            default=0,
                            output_field=IntegerField()
                        )
                    )
                )
                .filter(total_stock_quantity__gt=0)  # Only return items with stock
                .values('id', 'name', 'manufacturer', 'gtin', 'category__name', 'subcategory__name', 'total_stock_quantity'))
    
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
        additional_items = (models.Item.active_objects
                          .select_related('category', 'subcategory')
                          .filter(id__in=stock_item_matches)
                          .annotate(
                              total_stock_quantity=Sum(
                                  Case(
                                      When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                                      default=0,
                                      output_field=IntegerField()
                                  )
                              )
                          )
                          .filter(total_stock_quantity__gt=0)  # Only return items with stock
                          .values('id', 'name', 'manufacturer', 'gtin', 'category__name', 'subcategory__name', 'total_stock_quantity'))
        
        # Combine results and remove duplicates
        items_qs = items_qs.union(additional_items)
    
    # Get all unique item IDs for GTIN lookup
    item_ids = [item['id'] for item in items_qs]
    
    # Get all stock GTINs for these items
    stock_gtins_by_item = {}
    if item_ids:
        stock_gtins = models.StockItem.objects.filter(
            item_id__in=item_ids,
            gtin__gt=''
        ).values('item_id', 'gtin').distinct()
        
        for stock_gtin in stock_gtins:
            item_id = stock_gtin['item_id']
            if item_id not in stock_gtins_by_item:
                stock_gtins_by_item[item_id] = []
            stock_gtins_by_item[item_id].append(stock_gtin['gtin'])
    
    # Get total count before applying limit
    total_count = len(items_qs)
    
    # Build response with GTINs
    items_list = []
    for item in items_qs[:limit]:  # Apply the requested limit
        gtins = []
        if item['gtin']:
            gtins.append(item['gtin'])
        gtins.extend(stock_gtins_by_item.get(item['id'], []))
        
        items_list.append({
            'id': str(item['id']),
            'name': item['name'],
            'manufacturer': item['manufacturer'],
            'gtins': gtins,
            'category__name': item['category__name'],
            'subcategory__name': item['subcategory__name'],
            'total_stock_quantity': item['total_stock_quantity'] or 0,
        })
    
    return JsonResponse({
        'items': items_list,
        'total_count': total_count,
        'has_more': total_count > limit,
        'limit': limit
    })