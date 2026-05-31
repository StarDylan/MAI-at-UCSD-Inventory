"""
Autocomplete API endpoints for item-related fields.
"""

from django.http import JsonResponse

from inventory import models


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
