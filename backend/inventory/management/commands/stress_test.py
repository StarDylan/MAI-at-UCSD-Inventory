from django.core.management.base import BaseCommand
from inventory.models import TagGroup, Tag, Item, StockItem, Organization, User, AuditEvent, CheckOut, CheckOutItem
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import random
import uuid
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create a bunch of miscellaneous tag groups and tags for stress testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tag-groups',
            type=int,
            default=15,
            help='Number of tag groups to create (default: 15)',
        )
        parser.add_argument(
            '--tags-per-group',
            type=int,
            default=8,
            help='Average number of tags per group (default: 8)',
        )
        parser.add_argument(
            '--items',
            type=int,
            default=10000,
            help='Number of items to create (default: 10000)',
        )
        parser.add_argument(
            '--audit-events',
            type=int,
            default=15000,
            help='Number of audit events to create (default: 15000)',
        )
        parser.add_argument(
            '--checkouts',
            type=int,
            default=1000,
            help='Number of checkouts to create (default: 1000)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing tag groups and tags before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            # Clear in the right order due to foreign key constraints
            CheckOut.objects.all().delete()
            AuditEvent.objects.all().delete()
            StockItem.objects.all().delete()
            Item.objects.all().delete()
            Tag.objects.all().delete()
            TagGroup.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))

        try:
            # Create organizations and users first (needed for other data)
            organizations = self.create_organizations()
            users = self.create_users()
            
            # Create tag groups and tags
            tag_groups_created = self.create_tag_groups(options['tag_groups'])
            tags_created = self.create_tags(tag_groups_created, options['tags_per_group'])
            
            # Create items and stock items
            items_created = self.create_items_and_stock(options['items'], tag_groups_created, organizations)
            
            # Create audit events
            audit_events_created = self.create_audit_events(options['audit_events'], users)
            
            # Create checkouts
            checkouts_created = self.create_checkouts(options['checkouts'], organizations, users)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created:\n'
                    f'  - {len(organizations)} organizations\n'
                    f'  - {len(users)} users\n'
                    f'  - {len(tag_groups_created)} tag groups\n'
                    f'  - {tags_created} tags\n'
                    f'  - {items_created} items with stock\n'
                    f'  - {audit_events_created} audit events\n'
                    f'  - {checkouts_created} checkouts'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating data: {e}')
            )
            raise

    def create_tag_groups(self, num_groups):
        """Create diverse tag groups with realistic categories"""
        
        # Predefined tag group templates with colors and descriptions
        tag_group_templates = [
            {
                'name': 'Medical Supplies',
                'description': 'Equipment and supplies for medical and healthcare purposes',
                'color': '#dc3545',  # Red
            },
            {
                'name': 'Office Equipment',
                'description': 'General office supplies and equipment',
                'color': '#007bff',  # Blue
            },
            {
                'name': 'Electronics',
                'description': 'Electronic devices and components',
                'color': '#ffc107',  # Yellow
            },
            {
                'name': 'Safety Equipment',
                'description': 'Personal protective equipment and safety gear',
                'color': '#fd7e14',  # Orange
            },
            {
                'name': 'Cleaning Supplies',
                'description': 'Cleaning and maintenance supplies',
                'color': '#20c997',  # Teal
            },
            {
                'name': 'Food Service',
                'description': 'Kitchen and food service equipment',
                'color': '#6f42c1',  # Purple
            },
            {
                'name': 'Educational Materials',
                'description': 'Teaching and learning resources',
                'color': '#28a745',  # Green
            },
            {
                'name': 'Furniture',
                'description': 'Office and institutional furniture',
                'color': '#6c757d',  # Gray
            },
            {
                'name': 'Transportation',
                'description': 'Vehicles and transportation equipment',
                'color': '#17a2b8',  # Info
            },
            {
                'name': 'Storage Solutions',
                'description': 'Containers, shelving, and storage equipment',
                'color': '#e83e8c',  # Pink
            },
            {
                'name': 'Tools & Hardware',
                'description': 'Hand tools, power tools, and hardware',
                'color': '#343a40',  # Dark
            },
            {
                'name': 'Textiles & Fabrics',
                'description': 'Clothing, bedding, and fabric materials',
                'color': '#fd7e14',  # Orange
            },
            {
                'name': 'Laboratory Equipment',
                'description': 'Scientific and laboratory instruments',
                'color': '#6610f2',  # Indigo
            },
            {
                'name': 'Sports & Recreation',
                'description': 'Athletic and recreational equipment',
                'color': '#20c997',  # Teal
            },
            {
                'name': 'Emergency Supplies',
                'description': 'Emergency preparedness and disaster relief supplies',
                'color': '#dc3545',  # Red
            },
            {
                'name': 'IT & Networking',
                'description': 'Information technology and networking equipment',
                'color': '#007bff',  # Blue
            },
            {
                'name': 'Automotive',
                'description': 'Vehicle parts and automotive supplies',
                'color': '#343a40',  # Dark
            },
            {
                'name': 'Art & Craft Supplies',
                'description': 'Creative materials and art supplies',
                'color': '#e83e8c',  # Pink
            },
            {
                'name': 'Building Materials',
                'description': 'Construction and building supplies',
                'color': '#6c757d',  # Gray
            },
            {
                'name': 'Personal Care',
                'description': 'Personal hygiene and care products',
                'color': '#20c997',  # Teal
            }
        ]

        # Additional colors for extra groups if needed
        extra_colors = [
            '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57',
            '#ff9ff3', '#54a0ff', '#5f27cd', '#00d2d3', '#ff9f43',
            '#10ac84', '#ee5a24', '#0abde3', '#3867d6', '#8c7ae6'
        ]

        created_groups = []
        
        # Create tag groups from templates and generate additional ones if needed
        for i in range(num_groups):
            if i < len(tag_group_templates):
                template = tag_group_templates[i]
                name = template['name']
                description = template['description']
                color = template['color']
            else:
                # Generate additional groups with generic names
                name = f'Category {chr(65 + (i - len(tag_group_templates)))}'
                description = 'Miscellaneous category for various items'
                color = random.choice(extra_colors)

            # Check if tag group already exists, create if not
            try:
                tag_group, created = TagGroup.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': description,
                        'color': color,
                        'sort_order': i * 10,  # Leave space for manual reordering
                    }
                )
                if created:
                    self.stdout.write(f'Created tag group: {tag_group.name}')
                else:
                    self.stdout.write(f'Tag group already exists: {tag_group.name}')
                created_groups.append(tag_group)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error with tag group "{name}": {e}'))
                continue

        return created_groups

    def create_tags(self, tag_groups, avg_tags_per_group):
        """Create tags for each tag group"""
        
        # Predefined tag templates organized by category
        tag_templates = {
            'Medical Supplies': [
                'PPE', 'Disposable', 'Sterile', 'Non-Sterile', 'Diagnostic',
                'Surgical', 'First Aid', 'Pharmaceuticals', 'Bandages', 'Syringes'
            ],
            'Office Equipment': [
                'Stationery', 'Printing', 'Communication', 'Storage', 'Desk Accessories',
                'Binding', 'Technology', 'Filing', 'Writing Instruments', 'Paper Products'
            ],
            'Electronics': [
                'Computers', 'Mobile Devices', 'Audio/Video', 'Gaming', 'Cables/Adapters',
                'Storage Devices', 'Networking', 'Components', 'Peripherals', 'Batteries'
            ],
            'Safety Equipment': [
                'Hard Hats', 'Safety Glasses', 'Gloves', 'High Visibility', 'Respirators',
                'Fall Protection', 'Emergency Equipment', 'Fire Safety', 'Chemical Protection', 'Hearing Protection'
            ],
            'Cleaning Supplies': [
                'Disinfectants', 'Detergents', 'Paper Towels', 'Trash Bags', 'Mops/Brooms',
                'Vacuum Supplies', 'Window Cleaning', 'Floor Care', 'Restroom Supplies', 'Chemical Cleaners'
            ],
            'Food Service': [
                'Cookware', 'Serving Dishes', 'Utensils', 'Small Appliances', 'Food Storage',
                'Disposable Items', 'Cleaning/Sanitation', 'Prep Equipment', 'Beverage Service', 'Catering Supplies'
            ],
            'Educational Materials': [
                'Books', 'Supplies', 'Technology', 'Art Materials', 'Science Equipment',
                'Sports Equipment', 'Furniture', 'Audio/Visual', 'Games/Puzzles', 'Teaching Aids'
            ],
            'Furniture': [
                'Seating', 'Tables', 'Storage', 'Bedroom', 'Reception/Lounge',
                'Outdoor', 'Specialized', 'Accessories', 'Ergonomic', 'Modular'
            ],
            'Transportation': [
                'Vehicles', 'Bicycles', 'Accessories', 'Maintenance', 'Safety',
                'Electric', 'Public Transit', 'Cargo', 'Personal Mobility', 'Fleet'
            ],
            'Storage Solutions': [
                'Containers', 'Shelving', 'Cabinets', 'Bins/Baskets', 'Specialty Storage',
                'Mobile Storage', 'Security Storage', 'Archive Storage', 'Industrial Storage', 'Personal Storage'
            ],
            'Tools & Hardware': [
                'Hand Tools', 'Power Tools', 'Fasteners', 'Hardware', 'Measuring Tools',
                'Cutting Tools', 'Safety Equipment', 'Tool Storage', 'Specialty Tools', 'Workshop Equipment'
            ],
            'Textiles & Fabrics': [
                'Clothing', 'Bedding', 'Towels', 'Curtains/Drapes', 'Upholstery',
                'Fabric Materials', 'Protective Clothing', 'Uniforms', 'Outdoor Gear', 'Specialty Textiles'
            ],
            'Laboratory Equipment': [
                'Instruments', 'Glassware', 'Chemicals', 'Safety Equipment', 'Measurement Tools',
                'Microscopy', 'Heating/Cooling', 'Mixing/Separation', 'Sample Storage', 'Consumables'
            ],
            'Sports & Recreation': [
                'Team Sports', 'Individual Sports', 'Fitness Equipment', 'Outdoor Recreation', 'Water Sports',
                'Winter Sports', 'Protective Gear', 'Training Equipment', 'Games/Entertainment', 'Accessories'
            ],
            'Emergency Supplies': [
                'First Aid', 'Communication', 'Shelter', 'Food/Water', 'Tools',
                'Lighting', 'Power Sources', 'Sanitation', 'Personal Items', 'Documentation'
            ],
            'IT & Networking': [
                'Servers', 'Network Equipment', 'Cables', 'Security', 'Storage',
                'Software', 'Peripherals', 'Components', 'Tools', 'Documentation'
            ],
            'Automotive': [
                'Engine Parts', 'Body Parts', 'Electrical', 'Fluids', 'Tools',
                'Accessories', 'Safety Equipment', 'Maintenance Items', 'Performance Parts', 'Cleaning Supplies'
            ],
            'Art & Craft Supplies': [
                'Drawing', 'Painting', 'Sculpting', 'Paper Crafts', 'Fabric Crafts',
                'Jewelry Making', 'Woodworking', 'Model Making', 'Scrapbooking', 'General Supplies'
            ],
            'Building Materials': [
                'Lumber', 'Hardware', 'Plumbing', 'Electrical', 'Roofing',
                'Flooring', 'Insulation', 'Concrete/Masonry', 'Doors/Windows', 'Tools'
            ],
            'Personal Care': [
                'Hygiene Products', 'Hair Care', 'Skin Care', 'Oral Care', 'Health Monitoring',
                'First Aid', 'Grooming Tools', 'Feminine Care', 'Baby Care', 'Specialty Items'
            ]
        }

        # Generic tags for categories without specific templates
        generic_tags = [
            'Small', 'Medium', 'Large', 'Portable', 'Heavy Duty', 'Commercial Grade',
            'Residential', 'Professional', 'Budget', 'Premium', 'Eco-Friendly', 'Durable',
            'Lightweight', 'Compact', 'Multipurpose', 'Specialized', 'Vintage', 'Modern',
            'Digital', 'Manual', 'Automatic', 'Wireless', 'Wired', 'Battery Powered'
        ]

        total_tags_created = 0

        for tag_group in tag_groups:
            # Determine number of tags for this group (vary around the average)
            num_tags = max(3, avg_tags_per_group + random.randint(-3, 3))
            
            # Get tags for this category
            if tag_group.name in tag_templates:
                available_tags = tag_templates[tag_group.name].copy()
            else:
                available_tags = generic_tags.copy()
            
            # Shuffle and select tags
            random.shuffle(available_tags)
            selected_tags = available_tags[:num_tags]
            
            # If we need more tags than available, supplement with generic ones
            if len(selected_tags) < num_tags:
                remaining_generic = [tag for tag in generic_tags if tag not in selected_tags]
                random.shuffle(remaining_generic)
                selected_tags.extend(remaining_generic[:num_tags - len(selected_tags)])

            # Create the tags
            for i, tag_name in enumerate(selected_tags):
                # Occasionally give a tag its own color (10% chance)
                tag_color = ""
                if random.random() < 0.1:
                    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
                    tag_color = random.choice(colors)

                try:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name,
                        defaults={
                            'description': f'{tag_name} items in {tag_group.name}',
                            'tag_group': tag_group,
                            'color': tag_color,
                            'sort_order': i * 10,
                        }
                    )
                    if created:
                        self.stdout.write(f'  Created tag: {tag_group.name}: {tag_name}')
                    else:
                        self.stdout.write(f'  Tag already exists: {tag_name}')
                    total_tags_created += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error with tag "{tag_name}": {e}'))
                    continue

        return total_tags_created

    def create_organizations(self):
        """Create a few organizations for testing"""
        organizations_data = [
            {
                'name': 'Main University Hospital',
                'description': 'Primary medical facility',
                'contact_email': 'admin@mainhospital.edu',
                'contact_phone': '555-0100',
                'address': '123 Medical Center Dr, City, State 12345'
            },
            {
                'name': 'Community Health Center',
                'description': 'Local community medical center',
                'contact_email': 'info@communityhc.org',
                'contact_phone': '555-0200',
                'address': '456 Community Blvd, City, State 12345'
            },
            {
                'name': 'Research Institute',
                'description': 'Medical research facility',
                'contact_email': 'research@institute.edu',
                'contact_phone': '555-0300',
                'address': '789 Research Park, City, State 12345'
            },
            {
                'name': 'Emergency Services',
                'description': 'Emergency medical services',
                'contact_email': 'dispatch@ems.gov',
                'contact_phone': '555-0400',
                'address': '999 Emergency Way, City, State 12345'
            }
        ]

        created_orgs = []
        for org_data in organizations_data:
            org, created = Organization.objects.get_or_create(
                name=org_data['name'],
                defaults=org_data
            )
            if created:
                self.stdout.write(f'Created organization: {org.name}')
            else:
                self.stdout.write(f'Organization already exists: {org.name}')
            created_orgs.append(org)

        return created_orgs

    def create_users(self):
        """Create test users"""
        users_data = [
            {
                'username': 'admin_user',
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            },
            {
                'username': 'inventory_manager',
                'email': 'manager@example.com',
                'first_name': 'Inventory',
                'last_name': 'Manager',
                'is_staff': True,
                'is_superuser': False
            },
            {
                'username': 'staff_user1',
                'email': 'staff1@example.com',
                'first_name': 'Staff',
                'last_name': 'One',
                'is_staff': False,
                'is_superuser': False
            },
            {
                'username': 'staff_user2',
                'email': 'staff2@example.com',
                'first_name': 'Staff',
                'last_name': 'Two',
                'is_staff': False,
                'is_superuser': False
            }
        ]

        created_users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password('testpass123')  # Set a default password
                user.save()
                self.stdout.write(f'Created user: {user.username}')
            else:
                self.stdout.write(f'User already exists: {user.username}')
            created_users.append(user)

        return created_users

    def create_items_and_stock(self, num_items, tag_groups, organizations):
        """Create items with associated stock items"""
        # Common item name patterns
        item_patterns = [
            'Surgical Mask', 'N95 Respirator', 'Nitrile Gloves', 'Surgical Gloves', 'Hand Sanitizer',
            'Disinfectant Wipes', 'Thermometer', 'Blood Pressure Cuff', 'Stethoscope', 'Syringes',
            'Gauze Pads', 'Medical Tape', 'Bandages', 'Scissors', 'Forceps',
            'Laptop Computer', 'Desktop Monitor', 'Wireless Mouse', 'USB Cable', 'Network Switch',
            'Office Chair', 'Desk Lamp', 'Filing Cabinet', 'Printer Paper', 'Stapler',
            'Safety Goggles', 'Hard Hat', 'Reflective Vest', 'Emergency Kit', 'Fire Extinguisher',
            'Cleaning Solution', 'Vacuum Cleaner', 'Mop Bucket', 'Trash Bags', 'Paper Towels'
        ]

        manufacturers = [
            '3M', 'Johnson & Johnson', 'Medline', 'Cardinal Health', 'Honeywell',
            'Dell', 'HP', 'Lenovo', 'Microsoft', 'Cisco',
            'Steelcase', 'Herman Miller', 'Rubbermaid', 'Procter & Gamble', 'Clorox'
        ]

        locations = [
            'Warehouse A1', 'Warehouse A2', 'Warehouse B1', 'Warehouse B2', 'Storage Room 101',
            'Storage Room 102', 'Medical Supply Room', 'IT Storage', 'Emergency Supply',
            'Main Floor Storage', 'Basement Storage', 'Clean Room', 'Sterile Storage',
            'Office Supply Room', 'Maintenance Shop'
        ]

        created_count = 0
        batch_size = 100

        self.stdout.write(f'Creating {num_items} items...')

        for i in range(num_items):
            # Generate item data
            base_name = random.choice(item_patterns)
            variant = random.choice(['', 'Pro', 'Plus', 'Standard', 'Premium', 'Basic', 'XL', 'Large', 'Small'])
            name = f"{base_name} {variant}".strip()
            
            # Make name unique
            if Item.objects.filter(name=name).exists():
                name = f"{name} #{i+1}"

            gtin = f"{random.randint(100000000000, 999999999999)}" if random.random() < 0.3 else ""
            manufacturer = random.choice(manufacturers)
            items_per_box = random.choice([1, 5, 10, 20, 25, 50, 100]) if random.random() < 0.7 else None
            cost_per_item = Decimal(f"{random.uniform(0.50, 500.00):.2f}") if random.random() < 0.8 else None

            # Create item
            try:
                item = Item.objects.create(
                    name=name,
                    manufacturer=manufacturer,
                    gtin=gtin,
                    items_per_box=items_per_box,
                    cost_per_item=cost_per_item,
                    notes_public=f"Generated test item {i+1}",
                    notes_private="Stress test data"
                )

                # Add random tags (1-5 tags per item)
                if tag_groups:
                    all_tags = []
                    for tg in tag_groups:
                        all_tags.extend(tg.tags.all())
                    
                    if all_tags:
                        num_tags = random.randint(1, min(5, len(all_tags)))
                        selected_tags = random.sample(all_tags, num_tags)
                        item.tags.set(selected_tags)

                # Create 1-5 stock items for each item
                num_stock_items = random.randint(1, 5)
                for _ in range(num_stock_items):
                    quantity = random.randint(1, 1000)
                    location = random.choice(locations)
                    organization = random.choice(organizations)
                    
                    # Generate dates
                    days_ago = random.randint(1, 365)
                    date_received = timezone.now().date() - timedelta(days=days_ago)
                    
                    expiration_date = None
                    if random.random() < 0.4:  # 40% chance of having expiration
                        exp_days = random.randint(30, 365*3)
                        expiration_date = date_received + timedelta(days=exp_days)

                    StockItem.objects.create(
                        item=item,
                        organization=organization,
                        quantity=quantity,
                        location=location,
                        gtin=gtin if random.random() < 0.2 else "",  # Sometimes stock item has different GTIN
                        detail=random.choice(['', 'Size M', 'Size L', 'Blue', 'Red', 'Model A', 'Version 2']),
                        date_received=date_received,
                        expiration_date=expiration_date,
                        lot_number=f"LOT{random.randint(1000, 9999)}" if random.random() < 0.6 else "",
                        surplus_status=random.choice(['pending', 'wanted', 'not_wanted'])
                    )

                created_count += 1

                if created_count % batch_size == 0:
                    self.stdout.write(f'  Created {created_count}/{num_items} items...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating item {i+1}: {e}'))
                continue

        self.stdout.write(f'Created {created_count} items with stock')
        return created_count

    def create_audit_events(self, num_events, users):
        """Create fake audit events"""
        if not users:
            self.stdout.write(self.style.WARNING('No users available for audit events'))
            return 0

        # Get all items, organizations, and users for audit events
        items = list(Item.objects.all()[:1000])  # Limit to first 1000 items for performance
        organizations = list(Organization.objects.all())
        
        if not items:
            self.stdout.write(self.style.WARNING('No items available for audit events'))
            return 0

        entity_types = ['Item', 'StockItem', 'Organization', 'User', 'CheckOut']
        events = [
            'created', 'updated', 'deleted', 'restored', 'quantity_changed',
            'location_moved', 'status_changed', 'completed', 'cancelled'
        ]

        created_count = 0
        batch_size = 500

        self.stdout.write(f'Creating {num_events} audit events...')

        audit_events = []
        for i in range(num_events):
            # Generate event data
            entity_type = random.choice(entity_types)
            event = random.choice(events)
            user = random.choice(users)
            
            # Generate realistic entity_id based on type
            if entity_type == 'Item' and items:
                entity_id = random.choice(items).id
            elif entity_type == 'Organization' and organizations:
                entity_id = random.choice(organizations).id
            elif entity_type == 'User':
                entity_id = random.choice(users).id
            else:
                entity_id = uuid.uuid4()

            # Generate before/after data
            before_data = ""
            after_data = ""
            
            if event == 'quantity_changed':
                old_qty = random.randint(0, 100)
                new_qty = random.randint(0, 100)
                before_data = f'{{"quantity": {old_qty}}}'
                after_data = f'{{"quantity": {new_qty}}}'
            elif event == 'updated':
                before_data = '{"name": "Old Name", "status": "active"}'
                after_data = '{"name": "New Name", "status": "active"}'
            elif event == 'created':
                after_data = '{"status": "created", "initial": true}'
            elif event == 'deleted':
                before_data = '{"status": "active"}'
                after_data = '{"status": "deleted"}'

            # Generate timestamp (spread over last year)
            days_ago = random.randint(0, 365)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_at = timezone.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

            audit_events.append(AuditEvent(
                entity_type=entity_type,
                entity_id=entity_id,
                user=user,
                event=event,
                before=before_data,
                after=after_data,
                created_at=created_at
            ))

            if len(audit_events) >= batch_size:
                AuditEvent.objects.bulk_create(audit_events)
                created_count += len(audit_events)
                audit_events = []
                self.stdout.write(f'  Created {created_count}/{num_events} audit events...')

        # Create remaining events
        if audit_events:
            AuditEvent.objects.bulk_create(audit_events)
            created_count += len(audit_events)

        self.stdout.write(f'Created {created_count} audit events')
        return created_count

    def create_checkouts(self, num_checkouts, organizations, users):
        """Create checkouts with random items"""
        if not organizations or not users:
            self.stdout.write(self.style.WARNING('No organizations or users available for checkouts'))
            return 0

        # Get stock items for checkouts
        stock_items = list(StockItem.objects.filter(quantity__gt=0)[:5000])  # Limit for performance
        
        if not stock_items:
            self.stdout.write(self.style.WARNING('No stock items available for checkouts'))
            return 0

        created_count = 0
        batch_size = 50

        self.stdout.write(f'Creating {num_checkouts} checkouts...')

        for i in range(num_checkouts):
            try:
                # Create checkout
                organization = random.choice(organizations)
                created_by = random.choice(users)
                is_completed = random.random() < 0.7  # 70% completed
                is_donation = random.random() < 0.8   # 80% donations

                # Generate dates
                days_ago = random.randint(1, 365)
                created_at = timezone.now() - timedelta(days=days_ago)
                
                completed_at = None
                completed_by = None
                total_weight = None
                
                if is_completed:
                    completed_by = random.choice(users)
                    hours_later = random.randint(1, 48)
                    completed_at = created_at + timedelta(hours=hours_later)
                    total_weight = Decimal(f"{random.uniform(1.0, 500.0):.2f}")

                checkout = CheckOut.objects.create(
                    organization=organization,
                    created_by=created_by,
                    created_at=created_at,
                    completed_by=completed_by,
                    completed_at=completed_at,
                    total_weight=total_weight,
                    notes=f"Test checkout {i+1}",
                    is_completed=is_completed,
                    is_donation=is_donation
                )

                # Add 1-100 items to checkout
                num_items = random.randint(1, 100)
                selected_stock_items = random.sample(stock_items, min(num_items, len(stock_items)))
                
                checkout_items = []
                for stock_item in selected_stock_items:
                    # Don't checkout more than available
                    max_quantity = min(stock_item.quantity, 50)
                    if max_quantity > 0:
                        quantity = random.randint(1, max_quantity)
                        
                        checkout_items.append(CheckOutItem(
                            checkout=checkout,
                            stock_item=stock_item,
                            quantity=quantity,
                            notes=f"Checkout item for {stock_item.item.name}"
                        ))

                # Bulk create checkout items
                if checkout_items:
                    CheckOutItem.objects.bulk_create(checkout_items)

                created_count += 1

                if created_count % batch_size == 0:
                    self.stdout.write(f'  Created {created_count}/{num_checkouts} checkouts...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating checkout {i+1}: {e}'))
                continue

        self.stdout.write(f'Created {created_count} checkouts')
        return created_count
