# Template Organization

This document explains the reorganized template structure for the MAI inventory system. The templates have been organized to match the views module structure for better maintainability and navigation.

## New Template Structure

```
templates/
├── shared/           # Shared/common templates used across the application
│   ├── base.html     # Base template - defines overall page structure
│   ├── navbar.html   # Navigation bar component
│   └── footer.html   # Footer component
├── dashboard/        # Dashboard and main navigation templates
│   └── index.html    # Main dashboard interface
├── auth/             # Authentication and authorization templates
│   └── not_found.html # 404 page for unauthorized access
├── audit/            # Audit logging and history templates
│   └── list.html     # Audit events listing page
├── categories/       # Category management templates
│   ├── create.html   # Create new category form
│   ├── edit.html     # Edit category form
│   ├── delete.html   # Delete categories interface
│   └── detail.html   # View category items and details
├── subcategories/    # Subcategory management templates
│   ├── create.html   # Create new subcategory form
│   ├── delete.html   # Delete subcategories interface
│   └── detail.html   # View subcategory items and details
├── items/            # Item management templates
│   ├── list.html     # Main database view (categories listing)
│   ├── create.html   # Create new item form
│   ├── edit.html     # Edit item form
│   └── detail.html   # View individual item details
├── images/           # Image management templates
│   └── delete.html   # Delete images interface
├── search/           # Search and quantity management templates
│   └── update_quantity.html # Check in/out quantity interface
└── users/            # User management templates
    ├── list.html     # List all users interface
    ├── detail.html   # View individual user profile
    └── create.html   # Create new user form
```

## Template Naming Convention

Templates follow a consistent naming convention based on their functionality:

- **list.html** - Templates that display lists of items (e.g., all users, all categories)
- **detail.html** - Templates that show detailed information about a single item
- **create.html** - Templates for creating new items (forms)
- **edit.html** - Templates for editing existing items (forms)
- **delete.html** - Templates for deleting items
- **index.html** - Main entry point templates for a module

## Migration from Old Structure

### Old → New Template Paths

| Old Path | New Path | Purpose |
|----------|----------|---------|
| `base.html` | `shared/base.html` | Base template |
| `navbar.html` | `shared/navbar.html` | Navigation bar |
| `footer.html` | `shared/footer.html` | Footer component |
| `dashboard.html` | `dashboard/index.html` | Main dashboard |
| `registration/not_found.html` | `auth/not_found.html` | 404 page |
| `audit.html` | `audit/list.html` | Audit events |
| `register/category.html` | `categories/create.html` | Create category |
| `edit/category.html` | `categories/edit.html` | Edit category |
| `delete/category.html` | `categories/delete.html` | Delete categories |
| `view/category.html` | `categories/detail.html` | View category |
| `register/subcategory.html` | `subcategories/create.html` | Create subcategory |
| `delete/subcategory.html` | `subcategories/delete.html` | Delete subcategories |
| `view/subcategory.html` | `subcategories/detail.html` | View subcategory |
| `view.html` | `items/list.html` | Main database view |
| `register/item.html` | `items/create.html` | Create item |
| `edit/item.html` | `items/edit.html` | Edit item |
| `view/item.html` | `items/detail.html` | View item |
| `delete/image.html` | `images/delete.html` | Delete images |
| `search/updateqty.html` | `search/update_quantity.html` | Update quantity |
| `register/user.html` | `users/create.html` | Create user |
| `view/user.html` | `users/detail.html` | View user |
| `view/users.html` | `users/list.html` | List users |

## Template Inheritance

All templates extend from `shared/base.html`:
```django
{% extends "shared/base.html" %}
```

The base template includes:
- `shared/navbar.html` - Navigation bar
- `shared/footer.html` - Footer component

## Benefits of New Organization

1. **Modular Structure** - Templates are grouped by functionality, matching the views structure
2. **Better Navigation** - Easier to find templates related to specific features
3. **Consistent Naming** - Descriptive names make template purposes clear
4. **Maintainability** - Changes to one feature are contained within its module
5. **Scalability** - Easy to add new template types or modules
6. **Code Discoverability** - Templates are co-located with their corresponding view logic

## Views Module Integration

The template organization perfectly mirrors the views package structure:

```
views/                  templates/
├── audit.py           ├── audit/
├── auth.py            ├── auth/
├── categories.py      ├── categories/
├── dashboard.py       ├── dashboard/
├── images.py          ├── images/
├── items.py           ├── items/
├── search.py          ├── search/
├── subcategories.py   ├── subcategories/
├── users.py           ├── users/
└── utils.py           └── shared/
```

This parallel structure makes it intuitive to locate templates when working on specific views and vice versa.