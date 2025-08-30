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
    categories,
    dashboard,
    images,
    items,
    search,
    subcategories,
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
    path('create/item/', items.ItemCreateView.as_view(), name='create_item'),
    path('delete/item/<uuid:uuid>/', items.item_soft_delete_view, name='delete_item'),
    path('restore/item/<uuid:uuid>/', items.item_restore_view, name='restore_item'),
    
    # Image Management
    path('delete/image/', images.image_delete_list_view, name='delete_image_list_view'),
    path('delete/image/<uuid:uuid>/', images.image_delete_view, name='delete_image'),
    path('upload/photo/<uuid:uuid>/', images.image_upload_view, name='upload_photo'),
    
    # Search and Quantity Management
    path('search/check_in/', search.SearchCheckInView.as_view(), name='search_check_in'),
    path('search/check_out/', search.SearchCheckOutView.as_view(), name='search_check_out'),
    
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