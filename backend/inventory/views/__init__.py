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
from .audit import *
from .auth import *
from .categories import *
from .dashboard import *
from .images import *
from .items import *
from .search import *
from .subcategories import *
from .users import *
from .utils import *