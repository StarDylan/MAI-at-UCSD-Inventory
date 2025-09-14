from django.core.management.base import BaseCommand
from inventory.models import TagGroup, Tag
import random


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
            '--clear',
            action='store_true',
            help='Clear existing tag groups and tags before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing tag groups and tags...')
            Tag.objects.all().delete()
            TagGroup.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))

        try:
            tag_groups_created = self.create_tag_groups(options['tag_groups'])
            tags_created = self.create_tags(tag_groups_created, options['tags_per_group'])

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {len(tag_groups_created)} tag groups and {tags_created} tags'
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
