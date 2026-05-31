"""
GTIN (Global Trade Item Number) related API endpoints.
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from inventory import models


def item_details_gtins_api(request, item_id):
    """
    API endpoint to get all details and GTINs for a given item.
    
    Returns a JSON list of {detail, gtin} for each stock item variant, plus the item-level GTIN if present.
    
    Args:
        request: HTTP request object
        item_id: UUID of the item
        
    Returns:
        JsonResponse: JSON response with details and GTINs
    """
    item = get_object_or_404(models.Item, id=item_id)
    details = []
    # Add item-level GTIN if present and no variants
    if item.gtin:
        details.append({'detail': '', 'gtin': item.gtin})
    # Add all stock item variants
    stock_items = models.StockItem.objects.filter(item=item, detail__isnull=False).exclude(detail='')
    for si in stock_items:
        details.append({'detail': si.detail, 'gtin': si.gtin})
    return JsonResponse({'details': details})
