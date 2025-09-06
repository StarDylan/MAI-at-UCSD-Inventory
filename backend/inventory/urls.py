"""
URL patterns for the inventory application.

This module defines all URL routes for the inventory system, organized by functionality.
Routes are grouped logically and use the reorganized view modules for better maintainability.
"""

from django.conf import settings
from django.urls import path
from django.conf.urls.static import static

from inventory.views import (
    audit,
    auth,
    bulk_checkout,
    categories,
    dashboard,
    images,
    items,
    organizations,
    search,
    subcategories,
    surplus_reports,
    users
)

urlpatterns = [
    # Home and Dashboard
    path("", dashboard.index_view, name="home"),
    path("dashboard/", dashboard.dashboard_view, name="dashboard"),
    
    # Database and Items Views
    path("view_database/", items.view_database, name="view_database"),
    path('view/', items.view_database, name='view_database'),
    path('view/all/', items.view_all_items, name='view_all_items'),
    path('view/category/<uuid:uuid>/', items.view_category_items, name='view_category'),
    path('view/subcategory/<uuid:uuid>/', items.view_subcategory_items, name='view_subcategory'),
    path('view/item/<uuid:uuid>/', items.view_item_detail, name='view_item'),
    path('view/deleted_items', items.view_deleted_items, name='view_deleted_items'),
    
    # Audit Logging
    path("view/audit/", audit.audit_log_list_view, name="audit"),
    
    # Category Management
    path('delete/category/', categories.category_delete_list_view, name='delete_category_list_view'),
    path('delete/category/<uuid:uuid>/', categories.category_delete_view, name='delete_category'),
    path('edit/category/<uuid:pk>/', categories.CategoryUpdateView.as_view(), name='edit_category'),
    path('create/category/', categories.CategoryCreateView.as_view(), name='create_category'),
    
    # Subcategory Management  
    path('delete/subcategory/', subcategories.subcategory_delete_list_view, name='delete_subcategory_list_view'),
    path('delete/subcategory/<uuid:uuid>/', subcategories.subcategory_delete_view, name='delete_subcategory'),
    path('create/subcategory/', subcategories.SubcategoryCreateView.as_view(), name='create_subcategory'),
    
    # Item Management
    path('edit/item/<uuid:pk>/', items.ItemUpdateView.as_view(), name='edit_item'),
    path('edit/stock/<uuid:pk>/', items.StockItemUpdateView.as_view(), name='edit_stock_item'),
    path('delete/stock/<uuid:uuid>/', items.stock_item_delete_view, name='delete_stock_item'),
    path('create/item/', items.ItemCreateView.as_view(), name='create_item'),
    path('delete/item/<uuid:uuid>/', items.item_soft_delete_view, name='delete_item'),
    path('restore/item/<uuid:uuid>/', items.item_restore_view, name='restore_item'),
    
    # Organization Management
    path('organizations/', organizations.OrganizationListView.as_view(), name='organization_list'),
    path('organizations/create/', organizations.OrganizationCreateView.as_view(), name='create_organization'),
    path('organizations/edit/<uuid:pk>/', organizations.OrganizationUpdateView.as_view(), name='edit_organization'),
    # API endpoints
    path('api/organizations/create/', organizations.organization_create_ajax, name='organization_create_ajax'),
    path('api/organizations/list/', organizations.organization_list_api, name='organization_list_api'),
    path('api/manufacturers/autocomplete/', items.manufacturer_autocomplete_api, name='manufacturer_autocomplete_api'),
    path('api/stock-locations/autocomplete/', items.stock_location_autocomplete_api, name='stock_location_autocomplete_api'),
    path('api/items/search/', items.items_search_api, name='items_search_api'),
    path('api/items/<uuid:item_uuid>/stock-items/', bulk_checkout.get_stock_items_api, name='get_stock_items_api'),
    
    # Image Management
    path('delete/image/', images.image_delete_list_view, name='delete_image_list_view'),
    path('delete/image/<uuid:uuid>/', images.image_delete_view, name='delete_image'),
    path('upload/photo/<uuid:uuid>/', images.image_upload_view, name='upload_photo'),
    
    # Search and Quantity Management
    path('search/check_in/', search.SearchCheckInView.as_view(), name='search_check_in'),
    path('search/check_in/<uuid:item_uuid>/', search.SearchCheckInView.as_view(), name='search_check_in_item'),
    
    # Bulk Checkout System
    path('bulk-checkout/', bulk_checkout.BulkCheckoutListView.as_view(), name='bulk_checkout_list'),
    path('bulk-checkout/create/', bulk_checkout.checkout_create_view, name='checkout_create'),
    path('bulk-checkout/<uuid:checkout_id>/', bulk_checkout.checkout_detail_view, name='checkout_detail'),
    path('bulk-checkout/<uuid:checkout_id>/add-item/', bulk_checkout.checkout_add_item_view, name='checkout_add_item'),
    path('bulk-checkout/<uuid:checkout_id>/edit-item/<uuid:item_id>/', bulk_checkout.checkout_edit_item_view, name='checkout_edit_item'),
    path('bulk-checkout/<uuid:checkout_id>/edit-item-detail/<uuid:item_id>/', bulk_checkout.checkout_edit_item_detail_view, name='checkout_edit_item_detail'),
    path('bulk-checkout/<uuid:checkout_id>/remove-item/<uuid:item_id>/', bulk_checkout.checkout_remove_item_view, name='checkout_remove_item'),
    path('bulk-checkout/<uuid:checkout_id>/complete/', bulk_checkout.checkout_complete_view, name='checkout_complete'),
    path('bulk-checkout/<uuid:checkout_id>/undo/', bulk_checkout.checkout_undo_view, name='checkout_undo'),
    path('bulk-checkout/<uuid:checkout_id>/delete/', bulk_checkout.checkout_delete_view, name='checkout_delete'),
    path('item/<uuid:item_uuid>/add-to-checkout/', bulk_checkout.add_to_checkout_from_item_view, name='add_to_checkout_from_item'),
    
    # Surplus Reporting
    path('surplus/summary/', surplus_reports.surplus_summary, name='surplus_summary'),
    path('surplus/export/', surplus_reports.export_surplus_report, name='export_surplus_report'),
    path('surplus/upload/', surplus_reports.upload_surplus_report, name='upload_surplus_report'),
    
    # User Management
    path('manage/users/', users.manage_users_view, name='manage_users'),
    path('edit/user/<int:pk>/', users.edit_user_role_api, name='edit_user_role'),
    path('view/user/<int:pk>/', users.view_user_profile_view, name='view_user'),
    path('delete/user/<int:pk>/', users.delete_user_view, name='delete_user'),
    path('restore/user/<int:pk>/', users.restore_user_view, name='restore_user'),
    path('create/user/', users.UserCreateView.as_view(), name='create_user'),
    
    # Authentication
    path('accounts/profile/', dashboard.profile_view, name='profile'),
    path('accounts/logout/', auth.logout_view, name='logout'),
    path('accounts/not-recognized/', auth.AccountNotRecognizedView.as_view(), name='account_not_recognized'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)