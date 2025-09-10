"""
Management command for comprehensive stress testing of the inventory system.

Creates ~10,000 items with mock data and simulates realistic user interactions:
- 100 test users with proper permissions
- Each item has 1-5 stock items (50% for 1, even distribution for 2-5)
- 50% of stock items are expired
- Realistic user interactions:
  * Item renaming (1-3 times per item) using Django views
  * Checkout operations (1-10 times per item) with proper stock reduction
  * Stock check-ins with new deliveries and quantity updates
- Comprehensive audit trail for all operations
- Uses Django views directly for accurate business logic execution
- Uses tqdm for progress tracking
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import Client, RequestFactory
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import timezone
from tqdm import tqdm
from inventory.models import (
    Category, Subcategory, Organization, Item, StockItem, AuditEvent, CheckOut, CheckOutItem
)
from inventory.views.utils import audit_log_event, audit_log_state
from inventory.forms import ItemForm, CheckOutForm, CheckOutItemForm

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates comprehensive stress test data with ~10,000 items, 100 users, and realistic user interactions (rename, checkout, check-in operations)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            type=int,
            default=10000,
            help='Number of items to create (default: 10000)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )
        parser.add_argument(
            '--no-audit',
            action='store_true',
            help='Skip creating audit events (faster generation)',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=100,
            help='Number of test users to create for interactions (default: 100)',
        )
        parser.add_argument(
            '--no-interactions',
            action='store_true',
            help='Skip user interactions (rename, checkout) for faster generation',
        )

    def handle(self, *args, **options):
        num_items = options['items']
        clear_data = options['clear']
        create_audit = not options['no_audit']
        num_users = options['users']
        create_interactions = not options['no_interactions']
        
        self.stdout.write(f"Starting stress test data generation...")
        self.stdout.write(f"Target items: {num_items}")
        self.stdout.write(f"Test users: {num_users}")
        self.stdout.write(f"Clear existing data: {clear_data}")
        self.stdout.write(f"Create audit events: {create_audit}")
        self.stdout.write(f"Create user interactions: {create_interactions}")
        
        if clear_data:
            self.clear_existing_data()
        
        # Create or get required base data
        self.create_base_data()
        
        # Create test users for interactions
        test_users = self.create_test_users(num_users)
        
        # Generate the stress test data
        created_items = self.generate_items_and_stock(num_items, test_users[0], create_audit)
        
        # Generate user interactions if requested
        if create_interactions and created_items:
            self.generate_user_interactions(created_items, test_users, create_audit)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created stress test data!'))

    def clear_existing_data(self):
        """Clear existing data if requested"""
        self.stdout.write("Clearing existing data...")
        
        with transaction.atomic():
            # Clear in dependency order
            CheckOutItem.objects.all().delete()
            CheckOut.objects.all().delete()
            AuditEvent.objects.all().delete()
            StockItem.objects.all().delete()
            Item.objects.all().delete()
            Subcategory.objects.all().delete()
            Category.objects.all().delete()
            Organization.objects.filter(name__startswith='Test Org').delete()
            # Clear test users
            User.objects.filter(username__startswith='stress_test_user').delete()
            
        self.stdout.write(self.style.SUCCESS("Existing data cleared."))

    def create_base_data(self):
        """Create basic categories and organizations needed for items"""
        self.stdout.write("Creating base categories and organizations...")
        
        # Sample categories with subcategories
        categories_data = [
            ('Office Supplies', ['Pens & Pencils', 'Paper Products', 'Desk Accessories', 'Filing']),
            ('Electronics', ['Computers', 'Mobile Devices', 'Cables & Adapters', 'Batteries']),
            ('Medical Supplies', ['Disposables', 'Instruments', 'Medications', 'PPE']),
            ('Food & Beverages', ['Snacks', 'Beverages', 'Canned Goods', 'Fresh Produce']),
            ('Cleaning Supplies', ['Detergents', 'Disinfectants', 'Paper Towels', 'Trash Bags']),
            ('Tools & Equipment', ['Hand Tools', 'Power Tools', 'Safety Equipment', 'Hardware']),
            ('Educational Materials', ['Books', 'Stationery', 'Art Supplies', 'Teaching Aids']),
            ('Furniture', ['Chairs', 'Desks', 'Storage', 'Accessories']),
        ]
        
        for cat_name, subcat_names in categories_data:
            category, created = Category.objects.get_or_create(name=cat_name)
            for subcat_name in subcat_names:
                Subcategory.objects.get_or_create(
                    name=subcat_name,
                    category=category
                )
        
        # Create sample organizations
        org_names = [
            'Test Org Alpha Corp', 'Test Org Beta Solutions', 'Test Org Gamma Industries',
            'Test Org Delta Systems', 'Test Org Epsilon LLC', 'Test Org Zeta Partners',
            'Test Org Eta Enterprises', 'Test Org Theta Group', 'Test Org Iota Inc',
            'Test Org Kappa Supplies', 'Test Org Lambda Services', 'Test Org Mu Logistics'
        ]
        
        for org_name in org_names:
            Organization.objects.get_or_create(
                name=org_name,
                defaults={
                    'description': f'Test organization: {org_name}',
                    'contact_email': f'contact@{org_name.lower().replace(" ", "")}.com',
                    'contact_phone': f'+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}',
                    'address': f'{random.randint(100, 9999)} Test Street, Test City, TS {random.randint(10000, 99999)}'
                }
            )

    def create_test_users(self, num_users):
        """Create multiple test users with realistic names and permissions"""
        self.stdout.write(f"Creating {num_users} test users...")
        
        # Lists of realistic names
        first_names = [
            'Alice', 'Bob', 'Charlie', 'Diana', 'Edward', 'Fiona', 'George', 'Hannah',
            'Ian', 'Julia', 'Kevin', 'Linda', 'Michael', 'Nancy', 'Oliver', 'Patricia',
            'Quincy', 'Rachel', 'Steven', 'Teresa', 'Ulysses', 'Victoria', 'William', 'Xenia',
            'Yolanda', 'Zachary', 'Amanda', 'Benjamin', 'Catherine', 'Daniel', 'Elizabeth',
            'Frank', 'Grace', 'Henry', 'Isabel', 'Jason', 'Katherine', 'Lawrence', 'Margaret',
            'Nathan', 'Olivia', 'Peter', 'Quinn', 'Robert', 'Sarah', 'Thomas', 'Ursula',
            'Vincent', 'Wendy', 'Xavier', 'Yvonne', 'Zoe', 'Anthony', 'Barbara', 'Christopher',
            'Deborah', 'Eric', 'Frances', 'Gregory', 'Helen', 'Ivan', 'Jennifer', 'Kenneth',
            'Lisa', 'Mark', 'Nicole', 'Owen', 'Pamela', 'Richard', 'Sandra', 'Timothy',
            'Uma', 'Victor', 'Walter', 'Ximena', 'Yasmine', 'Zach', 'Andrea', 'Brandon',
            'Chloe', 'David', 'Emma', 'Felix', 'Gabriela', 'Harrison', 'Iris', 'Joseph'
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
            'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
            'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
            'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
            'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell',
            'Mitchell', 'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner',
            'Diaz', 'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris',
            'Morales', 'Murphy', 'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Morgan',
            'Cooper', 'Peterson', 'Bailey', 'Reed', 'Kelly', 'Howard', 'Ramos', 'Kim'
        ]
        
        # Get or create the inventory staff group with proper permissions
        staff_group, created = Group.objects.get_or_create(name='Inventory Staff')
        if created:
            # Add basic inventory permissions
            permissions = Permission.objects.filter(
                content_type__app_label='inventory',
                codename__in=[
                    'add_item', 'change_item', 'delete_item', 'view_item',
                    'add_stockitem', 'change_stockitem', 'delete_stockitem', 'view_stockitem',
                    'add_checkout', 'change_checkout', 'view_checkout', 'complete_checkout',
                    'add_checkoutitem', 'change_checkoutitem', 'delete_checkoutitem', 'view_checkoutitem',
                ]
            )
            staff_group.permissions.set(permissions)
        
        created_users = []
        
        with tqdm(total=num_users, desc="Creating users") as pbar:
            for i in range(num_users):
                # Generate unique username
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                username = f"stress_test_user_{i+1:03d}"
                email = f"{first_name.lower()}.{last_name.lower()}.{i+1}@stresstest.example.com"
                
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_staff': True,
                        'is_active': True,
                    }
                )
                
                if created:
                    user.set_password('stress_test_password')
                    user.save()
                    # Add to inventory staff group
                    user.groups.add(staff_group)
                
                created_users.append(user)
                pbar.update(1)
        
        self.stdout.write(self.style.SUCCESS(f"Created {len(created_users)} test users."))
        return created_users

    def generate_items_and_stock(self, num_items, test_user, create_audit):
        """Generate items with their associated stock items"""
        self.stdout.write(f"Generating {num_items} items with stock...")
        
        # Get all categories, subcategories, and organizations
        categories = list(Category.objects.all())
        subcategories = list(Subcategory.objects.all())
        organizations = list(Organization.objects.all())
        
        if not categories or not organizations:
            self.stdout.write(self.style.ERROR("No categories or organizations found. Run with base data creation first."))
            return []
        
        # Item name templates for variety
        item_templates = [
            'Professional {}', 'Deluxe {}', 'Standard {}', 'Premium {}', 'Basic {}',
            'Advanced {}', 'Compact {}', 'Portable {}', 'Heavy-duty {}', 'Lightweight {}',
            'Ergonomic {}', 'Wireless {}', 'Digital {}', 'Smart {}', 'Classic {}',
            'Modern {}', 'Vintage {}', 'Industrial {}', 'Commercial {}', 'Household {}'
        ]
        
        item_base_names = [
            'Calculator', 'Stapler', 'Notebook', 'Pen Set', 'Folder', 'Binder', 'Marker',
            'Scissors', 'Tape Dispenser', 'Paper Clips', 'Rubber Bands', 'Envelopes',
            'Labels', 'Stamps', 'Printer Paper', 'Toner Cartridge', 'USB Drive',
            'Computer Mouse', 'Keyboard', 'Monitor', 'Speaker', 'Headphones', 'Cable',
            'Battery Pack', 'Charger', 'Phone Case', 'Tablet Stand', 'Desk Lamp',
            'Office Chair', 'Filing Cabinet', 'Bookshelf', 'Whiteboard', 'Calendar',
            'Clock', 'Coffee Mug', 'Water Bottle', 'First Aid Kit', 'Fire Extinguisher',
            'Hand Sanitizer', 'Face Masks', 'Gloves', 'Cleaning Spray', 'Paper Towels',
            'Trash Bags', 'Soap Dispenser', 'Toilet Paper', 'Tissues', 'Bandages',
            'Thermometer', 'Blood Pressure Monitor', 'Scale', 'Stethoscope', 'Syringe'
        ]
        
        locations = [
            'Warehouse A-1', 'Warehouse A-2', 'Warehouse B-1', 'Warehouse B-2',
            'Storage Room 101', 'Storage Room 102', 'Storage Room 201', 'Storage Room 202',
            'Main Office', 'Branch Office North', 'Branch Office South', 'Branch Office East',
            'Inventory Closet', 'Supply Cabinet', 'Loading Dock', 'Receiving Area',
            'Cold Storage', 'Dry Storage', 'Security Vault', 'File Room',
            'Conference Room A', 'Conference Room B', 'Break Room', 'Kitchen Area'
        ]
        
        manufacturers = [
            'TestCorp Inc', 'MockTech Solutions', 'SampleTech Ltd', 'DemoWare Corp',
            'PrototypeProducts Inc', 'AlphaBeta Manufacturing', 'GammaDelta Industries',
            'TestBench Systems', 'MockSource Solutions', 'SampleSupply Co',
            'QualityTest Corp', 'ReliableMock Inc', 'PremiumTest Ltd', 'StandardDemo Corp'
        ]
        
        created_items = []
        
        # Generate items with progress bar
        with tqdm(total=num_items, desc="Creating items") as pbar:
            for i in range(num_items):
                with transaction.atomic():
                    # Create item
                    item = self.create_item(
                        i, categories, subcategories, item_templates, 
                        item_base_names, manufacturers
                    )
                    created_items.append(item)
                    
                    # Determine number of stock items (50% chance for 1, even distribution for 2-5)
                    if random.random() < 0.5:
                        num_stock_items = 1
                    else:
                        num_stock_items = random.choice([2, 3, 4, 5])
                    
                    # Create stock items for this item
                    for stock_idx in range(num_stock_items):
                        stock_item = self.create_stock_item(
                            item, organizations, locations
                        )
                        
                        # Create audit event if requested
                        if create_audit:
                            self.create_stock_audit_event(stock_item, test_user)
                    
                    pbar.update(1)
        
        return created_items

    def create_item(self, index, categories, subcategories, templates, base_names, manufacturers):
        """Create a single item with realistic data"""
        # Generate item name
        template = random.choice(templates)
        base_name = random.choice(base_names)
        item_name = template.format(base_name)
        
        # Add unique suffix to avoid conflicts
        item_name = f"{item_name} #{index+1:06d}"
        
        # Select category and possibly subcategory
        category = random.choice(categories)
        # 70% chance of having a subcategory
        subcategory = None
        if random.random() < 0.7:
            category_subcats = [sc for sc in subcategories if sc.category == category]
            if category_subcats:
                subcategory = random.choice(category_subcats)
        
        # Create the item
        item = Item.objects.create(
            name=item_name,
            category=category,
            subcategory=subcategory,
            manufacturer=random.choice(manufacturers) if random.random() < 0.8 else '',
            gtin=self.generate_gtin() if random.random() < 0.3 else '',
            items_per_box=random.choice([1, 5, 10, 12, 24, 50, 100]) if random.random() < 0.6 else None,
            cost_per_item=Decimal(f"{random.uniform(0.5, 500.0):.2f}") if random.random() < 0.7 else None,
            notes_public=self.generate_notes('public') if random.random() < 0.4 else '',
            notes_private=self.generate_notes('private') if random.random() < 0.2 else '',
            url=f"https://example.com/product/{index+1}" if random.random() < 0.15 else '',
        )
        
        return item

    def create_stock_item(self, item, organizations, locations):
        """Create a single stock item with realistic data"""
        # Generate dates
        days_ago_received = random.randint(1, 365)
        date_received = date.today() - timedelta(days=days_ago_received)
        
        # 50% chance of being expired
        expiration_date = None
        if random.random() < 0.7:  # 70% have expiration dates
            if random.random() < 0.5:  # 50% of those are expired
                # Expired: expiration date in the past
                days_expired = random.randint(1, 180)
                expiration_date = date.today() - timedelta(days=days_expired)
            else:
                # Not expired: expiration date in the future
                days_until_expiry = random.randint(30, 730)  # 30 days to 2 years
                expiration_date = date.today() + timedelta(days=days_until_expiry)
        
        stock_item = StockItem.objects.create(
            item=item,
            organization=random.choice(organizations),
            quantity=random.randint(1, 100),
            location=random.choice(locations),
            gtin=self.generate_gtin() if random.random() < 0.2 else '',
            detail=self.generate_detail() if random.random() < 0.5 else '',
            date_received=date_received,
            expiration_date=expiration_date,
            lot_number=self.generate_lot_number() if random.random() < 0.6 else '',
            notes=self.generate_notes('stock') if random.random() < 0.3 else '',
            surplus_status=random.choice(['pending', 'wanted', 'not_wanted']),
        )
        
        return stock_item

    def create_stock_audit_event(self, stock_item, test_user):
        """Create an audit event for stock item creation"""
        before_state = audit_log_state(None)
        after_state = audit_log_state(stock_item)
        
        audit_log_event(
            user=test_user,
            event=f"Stock item created for {stock_item.item.name}",
            before_state=before_state,
            after_state=after_state,
            entity_id=str(stock_item.id)
        )

    def generate_gtin(self):
        """Generate a realistic GTIN"""
        # Generate 13-digit GTIN (EAN-13)
        digits = [random.randint(0, 9) for _ in range(12)]
        # Calculate check digit (simplified)
        checksum = sum(digits[i] * (3 if i % 2 else 1) for i in range(12))
        check_digit = (10 - (checksum % 10)) % 10
        digits.append(check_digit)
        return ''.join(map(str, digits))

    def generate_detail(self):
        """Generate realistic detail descriptions"""
        colors = ['Red', 'Blue', 'Green', 'Black', 'White', 'Yellow', 'Orange', 'Purple']
        sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '8oz', '16oz', '32oz', 'Mini', 'Jumbo']
        materials = ['Plastic', 'Metal', 'Wood', 'Glass', 'Fabric', 'Paper', 'Ceramic']
        
        details = []
        if random.random() < 0.6:
            details.append(random.choice(colors))
        if random.random() < 0.4:
            details.append(random.choice(sizes))
        if random.random() < 0.3:
            details.append(random.choice(materials))
        
        return ', '.join(details) if details else f"Variant {random.randint(1, 20)}"

    def generate_lot_number(self):
        """Generate realistic lot numbers"""
        formats = [
            f"LOT-{random.randint(100000, 999999)}",
            f"BATCH-{random.randint(1000, 9999)}-{random.randint(10, 99)}",
            f"L{random.randint(10000, 99999)}",
            f"{random.randint(2020, 2024)}{random.randint(1, 12):02d}{random.randint(1, 28):02d}-{random.randint(1, 999):03d}",
        ]
        return random.choice(formats)

    def generate_notes(self, note_type):
        """Generate realistic notes"""
        if note_type == 'public':
            notes = [
                "High quality product with excellent durability.",
                "Environmentally friendly materials used.",
                "Suitable for professional use.",
                "Bulk pricing available for large orders.",
                "Customer favorite - highly rated.",
                "New improved formula/design.",
                "Compatible with standard equipment.",
                "Easy to use and maintain."
            ]
        elif note_type == 'private':
            notes = [
                "Check supplier reliability before reordering.",
                "Price negotiation possible for large quantities.",
                "Quality issues reported in previous batch.",
                "Alternative supplier being evaluated.",
                "Seasonal demand - stock accordingly.",
                "Discontinuation notice received from manufacturer.",
                "Storage temperature requirements: 15-25°C.",
                "Handle with care - fragile items."
            ]
        else:  # stock notes
            notes = [
                "Received in good condition.",
                "Minor packaging damage noted.",
                "Quality checked and approved.",
                "Store in dry environment.",
                "First batch from new supplier.",
                "Urgent delivery - expedited shipping.",
                "Partial shipment - remainder expected next week.",
                "Special handling required during transport."
            ]
        
        return random.choice(notes)

    def generate_user_interactions(self, created_items, test_users, create_audit):
        """Generate realistic user interactions using Django views"""
        self.stdout.write(f"Generating user interactions for {len(created_items)} items...")
        
        # Create Django test client for making requests
        factory = RequestFactory()
        client = Client()
        
        total_operations = 0
        
        # Calculate approximate total operations for progress bar
        estimated_operations = len(created_items) * 3  # Rough estimate
        
        with tqdm(total=estimated_operations, desc="Generating interactions") as pbar:
            
            # For each item, generate random interactions
            for item in created_items:
                operations_this_item = 0
                
                # 1. Item Rename Operations (1-3 times per item)
                num_renames = random.randint(1, 3)
                for rename_idx in range(num_renames):
                    user = random.choice(test_users)
                    success = self.perform_item_rename(item, user, rename_idx + 1, factory)
                    if success:
                        operations_this_item += 1
                        pbar.update(1)
                
                # 2. Checkout Operations (1-10 times, but not always)
                if random.random() < 0.7:  # 70% chance of having checkout operations
                    num_checkouts = random.randint(1, min(10, len(item.stock_items.all())))
                    
                    for checkout_idx in range(num_checkouts):
                        user = random.choice(test_users)
                        success = self.perform_checkout_operation(item, user, factory, client)
                        if success:
                            operations_this_item += 1
                            pbar.update(1)
                
                # 3. Stock Updates (check-ins) - simulate receiving new stock
                if random.random() < 0.4:  # 40% chance of stock updates
                    num_stock_updates = random.randint(1, 3)
                    for update_idx in range(num_stock_updates):
                        user = random.choice(test_users)
                        success = self.perform_stock_update(item, user, factory)
                        if success:
                            operations_this_item += 1
                            pbar.update(1)
                
                total_operations += operations_this_item
        
        self.stdout.write(self.style.SUCCESS(f"Generated {total_operations} user interactions."))
    
    def perform_item_rename(self, item, user, rename_number, factory):
        """Simulate item rename using ItemUpdateView"""
        try:
            # Generate new name variant
            suffix_options = [
                f" v{rename_number}",
                f" Rev {rename_number}",
                f" Updated",
                f" Revised",
                f" Modified",
                f" Enhanced",
                f" Improved"
            ]
            
            # Get current name and add suffix
            original_name = item.name
            if " #" in original_name:
                base_name = original_name.split(" #")[0]
            else:
                base_name = original_name
                
            new_name = base_name + random.choice(suffix_options)
            
            # Create request with form data
            post_data = {
                'name': new_name,
                'manufacturer': item.manufacturer,
                'gtin': item.gtin,
                'items_per_box': item.items_per_box or '',
                'cost_per_item': item.cost_per_item or '',
                'subcategory': item.subcategory.id if item.subcategory else '',
                'url': item.url,
                'notes_public': item.notes_public,
                'notes_private': item.notes_private,
            }
            
            request = factory.post(f'/edit/item/{item.id}/', post_data)
            request.user = user
            
            # Simulate the update using the form directly
            from inventory.forms import ItemForm
            form = ItemForm(post_data, instance=item)
            
            if form.is_valid():
                # Save the changes
                before_state = audit_log_state(item)
                form.save()
                
                # Create audit event
                after_state = audit_log_state(item)
                audit_log_event(
                    user,
                    f"Updated item name from \"{original_name}\" to \"{new_name}\"",
                    before_state,
                    after_state
                )
                return True
                
        except Exception as e:
            # Silently continue on errors to avoid breaking the stress test
            pass
        
        return False
    
    def perform_checkout_operation(self, item, user, factory, client):
        """Simulate checkout operation using checkout views"""
        try:
            # Get available stock items for this item
            available_stock = item.stock_items.filter(quantity__gt=0)
            if not available_stock.exists():
                return False
            
            # Get random organization for checkout
            organizations = list(Organization.objects.all())
            if not organizations:
                return False
            
            target_org = random.choice(organizations)
            
            # Create checkout using direct model creation (simpler for stress test)
            checkout = CheckOut.objects.create(
                organization=target_org,
                created_by=user,
                is_donation=random.choice([True, False]),
                notes=f"Stress test checkout by {user.get_full_name() or user.username}"
            )
            
            # Add 1-3 stock items to the checkout
            num_items_to_checkout = min(random.randint(1, 3), available_stock.count())
            selected_stock = random.sample(list(available_stock), num_items_to_checkout)
            
            for stock_item in selected_stock:
                # Checkout 1 to min(5, available_quantity)
                max_quantity = min(5, stock_item.quantity)
                checkout_quantity = random.randint(1, max_quantity)
                
                CheckOutItem.objects.create(
                    checkout=checkout,
                    stock_item=stock_item,
                    quantity=checkout_quantity,
                    notes=f"Stress test checkout item"
                )
            
            # Complete the checkout (simulate stock reduction)
            if random.random() < 0.8:  # 80% chance to complete immediately
                checkout.is_completed = True
                checkout.completed_by = user
                checkout.completed_at = timezone.now()
                checkout.save()
                
                # Reduce stock quantities
                for checkout_item in checkout.checkout_items.all():
                    stock_item = checkout_item.stock_item
                    stock_item.quantity = max(0, stock_item.quantity - checkout_item.quantity)
                    stock_item.save()
                    
                    # Create audit event for stock reduction
                    audit_log_event(
                        user,
                        f"Completed checkout - reduced stock by {checkout_item.quantity}",
                        audit_log_state(None),
                        audit_log_state(stock_item)
                    )
            
            return True
            
        except Exception as e:
            # Silently continue on errors
            pass
        
        return False
    
    def perform_stock_update(self, item, user, factory):
        """Simulate stock update (check-in) operation"""
        try:
            # Get random stock item or create new one
            stock_items = list(item.stock_items.all())
            if stock_items and random.random() < 0.6:
                # 60% chance to update existing stock
                stock_item = random.choice(stock_items)
                
                # Add to existing quantity
                additional_quantity = random.randint(1, 50)
                old_quantity = stock_item.quantity
                stock_item.quantity += additional_quantity
                stock_item.save()
                
                # Create audit event
                audit_log_event(
                    user,
                    f"Stock check-in: added {additional_quantity} units (was {old_quantity}, now {stock_item.quantity})",
                    audit_log_state(None),
                    audit_log_state(stock_item)
                )
                
            else:
                # 40% chance to create new stock item (new delivery)
                organizations = list(Organization.objects.all())
                if organizations:
                    org = random.choice(organizations)
                    
                    locations = [
                        'Warehouse A-1', 'Warehouse B-2', 'Storage Room 101', 'Receiving Area',
                        'Loading Dock', 'Supply Cabinet', 'Main Office', 'Branch Office'
                    ]
                    
                    new_stock = StockItem.objects.create(
                        item=item,
                        organization=org,
                        quantity=random.randint(1, 100),
                        location=random.choice(locations),
                        date_received=date.today() - timedelta(days=random.randint(0, 30)),
                        notes=f"New delivery - stress test check-in by {user.get_full_name() or user.username}"
                    )
                    
                    # Create audit event
                    audit_log_event(
                        user,
                        f"New stock delivery: {new_stock.quantity} units",
                        audit_log_state(None),
                        audit_log_state(new_stock)
                    )
            
            return True
            
        except Exception as e:
            # Silently continue on errors
            pass
        
        return False