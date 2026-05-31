"""
Item search API endpoints for searching and filtering items.
"""

from django.http import JsonResponse
from django.db.models import Q, Sum, Case, When, IntegerField

from inventory import models


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
    include_zero_stock = request.GET.get('include_zero_stock', 'false').lower() == 'true'
    
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
    
    # Check for exact GTIN match first - if found, prioritize it over name/manufacturer filters
    exact_gtin_match = None
    if gtin_query:
        exact_gtin_match = gtin_query
    elif general_query and len(general_query) >= 8:  # GTINs are typically 8+ digits
        # Check if general_query could be a GTIN by trying exact match
        exact_gtin_match = general_query
    
    search_conditions = Q()
    use_exact_gtin_priority = False
    
    if exact_gtin_match:
        # First check if there's an exact GTIN match (item level or stock level)
        gtin_exists = (
            models.Item.active_objects.filter(gtin__exact=exact_gtin_match).exists() or
            models.StockItem.objects.filter(gtin__exact=exact_gtin_match, item__is_deleted=False).exists()
        )
        
        if gtin_exists:
            # If exact GTIN match exists, use only GTIN condition and ignore name/manufacturer
            use_exact_gtin_priority = True
            search_conditions = Q(gtin__exact=exact_gtin_match) | Q(stock_items__gtin__exact=exact_gtin_match)
    
    if not use_exact_gtin_priority:
        # First, handle the case where we have both a GTIN query and name/manufacturer queries
        if gtin_query and (name_query or manufacturer_query):
            # Create two separate condition sets - one for GTIN and one for name/manufacturer
            gtin_conditions = Q(gtin__exact=gtin_query) | Q(stock_items__gtin__exact=gtin_query)
            text_conditions = Q()
            
            if name_query:
                text_conditions |= Q(name__icontains=name_query)
            
            if manufacturer_query:
                text_conditions |= Q(manufacturer__icontains=manufacturer_query)
            
            # Use OR logic between GTIN and name/manufacturer conditions
            search_conditions = gtin_conditions | text_conditions
        else:
            # Handle each query type separately with AND logic between different query types
            if general_query:
                # Check if this looks like a GTIN (8+ digits, mostly numeric)
                is_gtin_search = len(general_query) >= 8 and general_query.replace('-', '').replace(' ', '').isdigit()
                
                if is_gtin_search:
                    # For GTIN searches, only search GTIN fields to avoid duplicates
                    search_conditions &= (
                        Q(gtin__exact=general_query) |  # Exact match for item-level GTIN
                        Q(stock_items__gtin__exact=general_query)  # Exact match for stock item GTIN
                    )
                else:
                    # General search across text fields (OR within this condition)
                    search_conditions &= (
                        Q(name__icontains=general_query) | 
                        Q(manufacturer__icontains=general_query)
                    )
            
            if name_query:
                search_conditions &= Q(name__icontains=name_query)
            
            if manufacturer_query:
                search_conditions &= Q(manufacturer__icontains=manufacturer_query)
            
            if gtin_query and not (name_query or manufacturer_query):
                search_conditions &= (Q(gtin__exact=gtin_query) | Q(stock_items__gtin__exact=gtin_query))  # Exact match for both item and stock item GTIN
    
    # Build the base queryset similar to view_subcategory_items
    items_query = models.Item.active_objects
    if not request.user.has_perm('inventory.view_internalstockingdetails'):
        items_query = items_query.filter(stock_items__surplus_status__in=['not_wanted'])

    # Search items by the built conditions
    items_qs = (items_query
                .filter(search_conditions)
                .distinct()  # Prevent duplicates when joining with stock_items
                .annotate(
                    annotated_total_stock_quantity=Sum(
                        Case(
                            When(stock_items__quantity__gt=0, then='stock_items__quantity'),
                            default=0,
                            output_field=IntegerField()
                        )
                    )
                ))
                
    # Apply stock quantity filter based on parameter
    if not include_zero_stock:
        items_qs = items_qs.filter(annotated_total_stock_quantity__gt=0)  # Only return items with stock
        
    items_qs = items_qs.values('id', 'name', 'manufacturer', 'gtin', 'annotated_total_stock_quantity')
    # Also search by stock item GTINs if GTIN queries are provided
    # These items must also match other non-GTIN criteria (unless exact GTIN priority is used)
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
            
            if use_exact_gtin_priority:
                # If using exact GTIN priority, only filter by GTIN - ignore name/manufacturer
                pass  # No additional conditions needed
            else:
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
                                 .select_related('item')
                                 .filter(stock_gtin_conditions, additional_item_conditions, item__is_deleted=False)
                                 .values_list('item_id', flat=True)
                                 .distinct())
    
    if stock_item_matches:
        # Use the same filtering logic as items_query above for permission checks
        if manufacturer_query or name_query:
            # Try to infer subcategory from other filters if needed (optional)
            pass  # No-op, as subcategory is not available in this context

        # Build items_query as in view_subcategory_items
        items_query = models.Item.active_objects
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
            ))
            
        # Apply stock quantity filter based on parameter
        if not include_zero_stock:
            additional_items = additional_items.filter(annotated_total_stock_quantity__gt=0)
            
        additional_items = additional_items.values('id', 'name', 'manufacturer', 'gtin', 'annotated_total_stock_quantity')
        
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
        locations_by_item[item_id].add(stock_item.location_new.name)

    # Get total count before applying limit
    total_count = len(items_qs)

    # Build response with GTINs, locations, and details for each item
    items_list = []
    for item in items_qs[:limit]:  # Apply the requested limit
        gtins = []
        if item['gtin']:
            gtins.append(item['gtin'])
        gtins.extend(stock_gtins_by_item.get(item['id'], []))
        gtins = list(dict.fromkeys(gtins))
        locations = locations_by_item.get(item['id'], set())
        location_str = ", ".join(sorted(locations)) if locations else ""

        # Gather details/GTINs for this item
        details = []
        # Add item-level GTIN if present and no variants
        if item['gtin']:
            details.append({'detail': '', 'gtin': item['gtin']})
        # Add all stock item variants (details/gtin)
        for stock_item in stock_items:
            if getattr(stock_item, 'item_id', None) == item['id'] and getattr(stock_item, 'detail', None):
                if stock_item.detail:
                    details.append({'detail': stock_item.detail, 'gtin': stock_item.gtin})

        items_list.append({
            'id': str(item['id']),
            'name': item['name'],
            'manufacturer': item['manufacturer'],
            'gtins': gtins,
            'total_stock_quantity': item['annotated_total_stock_quantity'] or 0,
            'location': location_str,
            'details_gtins': details,
            'has_item_gtin': bool(item['gtin']),
        })
    
    return JsonResponse({
        'items': items_list,
        'total_count': total_count,
        'has_more': total_count > limit,
        'limit': limit
    })
