"""
Legacy views module for backward compatibility.

This module has been reorganized into a views package with logical modules.
All imports are maintained for backward compatibility, but new development
should use the organized structure in the views package.

For more information, see the views package documentation.
"""

# Import all views from the organized views package
from .views import *

# Explicit backward compatibility imports to ensure existing URLs continue to work
from .views import (
    # Dashboard and navigation
    index, dashboard, profile_view,
    
    # Audit functionality  
    audit_view,
    
    # Category management
    delete_category_list_view, delete_category,
    CategoryUpdateView, CategoryCreateView,
    
    # Subcategory management
    delete_subcategory_list_view, delete_subcategory,
    SubcategoryCreateView,
    
    # Item management
    view_database, view_all_items, view_category_items, 
    view_subcategory_items, view_item, delete_item, restore_item,
    ItemUpdateView, ItemCreateView, view_deleted_items,
    
    # Image management
    delete_image_list_view, upload_photo, delete_image,
    
    # Search and quantity management
    SearchCheckInView, SearchCheckOutView,
    
    # User management
    manage_users_view, edit_user_role_api, view_user_profile_view,
    delete_user_view, restore_user_view, UserCreateView, is_admin,
    
    # Authentication
    logout_view, AccountNotRecognizedView, GoogleLoginView
)