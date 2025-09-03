# Development Guide

## Stock Items with Expiration Tracking

This application now supports detailed stock tracking with expiration dates and source organizations.

### New Models

#### Organization
Represents suppliers or sources of inventory items.
- `name`: Organization name (required, unique)
- `description`: Optional description
- `contact_email`: Contact email address
- `contact_phone`: Contact phone number  
- `address`: Physical address

#### StockItem
Individual stock batches with expiration tracking.
- `item`: Related Item (ForeignKey)
- `organization`: Source organization (ForeignKey)
- `quantity`: Number of units in this stock batch
- `date_received`: When the stock was received
- `expiration_date`: Expiration date (optional for non-perishable items)
- `lot_number`: Batch/lot identifier
- `notes`: Additional notes
- Stock availability is now determined by `quantity`: when `quantity == 0`, the stock is considered inactive.

### Key Features

- **Expiration Tracking**: Each stock item can have an expiration date
- **Source Tracking**: Know which organization provided each stock batch
- **Batch Management**: Track individual lots with lot numbers
- **Quantity Calculation**: Items automatically calculate total stock from active stock items
- **Admin Interface**: Full management through Django admin

### Database Migration

After pulling these changes, run:

```bash
python manage.py migrate inventory 0002_add_organization_stockitem
```

### Permissions

The setup_groups management command has been updated to include:
- Members can view, add, and change stock items
- Admins have full control over organizations and stock items

### Usage

1. Create organizations in the admin interface
2. Add stock items to existing items, specifying:
   - Source organization
   - Quantity received
   - Date received
   - Expiration date (if applicable)
   - Lot number for tracking

The Item model now shows both the original `quantity_active` field and a new `total_stock_quantity` property that sums active stock items.
