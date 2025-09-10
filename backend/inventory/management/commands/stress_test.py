"""
Management command for stress testing the inventory system.

Creates ~10,000 items with mock data according to specified probabilities:
- Each item has 1-5 stock items (50% for 1, even distribution for 2-5)
- 50% of stock items are expired
- Various fields filled with realistic probabilities
- Includes audit events for stock operations
- Uses tqdm for progress tracking
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from tqdm import tqdm
from inventory.models import (
    Category, Subcategory, Organization, Item, StockItem, AuditEvent
)
from inventory.views.utils import audit_log_event, audit_log_state

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates stress test data with ~10,000 items and realistic mock data'

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

    def handle(self, *args, **options):
        num_items = options['items']
        clear_data = options['clear']
        create_audit = not options['no_audit']
        
        self.stdout.write(f"Starting stress test data generation...")
        self.stdout.write(f"Target items: {num_items}")
        self.stdout.write(f"Clear existing data: {clear_data}")
        self.stdout.write(f"Create audit events: {create_audit}")
        
        if clear_data:
            self.clear_existing_data()
        
        # Create or get required base data
        self.create_base_data()
        
        # Get the test user for audit events
        test_user = self.get_or_create_test_user()
        
        # Generate the stress test data
        self.generate_items_and_stock(num_items, test_user, create_audit)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created stress test data!'))

    def clear_existing_data(self):
        """Clear existing data if requested"""
        self.stdout.write("Clearing existing data...")
        
        with transaction.atomic():
            # Clear in dependency order
            AuditEvent.objects.all().delete()
            StockItem.objects.all().delete()
            Item.objects.all().delete()
            Subcategory.objects.all().delete()
            Category.objects.all().delete()
            Organization.objects.filter(name__startswith='Test Org').delete()
            
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

    def get_or_create_test_user(self):
        """Get or create a test user for audit events"""
        test_user, created = User.objects.get_or_create(
            username='stress_test_user',
            defaults={
                'email': 'stress_test@example.com',
                'first_name': 'Stress',
                'last_name': 'Test',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            test_user.set_password('stress_test_password')
            test_user.save()
        return test_user

    def generate_items_and_stock(self, num_items, test_user, create_audit):
        """Generate items with their associated stock items"""
        self.stdout.write(f"Generating {num_items} items with stock...")
        
        # Get all categories, subcategories, and organizations
        categories = list(Category.objects.all())
        subcategories = list(Subcategory.objects.all())
        organizations = list(Organization.objects.all())
        
        if not categories or not organizations:
            self.stdout.write(self.style.ERROR("No categories or organizations found. Run with base data creation first."))
            return
        
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
        
        # Generate items with progress bar
        with tqdm(total=num_items, desc="Creating items") as pbar:
            for i in range(num_items):
                with transaction.atomic():
                    # Create item
                    item = self.create_item(
                        i, categories, subcategories, item_templates, 
                        item_base_names, manufacturers
                    )
                    
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