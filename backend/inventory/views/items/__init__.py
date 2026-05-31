"""
Items views package - organized into logical modules for better maintainability.

This package contains all views related to item management, including:
- Detail views for displaying item information
- CRUD views for creating and updating items
- Deletion and restoration views
- Stock item management views
- Search and autocomplete APIs
- GTIN-related APIs
"""

# Detail views
from .detail import view_item_detail, public_search_view, public_search_api

# CRUD views
from .crud import ItemUpdateView, ItemCreateView

# Delete/Restore views
from .delete import item_soft_delete_view, item_restore_view, view_deleted_items

# Stock views
from .stock import StockItemUpdateView, stock_item_delete_view, transfer_stock_from_item_view

# Search APIs
from .search import items_search_api

# Autocomplete APIs
from .autocomplete import manufacturer_autocomplete_api, stock_location_autocomplete_api

# GTIN APIs
from .gtins import item_details_gtins_api

__all__ = [
    # Detail views
    'view_item_detail',
    'public_search_view',
    'public_search_api',
    # CRUD views
    'ItemUpdateView',
    'ItemCreateView',
    # Delete/Restore views
    'item_soft_delete_view',
    'item_restore_view',
    'view_deleted_items',
    # Stock views
    'StockItemUpdateView',
    'stock_item_delete_view',
    'transfer_stock_from_item_view',
    # Search APIs
    'items_search_api',
    # Autocomplete APIs
    'manufacturer_autocomplete_api',
    'stock_location_autocomplete_api',
    # GTIN APIs
    'item_details_gtins_api',
]
