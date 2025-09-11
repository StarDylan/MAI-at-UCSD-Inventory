"""
Spreadsheet import views for bulk adding new inventory items.

This module handles Excel import functionality for bulk item creation,
including template generation and import processing.
"""

import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime, date
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db import transaction
from decimal import Decimal, InvalidOperation

from inventory.models import Item, StockItem, Organization, Category, Subcategory
from .utils import audit_log_state, audit_log_event


@login_required
@permission_required('inventory.add_viaspreadsheet_item', raise_exception=True)
def download_import_template(request):
    """
    Generate and download an Excel template for importing new items.
    
    Returns:
        HttpResponse: Excel file download with template headers and sample data
    """
    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Item Import Template"
    
    # Headers for import
    headers = [
        'Item Name', 'Manufacturer', 'GTIN', 'Category', 'Subcategory', 
        'Items Per Box', 'Cost Per Item', 'URL', 'Public Notes', 'Private Notes',
        'Organization', 'Quantity', 'Location', 'Detail', 'Date Received', 
        'Expiration Date', 'Lot Number', 'Stock Notes'
    ]
    
    # Add headers with styling
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
    
    # Add sample data row for guidance
    sample_data = [
        'Medical Gloves', 'Nitrile Brand', '1234567890123', 'Medical Supplies', 'PPE',
        '100', '0.15', 'https://example.com', 'Disposable nitrile gloves', 'Store in cool dry place',
        'UCSD Health', '1000', 'Storage Room A', 'Size Large', str(date.today()), 
        '', 'LOT2024001', 'Received in good condition'
    ]
    
    for col, data in enumerate(sample_data, 1):
        cell = ws.cell(row=2, column=col, value=data)
        cell.font = Font(italic=True, color='808080')
    
    # Set column widths for better readability
    column_widths = [15, 15, 15, 15, 15, 12, 12, 20, 20, 20, 15, 10, 15, 15, 12, 12, 12, 20]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width
    
    # Add instructions sheet
    instructions_ws = wb.create_sheet("Instructions")
    instructions = [
        "Item Import Template Instructions",
        "",
        "Required Fields:",
        "- Item Name: Unique name for the item",
        "- Category: Must match existing category name",
        "- Subcategory: Must match existing subcategory name",
        "- Organization: Must match existing organization name", 
        "- Quantity: Number of items (must be positive integer)",
        "- Location: Storage location for the stock",
        "- Date Received: Date in YYYY-MM-DD format",
        "",
        "Optional Fields:",
        "- Manufacturer: Brand or manufacturer name",
        "- GTIN: Global Trade Item Number (barcode)",
        "- Items Per Box: Number of items per package",
        "- Cost Per Item: Cost in dollars (e.g., 1.50)",
        "- URL: Product website or documentation link",
        "- Public Notes: Notes visible to all users",
        "- Private Notes: Notes visible only to MAI members",
        "- Detail: Variant details (size, color, etc.)",
        "- Expiration Date: For perishable items (YYYY-MM-DD)",
        "- Lot Number: Batch identifier",
        "- Stock Notes: Notes specific to this stock entry",
        "",
        "Important Notes:",
        "- If an item name already exists, new stock will be added to the existing item",
        "- When reusing existing items, only stock details (quantity, location, etc.) are used",
        "- GTIN placement: If Detail field is empty, GTIN goes on the Item; if Detail has content, GTIN goes on the Stock Item",
        "- GTINs must be unique within their respective location (Item or Stock Item)",
        "- Categories and subcategories must already exist in the system",
        "- Organizations must already exist in the system",
        "- Dates should be in YYYY-MM-DD format",
        "- Delete the sample row before importing",
        "",
        "Available Categories and Subcategories:",
    ]
    
    # Add category/subcategory information
    categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
    for category in categories:
        instructions.append(f"  {category.name}:")
        for subcategory in category.subcategories.all().order_by('name'):
            instructions.append(f"    - {subcategory.name}")
    
    instructions.append("")
    instructions.append("Available Organizations:")
    organizations = Organization.objects.all().order_by('name')
    for org in organizations:
        instructions.append(f"  - {org.name}")
    
    # Add instructions to sheet
    for row, instruction in enumerate(instructions, 1):
        cell = instructions_ws.cell(row=row, column=1, value=instruction)
        if row == 1:  # Title
            cell.font = Font(bold=True, size=14)
        elif instruction.endswith(":") and not instruction.startswith(" "):  # Headers
            cell.font = Font(bold=True)
    
    # Set column width for instructions
    instructions_ws.column_dimensions['A'].width = 80
    
    # Prepare response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'item_import_template_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Save workbook to response
    wb.save(response)
    return response


@login_required
@permission_required('inventory.add_viaspreadsheet_item', raise_exception=True)
def upload_spreadsheet(request):
    """
    Handle Excel file upload to create new items and stock items.
    
    Returns:
        HttpResponse: Rendered template or redirect
    """
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'No file was uploaded.')
            # Prepare context for the template
            categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
            organizations = Organization.objects.all().order_by('name')
            
            context = {
                'categories': categories,
                'organizations': organizations,
            }
            return render(request, 'spreadsheet_import/upload.html', context)
        
        excel_file = request.FILES['excel_file']
        
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Please upload a valid Excel file (.xlsx or .xls).')
            # Prepare context for the template
            categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
            organizations = Organization.objects.all().order_by('name')
            
            context = {
                'categories': categories,
                'organizations': organizations,
            }
            return render(request, 'spreadsheet_import/upload.html', context)
        
        try:
            # Load workbook
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active
            
            # Validate headers
            expected_headers = [
                'Item Name', 'Manufacturer', 'GTIN', 'Category', 'Subcategory', 
                'Items Per Box', 'Cost Per Item', 'URL', 'Public Notes', 'Private Notes',
                'Organization', 'Quantity', 'Location', 'Detail', 'Date Received', 
                'Expiration Date', 'Lot Number', 'Stock Notes'
            ]
            
            if ws.max_row < 1:
                messages.error(request, 'The uploaded file appears to be empty.')
                # Prepare context for the template
                categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
                organizations = Organization.objects.all().order_by('name')
                
                context = {
                    'categories': categories,
                    'organizations': organizations,
                }
                return render(request, 'spreadsheet_import/upload.html', context)
                
            actual_headers = [cell.value for cell in ws[1]]
            if actual_headers != expected_headers:
                messages.error(request, 'Invalid file format. Please use the template from the download function.')
                # Prepare context for the template
                categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
                organizations = Organization.objects.all().order_by('name')
                
                context = {
                    'categories': categories,
                    'organizations': organizations,
                }
                return render(request, 'spreadsheet_import/upload.html', context)
            
            # Process data rows
            created_count = 0
            error_count = 0
            errors = []
            
            # Prefetch all data to avoid N+1 queries in the loop
            organizations_dict = {org.name.lower(): org for org in Organization.objects.all()}
            categories_dict = {cat.name.lower(): cat for cat in Category.objects.all()}
            # For subcategories, create a nested dict: {category_name_lower: {subcat_name_lower: subcat_obj}}
            subcategories_dict = {}
            for subcat in Subcategory.objects.select_related('category').all():
                cat_name_lower = subcat.category.name.lower()
                if cat_name_lower not in subcategories_dict:
                    subcategories_dict[cat_name_lower] = {}
                subcategories_dict[cat_name_lower][subcat.name.lower()] = subcat
            
            # First pass: validate all data
            items_to_create = []
            # Track items being created in this import to handle duplicates within the same file
            items_in_current_import = {}  # name_lower -> item_data
            
            for row_num in range(2, ws.max_row + 1):
                try:
                    # Extract row data
                    item_name = str(ws.cell(row=row_num, column=1).value or '').strip()
                    manufacturer = str(ws.cell(row=row_num, column=2).value or '').strip()
                    gtin = str(ws.cell(row=row_num, column=3).value or '').strip()
                    category_name = str(ws.cell(row=row_num, column=4).value or '').strip()
                    subcategory_name = str(ws.cell(row=row_num, column=5).value or '').strip()
                    items_per_box = ws.cell(row=row_num, column=6).value
                    cost_per_item = ws.cell(row=row_num, column=7).value
                    url = str(ws.cell(row=row_num, column=8).value or '').strip()
                    public_notes = str(ws.cell(row=row_num, column=9).value or '').strip()
                    private_notes = str(ws.cell(row=row_num, column=10).value or '').strip()
                    organization_name = str(ws.cell(row=row_num, column=11).value or '').strip()
                    quantity = ws.cell(row=row_num, column=12).value
                    location = str(ws.cell(row=row_num, column=13).value or '').strip()
                    detail = str(ws.cell(row=row_num, column=14).value or '').strip()
                    date_received = ws.cell(row=row_num, column=15).value
                    expiration_date = ws.cell(row=row_num, column=16).value
                    lot_number = str(ws.cell(row=row_num, column=17).value or '').strip()
                    stock_notes = str(ws.cell(row=row_num, column=18).value or '').strip()
                    
                    # Skip empty rows
                    if not item_name:
                        continue
                    
                    # Validate required fields
                    if not category_name:
                        errors.append(f"Row {row_num}: Category is required")
                        error_count += 1
                        continue
                    
                    if not subcategory_name:
                        errors.append(f"Row {row_num}: Subcategory is required")
                        error_count += 1
                        continue
                        
                    if not organization_name:
                        errors.append(f"Row {row_num}: Organization is required")
                        error_count += 1
                        continue
                        
                    if not quantity:
                        errors.append(f"Row {row_num}: Quantity is required")
                        error_count += 1
                        continue
                        
                    if not location:
                        errors.append(f"Row {row_num}: Location is required")
                        error_count += 1
                        continue
                        
                    if not date_received:
                        errors.append(f"Row {row_num}: Date Received is required")
                        error_count += 1
                        continue
                    
                    item_name_lower = item_name.lower()
                    
                    # Check if item already exists in database
                    existing_item = Item.objects.filter(name__iexact=item_name).first()
                    
                    # Check if item is being created in this import
                    item_from_current_import = items_in_current_import.get(item_name_lower)
                    
                    # Determine which item to use (existing in DB, or from current import)
                    reference_item_data = None
                    if existing_item:
                        reference_item_data = {
                            'category_name': existing_item.category.name,
                            'subcategory_name': existing_item.subcategory.name if existing_item.subcategory else ''
                        }
                    elif item_from_current_import:
                        reference_item_data = {
                            'category_name': item_from_current_import['category_name'],
                            'subcategory_name': item_from_current_import['subcategory_name']
                        }
                    
                    # If we have a reference (existing or from current import), validate consistency
                    if reference_item_data:
                        # Check for category/subcategory consistency
                        if reference_item_data['category_name'].lower() != category_name.lower():
                            existing_source = "database" if existing_item else "earlier in this import"
                            errors.append(f"Row {row_num}: Item '{item_name}' exists in {existing_source} with category '{reference_item_data['category_name']}', but row specifies '{category_name}'")
                            error_count += 1
                            continue
                        if reference_item_data['subcategory_name'] and reference_item_data['subcategory_name'].lower() != subcategory_name.lower():
                            existing_source = "database" if existing_item else "earlier in this import"
                            errors.append(f"Row {row_num}: Item '{item_name}' exists in {existing_source} with subcategory '{reference_item_data['subcategory_name']}', but row specifies '{subcategory_name}'")
                            error_count += 1
                            continue
                    
                    # Validate GTIN uniqueness if provided
                    if gtin:
                        if len(gtin) > 14:
                            errors.append(f"Row {row_num}: GTIN must be at most 14 characters")
                            error_count += 1
                            continue
                        
                        # Determine where GTIN will be placed based on detail field
                        gtin_on_stock_item = bool(detail.strip())
                        
                        if gtin_on_stock_item:
                            # GTIN goes on StockItem - check for conflicts in StockItem table
                            if StockItem.objects.filter(gtin=gtin).exists():
                                errors.append(f"Row {row_num}: GTIN '{gtin}' already exists on a stock item")
                                error_count += 1
                                continue
                        else:
                            # GTIN goes on Item - check for conflicts in Item table (excluding existing item if reusing)
                            gtin_conflict = Item.objects.filter(gtin=gtin).exclude(id=existing_item.id if existing_item else None).exists()
                            if gtin_conflict:
                                errors.append(f"Row {row_num}: GTIN '{gtin}' already exists on an item")
                                error_count += 1
                                continue
                    
                    # Validate category using pre-fetched dictionary
                    category = categories_dict.get(category_name.lower())
                    if not category:
                        errors.append(f"Row {row_num}: Category '{category_name}' not found")
                        error_count += 1
                        continue
                    
                    # Validate subcategory using pre-fetched dictionary
                    category_subcats = subcategories_dict.get(category_name.lower(), {})
                    subcategory = category_subcats.get(subcategory_name.lower())
                    if not subcategory:
                        errors.append(f"Row {row_num}: Subcategory '{subcategory_name}' not found in category '{category_name}'")
                        error_count += 1
                        continue
                    
                    # Validate organization using pre-fetched dictionary
                    organization = organizations_dict.get(organization_name.lower())
                    if not organization:
                        errors.append(f"Row {row_num}: Organization '{organization_name}' not found")
                        error_count += 1
                        continue
                    
                    # Validate quantity
                    try:
                        quantity = int(quantity)
                        if quantity <= 0:
                            errors.append(f"Row {row_num}: Quantity must be positive")
                            error_count += 1
                            continue
                    except (ValueError, TypeError):
                        errors.append(f"Row {row_num}: Quantity must be a valid number")
                        error_count += 1
                        continue
                    
                    # Validate items_per_box if provided
                    if items_per_box:
                        try:
                            items_per_box = int(items_per_box)
                            if items_per_box <= 0:
                                items_per_box = None
                        except (ValueError, TypeError):
                            items_per_box = None
                    else:
                        items_per_box = None
                    
                    # Validate cost_per_item if provided
                    if cost_per_item:
                        try:
                            cost_per_item = Decimal(str(cost_per_item))
                            if cost_per_item < 0:
                                cost_per_item = None
                        except (InvalidOperation, ValueError, TypeError):
                            cost_per_item = None
                    else:
                        cost_per_item = None
                    
                    # Validate date_received
                    if isinstance(date_received, str):
                        try:
                            date_received = datetime.strptime(date_received, '%Y-%m-%d').date()
                        except ValueError:
                            errors.append(f"Row {row_num}: Date Received must be in YYYY-MM-DD format")
                            error_count += 1
                            continue
                    elif not isinstance(date_received, date):
                        try:
                            date_received = date_received.date() if hasattr(date_received, 'date') else date.today()
                        except:
                            errors.append(f"Row {row_num}: Invalid Date Received format")
                            error_count += 1
                            continue
                    
                    # Validate expiration_date if provided
                    if expiration_date:
                        if isinstance(expiration_date, str):
                            try:
                                expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
                            except ValueError:
                                errors.append(f"Row {row_num}: Expiration Date must be in YYYY-MM-DD format")
                                error_count += 1
                                continue
                        elif not isinstance(expiration_date, date):
                            try:
                                expiration_date = expiration_date.date() if hasattr(expiration_date, 'date') else None
                            except:
                                expiration_date = None
                    else:
                        expiration_date = None
                    
                    # Determine where GTIN should be placed based on detail field
                    gtin_on_stock_item = bool(detail.strip())
                    item_gtin = '' if gtin_on_stock_item else gtin
                    stock_gtin = gtin if gtin_on_stock_item else ''
                    
                    # Determine if we need to create a new item or reuse existing
                    will_create_new_item = not existing_item and not item_from_current_import
                    
                    # If creating new item, track it for subsequent rows
                    if will_create_new_item:
                        items_in_current_import[item_name_lower] = {
                            'category_name': category_name,
                            'subcategory_name': subcategory_name,
                            'item_data': {
                                'name': item_name,
                                'manufacturer': manufacturer,
                                'gtin': item_gtin,
                                'category': category,
                                'subcategory': subcategory,
                                'items_per_box': items_per_box,
                                'cost_per_item': cost_per_item,
                                'url': url,
                                'notes_public': public_notes,
                                'notes_private': private_notes,
                            }
                        }
                    
                    # Store validated data for creation
                    items_to_create.append({
                        'row_num': row_num,
                        'existing_item': existing_item,  # None if creating new item
                        'item_name_lower': item_name_lower,  # For tracking within import
                        'item_data': {
                            'name': item_name,
                            'manufacturer': manufacturer,
                            'gtin': item_gtin,
                            'category': category,
                            'subcategory': subcategory,
                            'items_per_box': items_per_box,
                            'cost_per_item': cost_per_item,
                            'url': url,
                            'notes_public': public_notes,
                            'notes_private': private_notes,
                        },
                        'stock_data': {
                            'organization': organization,
                            'quantity': quantity,
                            'location': location,
                            'detail': detail,
                            'date_received': date_received,
                            'expiration_date': expiration_date,
                            'lot_number': lot_number,
                            'notes': stock_notes,
                            'gtin': stock_gtin,
                        }
                    })
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: Error processing row - {str(e)}")
                    error_count += 1
            
            # If there are validation errors, don't proceed with creation
            if error_count > 0:
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)
                if len(errors) > 10:
                    messages.warning(request, f'... and {len(errors) - 10} more errors.')
                messages.error(request, f'Found {error_count} validation errors. No items were created.')
                return redirect('spreadsheet_import_upload')
            
            # Create all items within a transaction
            created_item_count = 0
            added_stock_count = 0
            # Track items created in this transaction
            created_items_map = {}  # name_lower -> Item instance
            
            try:
                with transaction.atomic():
                    for item_data in items_to_create:
                        item_name_lower = item_data['item_name_lower']
                        
                        # Determine which item to use
                        if item_data['existing_item']:
                            # Use existing item from database
                            item = item_data['existing_item']
                        elif item_name_lower in created_items_map:
                            # Use item created earlier in this transaction
                            item = created_items_map[item_name_lower]
                        else:
                            # Create new Item
                            item = Item(**item_data['item_data'])
                            item.save()
                            created_item_count += 1
                            created_items_map[item_name_lower] = item
                            
                            # Log item creation
                            audit_log_event(
                                request.user,
                                f"Created item \"{item.name}\" via spreadsheet import",
                                audit_log_state(None),
                                audit_log_state(item)
                            )
                        
                        # Create StockItem (always create new stock)
                        stock_item = StockItem(
                            item=item,
                            **item_data['stock_data']
                        )
                        stock_item.save()
                        added_stock_count += 1
                        
                        # Log stock item creation
                        action_desc = "Added initial stock" if item_name_lower in created_items_map else "Added stock"
                        audit_log_event(
                            request.user,
                            f"{action_desc} for \"{item.name}\" via spreadsheet import - {stock_item.quantity} units to {stock_item.location}",
                            audit_log_state(None),
                            audit_log_state(stock_item)
                        )
                
                # Build success message
                if created_item_count > 0 and added_stock_count > created_item_count:
                    messages.success(request, f'Successfully created {created_item_count} new items and added stock to {added_stock_count - created_item_count} existing items from spreadsheet.')
                elif created_item_count > 0:
                    messages.success(request, f'Successfully created {created_item_count} new items from spreadsheet.')
                else:
                    messages.success(request, f'Successfully added stock to {added_stock_count} existing items from spreadsheet.')
                    
                return redirect('spreadsheet_import_upload')
                
            except Exception as e:
                messages.error(request, f'Error creating items: {str(e)}')
                return redirect('spreadsheet_import_upload')
        
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            # Prepare context for the template
            categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
            organizations = Organization.objects.all().order_by('name')
            
            context = {
                'categories': categories,
                'organizations': organizations,
            }
            return render(request, 'spreadsheet_import/upload.html', context)
    
    # Prepare context for the template
    categories = Category.objects.prefetch_related('subcategories').all().order_by('name')
    organizations = Organization.objects.all().order_by('name')
    
    context = {
        'categories': categories,
        'organizations': organizations,
    }
    
    return render(request, 'spreadsheet_import/upload.html', context)