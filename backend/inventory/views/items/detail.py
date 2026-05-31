"""
Item detail views for displaying item information and public search interface.
"""

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Sum, Case, When, IntegerField, Count, F, Q
from django.utils import timezone
from django.http import JsonResponse
from uuid import UUID

from inventory import models
from inventory.models import Item, AuditEvent, StockItem, Tag


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
    # Use all_objects manager to include deleted items with optimized tag prefetching
    item = get_object_or_404(
        Item.objects.prefetch_related(
            # Only prefetch active tags from active tag groups
            Prefetch(
                'tags',
                queryset=models.Tag.objects.filter(is_active=True, tag_group__is_active=True).select_related('tag_group')
            )
        ),
        id=uuid
    )

    # Check permissions for viewing deleted items
    if (item.is_deleted and 
        (not request.user.is_authenticated or 
         not request.user.has_perm('inventory.view_deleteditem'))):
        return HttpResponseForbidden()

    # Fetch related images, stock items, and audit events with optimized queries
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
        Prefetch(
            'tags',
            queryset=models.Tag.objects.filter(is_active=True).order_by('name')
        )
    ).order_by('sort_order', 'name')
    
    selected_location_name = ""
    location_uuid = request.GET.get('location_uuid', '').strip()
    if location_uuid:
        try:
            location_uuid = str(UUID(location_uuid))
            selected_location_name = models.Location.objects.filter(id=location_uuid).values_list('name', flat=True).first() or ""
        except (ValueError, TypeError, AttributeError):
            selected_location_name = ""

    context = {
        'tag_groups': tag_groups,
        'selected_location_name': selected_location_name,
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
        location_uuid: Optional location UUID to restrict items to stock at that location
        tag_groups: Comma-separated list of tag group IDs to filter by
        tags: Comma-separated list of tag IDs to filter by
        exclude_expired: Exclude expired items (true/false, default: false)
        sort_by: Sort field (date_added, name, manufacturer, tags, quantity)
        sort_order: Sort order (asc/desc, default: desc for date_added, asc for others)
        
    Returns:
        JsonResponse: JSON response with items data and pagination info
    """
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
    location_uuid = request.GET.get('location_uuid', '').strip()

    tag_ids = request.GET.get('tags', '').strip()
    excluded_tag_ids = request.GET.get('excluded_tags', '').strip()

    exclude_expired_param = request.GET.get('exclude_expired', 'false')
    exclude_expired = exclude_expired_param.lower() == 'true' if isinstance(exclude_expired_param, str) else bool(exclude_expired_param)
    
    sort_by = request.GET.get('sort_by', 'last_updated')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Check user permissions
    has_internal_details_perm = request.user.has_perm('inventory.view_internalstockingdetails')
    
    # Start with stock items queryset and filter based on permissions
    stock_items_query = models.StockItem.objects.select_related('item', 'organization').filter(
        item__is_deleted=False,  # Only active items
        quantity__gt=0
    )
    
    # Filter for permission-based access - only show surplus-approved items for public users
    if not has_internal_details_perm:
        stock_items_query = stock_items_query.filter(surplus_status__in=['not_wanted'])

    # URL-only location filter: keep only stock items at a specific location UUID.
    if location_uuid:
        try:
            location_uuid = str(UUID(location_uuid))
        except (ValueError, TypeError, AttributeError):
            return JsonResponse({
                'items': [],
                'total_count': 0,
                'offset': offset,
                'limit': limit,
                'has_more': False,
            })
        stock_items_query = stock_items_query.filter(location_new_id=location_uuid)
    
    # Apply search filter to stock items and their related items
    search_conditions = Q()
    if search_query and len(search_query) >= 2:        
        # Check if this looks like a GTIN (8+ digits, mostly numeric)
        is_gtin_search = len(search_query) >= 8 and search_query.replace('-', '').replace(' ', '').isdigit()
        
        if is_gtin_search:
            # For GTIN searches, only search GTIN fields to avoid duplicates
            search_conditions = (
                Q(item__gtin__exact=search_query) |  # Exact match for item-level GTIN
                Q(gtin__exact=search_query)  # Exact match for stock item GTIN
            )
        else:
            # For non-GTIN searches, search all text fields
            search_conditions = (
                Q(item__name__icontains=search_query) | 
                Q(item__manufacturer__icontains=search_query) |
                Q(item__tags__name__icontains=search_query) |  # Search in tag names
                Q(item__tags__tag_group__name__icontains=search_query)  # Search in tag group names
            )
    
    
    stock_items_query = stock_items_query.filter(search_conditions)
    
    # Apply specific tag filter
    if tag_ids:
        try:
            tag_list = [tag_id.strip() for tag_id in tag_ids.split(',') if tag_id.strip()]
            if tag_list:
                stock_items_query = stock_items_query.filter(item__tags__id__in=tag_list)
        except (ValueError, TypeError):
            pass
    
    # Apply excluded tag filter
    if excluded_tag_ids:
        try:
            excluded_tag_list = [tag_id.strip() for tag_id in excluded_tag_ids.split(',') if tag_id.strip()]
            if excluded_tag_list:
                stock_items_query = stock_items_query.exclude(item__tags__id__in=excluded_tag_list)
        except (ValueError, TypeError):
            pass
    
    # Get unique item IDs from the filtered stock items
    item_ids = stock_items_query.values_list('item_id', flat=True).distinct()
    
    # Now build the items query from the filtered item IDs with proper prefetching
    items_query = models.Item.active_objects.filter(
        id__in=item_ids
    ).prefetch_related(
        # Only prefetch active tags from active tag groups
        Prefetch(
            'tags',
            queryset=models.Tag.objects.filter(is_active=True, tag_group__is_active=True).select_related('tag_group')
        ),
        # Prefetch images ordered by ID to get first image efficiently
        Prefetch('images', queryset=models.Image.objects.order_by('id')),
        # Prefetch stock items with organization for location aggregation and surplus status checks
        Prefetch(
            'stock_items', 
            queryset=models.StockItem.objects.select_related('organization').filter(quantity__gt=0)
        )
    ).select_related()
    
    # Add distinct to prevent duplicates when joining with stock_items, tags, etc.
    items_query = items_query.distinct()
    
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
        variant_count=Count('stock_items__detail', distinct=True)
    )
    
    # Apply expiration filter
    if exclude_expired:
        # Only exclude items where ALL stock is expired (no valid stock remaining)
        items_query = items_query.exclude(
            Q(annotated_total_stock_quantity=F('expired_stock_quantity')) &
            Q(annotated_total_stock_quantity__gt=0)
        )
    
    # Apply sorting
    sort_field = 'name'  # default
    if sort_by == 'last_updated':
        sort_field = 'last_updated'
    elif sort_by == 'name':
        sort_field = 'name'
    elif sort_by == 'manufacturer':
        sort_field = 'manufacturer'
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
        # Get the first image URL if available - use thumbnail for public search performance
        # Use prefetched images to avoid additional query
        images = list(item.images.all())
        first_image = images[0] if images else None
        image_url = first_image.get_thumbnail_url() if first_image else None
        
        # Calculate expiration info
        has_expired_stock = item.expired_stock_quantity > 0 if item.expired_stock_quantity else False
        
        # Get locations from prefetched stock items to avoid additional queries
        prefetched_stock_items = list(item.stock_items.all())
        locations_set = set()
        for stock_item in prefetched_stock_items:
            if stock_item.location_new.name:
                locations_set.add(stock_item.location_new.name)
        locations = ", ".join(sorted(locations_set))
        
        # Check surplus status information for users with internal stocking details permission
        # Use prefetched stock items to avoid additional queries
        has_pending_surplus = False
        has_wanted_surplus = False
        if request.user.has_perm('inventory.view_internalstockingdetails'):
            # Check surplus status from prefetched stock items
            has_pending_surplus = any(
                stock_item.surplus_status == 'pending' and stock_item.quantity > 0 
                for stock_item in prefetched_stock_items
            )
            has_wanted_surplus = any(
                stock_item.surplus_status == 'wanted' and stock_item.quantity > 0 
                for stock_item in prefetched_stock_items
            )
        
        # Get tags information from prefetched tags
        item_tags = []
        tag_groups_display = []
        tags_by_group = {}
        
        # Get all tags and sort them properly for tags_display
        all_tags = list(item.tags.all())
        all_tags.sort(key=lambda t: (t.tag_group.sort_order or 0, t.name))
        
        # Compute tags_display using prefetched data to avoid N+1 query
        tags_display = ', '.join(tag.name for tag in all_tags) if all_tags else ""
        
        for tag in all_tags:
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
            # New tag-based fields
            'tags': item_tags,
            'tags_display': tags_display,
            'tag_groups_display': ', '.join(tag_groups_display),
            'tags_by_group': tags_by_group,
            'total_stock_quantity': item.annotated_total_stock_quantity or 0,
            'expired_stock_quantity': item.expired_stock_quantity or 0,
            'has_expired_stock': has_expired_stock,
            'has_pending_surplus': has_pending_surplus,
            'has_wanted_surplus': has_wanted_surplus,
            'variant_count': item.variant_count or 0,
            'image_url': image_url,
            'locations': locations,
            'last_updated': item.last_updated.isoformat() if item.last_updated else None,
            'notes_public': item.notes_public,
            'url': item.url,
        })
    
    return JsonResponse({
        'items': items_list,
        'total_count': total_count,
        'offset': offset,
        'limit': limit,
        'has_more': total_count > offset + limit,
        'user_permissions': {
            'view_internal_stocking_details': has_internal_details_perm,
        },
    })
