"""
Views package for the inventory application.

This package organizes all view functions and classes into logical modules
for better maintainability and navigation. Each module handles a specific
aspect of the inventory system functionality.

Modules:
    - audit: Audit logging and history views
    - auth: Authentication and authorization views
    - categories: Category CRUD operations
    - dashboard: Main dashboard and navigation views
    - images: Image upload and management views
    - items: Item CRUD operations and viewing
    - search: Search and quantity management views
    - subcategories: Subcategory CRUD operations
    - users: User management and administration views
    - utils: Shared utility functions and helpers
"""

# Import all view functions and classes for easy access
from .audit import audit_log_list_view
from .auth import logout_view, AccountNotRecognizedView, GoogleLoginView
from .categories import (
    category_delete_list_view, category_delete_view, 
    CategoryUpdateView, CategoryCreateView
)
from .dashboard import index_view, dashboard_view, profile_view
from .images import image_delete_list_view, image_upload_view, image_delete_view
from .items import (
    view_database, view_all_items, view_category_items, view_subcategory_items,
    view_item_detail, item_soft_delete_view, item_restore_view, view_deleted_items,
    ItemUpdateView, ItemCreateView
)
from .search import SearchCheckInView, SearchCheckOutView
from .subcategories import (
    subcategory_delete_list_view, subcategory_delete_view, SubcategoryCreateView
)
from .users import (
    manage_users_view, edit_user_role_api, view_user_profile_view,
    delete_user_view, restore_user_view, UserCreateView, is_admin
)

# Legacy imports for backward compatibility
# These maintain the original function names while using the new organized structure
index = index_view
dashboard = dashboard_view
audit_view = audit_log_list_view
delete_category_list_view = category_delete_list_view
delete_category = category_delete_view
delete_image_list_view = image_delete_list_view
delete_subcategory_list_view = subcategory_delete_list_view
delete_subcategory = subcategory_delete_view
view_item = view_item_detail
delete_item = item_soft_delete_view
restore_item = item_restore_view
upload_photo = image_upload_view
delete_image = image_delete_view
edit_user_role = edit_user_role_api
view_user = view_user_profile_view
delete_user = delete_user_view
restore_user = restore_user_view