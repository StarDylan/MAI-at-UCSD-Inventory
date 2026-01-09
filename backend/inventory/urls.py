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
    audit_api,
    auth,
    bulk_checkout,
    dashboard,
    images,
    items,
    locations,
    organizations,
    search,
    spreadsheet_import,
    surplus_reports,
    tags,
    users
)

urlpatterns = [
    # Home and Dashboard
    path("", dashboard.index_view, name="home"),
    path("dashboard/", dashboard.dashboard_view, name="dashboard"),
    
    # Database and Items Views
    path('view/item/<uuid:uuid>/', items.view_item_detail, name='view_item'),
    path('view/deleted_items', items.view_deleted_items, name='view_deleted_items'),
    
    # Public Search
    path('search/', items.public_search_view, name='public_search'),
    
    # Audit Logging
    path("view/audit/", audit.AuditLogListView.as_view(), name="audit"),
    
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
    
    # Location Management
    path('locations/', locations.LocationListView.as_view(), name='location_list'),
    path('locations/add/', locations.LocationCreateView.as_view(), name='location_create'),
    path('locations/<uuid:pk>/edit/', locations.LocationUpdateView.as_view(), name='location_update'),
    path('locations/<uuid:pk>/delete/', locations.LocationDeleteView.as_view(), name='location_delete'),
    
    # API endpoints
    path('api/audit/by_user/<int:user_id>/', audit_api.audit_by_user_api, name='audit_by_user_api'),
    path('api/audit/on_user/<int:user_id>/', audit_api.audit_on_user_api, name='audit_on_user_api'),
    path('api/organizations/create/', organizations.organization_create_ajax, name='organization_create_ajax'),
    path('api/organizations/list/', organizations.organization_list_api, name='organization_list_api'),
    path('api/manufacturers/autocomplete/', items.manufacturer_autocomplete_api, name='manufacturer_autocomplete_api'),
    path('api/stock-locations/autocomplete/', items.stock_location_autocomplete_api, name='stock_location_autocomplete_api'),
    path('api/items/search/', items.items_search_api, name='items_search_api'),
    path('api/public-search/', items.public_search_api, name='public_search_api'),
    path('api/items/<uuid:item_id>/details-gtins/', items.item_details_gtins_api, name='item_details_gtins_api'),
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
    path('bulk-checkout/<uuid:checkout_id>/export/', bulk_checkout.export_checkout_items_view, name='checkout_export'),
    path('item/<uuid:item_uuid>/add-to-checkout/', bulk_checkout.add_to_checkout_from_item_view, name='add_to_checkout_from_item'),
    
    # Surplus Reporting
    path('surplus/summary/', surplus_reports.surplus_summary, name='surplus_summary'),
    path('surplus/export/', surplus_reports.export_surplus_report, name='export_surplus_report'),
    path('surplus/upload/', surplus_reports.upload_surplus_report, name='upload_surplus_report'),
    
    # Spreadsheet Import
    path('import/spreadsheet/', spreadsheet_import.upload_spreadsheet, name='spreadsheet_import_upload'),
    path('import/template/', spreadsheet_import.download_import_template, name='download_import_template'),
    
    # Tag Management
    path('tags/groups/', tags.TagGroupListView.as_view(), name='tag_groups_list'),
    path('tags/groups/create/', tags.TagGroupCreateView.as_view(), name='tag_group_create'),
    path('tags/groups/edit/<uuid:pk>/', tags.TagGroupUpdateView.as_view(), name='tag_group_edit'),
    path('tags/groups/delete/<uuid:uuid>/', tags.tag_group_delete_view, name='tag_group_delete'),
    path('api/tags/check-dependencies/<uuid:uuid>/', tags.check_tag_dependencies, name='check_tag_dependencies'),
    path('api/tag-groups/check-dependencies/<uuid:uuid>/', tags.check_tag_group_dependencies, name='check_tag_group_dependencies'),
    path('api/tags/hide/<uuid:uuid>/', tags.hide_tag, name='hide_tag'),
    path('api/tags/hidden/', tags.api_hidden_tags, name='api_hidden_tags'),
    path('api/tags/restore/<uuid:tag_id>/', tags.api_restore_tag, name='api_restore_tag'),
    path('tags/', tags.TagListView.as_view(), name='tag_list'),
    path('tags/create/', tags.TagCreateView.as_view(), name='tag_create'),
    path('tags/edit/<uuid:pk>/', tags.TagUpdateView.as_view(), name='tag_edit'),
    path('tags/delete/<uuid:uuid>/', tags.tag_delete_view, name='tag_delete'),
    path('tags/bulk-create/', tags.tag_bulk_create_view, name='tag_bulk_create'),
    
    # User Management
    path('manage/users/', users.manage_users_view, name='manage_users'),
    path('edit/user/<int:pk>/', users.edit_user_role_api, name='edit_user_role'),
    path('edit/user/profile/<int:pk>/', users.edit_user_view, name='edit_user'),
    path('view/user/<int:pk>/', users.view_user_profile_view, name='view_user'),
    path('delete/user/<int:pk>/', users.delete_user_view, name='delete_user'),
    path('restore/user/<int:pk>/', users.restore_user_view, name='restore_user'),
    path('create/user/', users.UserCreateView.as_view(), name='create_user'),
    
    # Authentication
    path('accounts/profile/', dashboard.profile_view, name='profile'),
    path('accounts/logout/', auth.logout_view, name='logout'),
    path('accounts/not-recognized/', auth.AccountNotRecognizedView.as_view(), name='account_not_recognized'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)