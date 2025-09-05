from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from .models import Category, Subcategory, Item, Organization, StockItem


class OrganizationModelTest(TestCase):
    def test_create_organization(self):
        """Test creating an organization"""
        org = Organization.objects.create(
            name="Test Supplier",
            description="A test supplier organization",
            contact_email="contact@testsupplier.com",
            contact_phone="555-0123",
            address="123 Test St, Test City, TC 12345"
        )
        self.assertEqual(str(org), "Test Supplier")
        self.assertEqual(org.contact_email, "contact@testsupplier.com")

    def test_organization_unique_constraint(self):
        """Test that organization names must be unique"""
        Organization.objects.create(name="Duplicate Name")
        with self.assertRaises(Exception):  # Django will raise IntegrityError
            Organization.objects.create(name="Duplicate Name")


class StockItemModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(name="Test Category")
        self.item = Item.objects.create(
            name="Test Item",
            category=self.category
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            description="Test organization"
        )

    def test_create_stock_item(self):
        """Test creating a stock item"""
        stock = StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=10,
            location="Test Location",
            date_received=date.today(),
            expiration_date=date.today() + timedelta(days=30),
            lot_number="LOT123"
        )
        self.assertEqual(stock.quantity, 10)
        self.assertEqual(stock.item, self.item)
        self.assertEqual(stock.organization, self.organization)
        self.assertFalse(stock.is_expired)

    def test_stock_item_without_expiration(self):
        """Test creating a stock item without expiration date (non-perishable)"""
        stock = StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=5,
            location="Storage Room A",
            date_received=date.today()
        )
        self.assertIsNone(stock.expiration_date)
        self.assertFalse(stock.is_expired)

    def test_expired_stock_item(self):
        """Test expired stock item detection"""
        expired_date = date.today() - timedelta(days=1)
        stock = StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=3,
            location="Expired Storage",
            date_received=date.today() - timedelta(days=10),
            expiration_date=expired_date
        )
        self.assertTrue(stock.is_expired)

    def test_item_total_stock_quantity(self):
        """Test the total stock quantity property on Item"""
        # Create multiple stock items for the same item
        StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=10,
            location="Shelf A",
            date_received=date.today()
        )
        StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=5,
            location="Shelf B",
            date_received=date.today()
        )
        StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=0,  # This should not be counted (inactive)
            location="Storage",
            date_received=date.today()
        )
        
        # Check total quantity
        self.assertEqual(self.item.total_stock_quantity, 15)  # 10 + 5 (0 quantity is inactive)

    def test_stock_item_str_representation(self):
        """Test the string representation of StockItem"""
        stock = StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=7,
            location="Warehouse A",
            date_received=date.today()
        )
        expected_str = f"{self.item.name} - 7 units from Warehouse A"
        self.assertEqual(str(stock), expected_str)


class ItemGTINTest(TestCase):
    def setUp(self):
        """Set up test data for GTIN tests"""
        self.category = Category.objects.create(name="Test Category")
        self.organization = Organization.objects.create(
            name="Test Org",
            description="Test organization"
        )

    def test_stockitem_with_gtin(self):
        """Test creating a stock item with GTIN"""
        item = Item.objects.create(
            name="Test Item",
            category=self.category
        )
        stock_item = StockItem.objects.create(
            item=item,
            organization=self.organization,
            quantity=10,
            location="Test Location",
            gtin="1234567890123",
            date_received=timezone.now().date()
        )
        self.assertEqual(stock_item.gtin, "1234567890123")

    def test_stockitem_without_gtin(self):
        """Test creating a stock item without GTIN (blank)"""
        item = Item.objects.create(
            name="Test Item",
            category=self.category
        )
        stock_item = StockItem.objects.create(
            item=item,
            organization=self.organization,
            quantity=10,
            location="Test Location",
            date_received=timezone.now().date()
        )
        self.assertEqual(stock_item.gtin, "")

    def test_stockitem_gtin_uniqueness_constraint(self):
        """Test that GTIN must be unique when provided on stock items"""
        item1 = Item.objects.create(
            name="First Item",
            category=self.category
        )
        item2 = Item.objects.create(
            name="Second Item",
            category=self.category
        )
        
        # Create first stock item with GTIN
        StockItem.objects.create(
            item=item1,
            organization=self.organization,
            quantity=10,
            location="Location 1",
            gtin="1234567890123",
            date_received=timezone.now().date()
        )
        
        # Try to create second stock item with same GTIN - should raise IntegrityError
        with self.assertRaises(Exception):  # Django will raise IntegrityError
            StockItem.objects.create(
                item=item2,
                organization=self.organization,
                quantity=5,
                location="Location 2",
                gtin="1234567890123",
                date_received=timezone.now().date()
            )

    def test_stockitem_gtin_uniqueness_allows_empty(self):
        """Test that multiple stock items can have empty GTIN"""
        item1 = Item.objects.create(
            name="First Item",
            category=self.category
        )
        item2 = Item.objects.create(
            name="Second Item",
            category=self.category
        )
        
        # Create two stock items with empty GTIN
        stock1 = StockItem.objects.create(
            item=item1,
            organization=self.organization,
            quantity=10,
            location="Location 1",
            gtin="",
            date_received=timezone.now().date()
        )
        stock2 = StockItem.objects.create(
            item=item2,
            organization=self.organization,
            quantity=5,
            location="Location 2",
            gtin="",
            date_received=timezone.now().date()
        )
        
        # Should succeed without errors
        self.assertEqual(stock1.gtin, "")
        self.assertEqual(stock2.gtin, "")

    def test_stockitem_different_gtins_allowed(self):
        """Test that different GTINs can be used on different stock items"""
        item1 = Item.objects.create(
            name="First Item",
            category=self.category
        )
        item2 = Item.objects.create(
            name="Second Item",
            category=self.category
        )
        
        stock1 = StockItem.objects.create(
            item=item1,
            organization=self.organization,
            quantity=10,
            location="Location 1",
            gtin="1234567890123",
            date_received=timezone.now().date()
        )
        stock2 = StockItem.objects.create(
            item=item2,
            organization=self.organization,
            quantity=5,
            location="Location 2",
            gtin="9876543210987",
            date_received=timezone.now().date()
        )
        
        self.assertEqual(stock1.gtin, "1234567890123")
        self.assertEqual(stock2.gtin, "9876543210987")

    def test_stockitem_detail_field(self):
        """Test that stock items can have detail information"""
        item = Item.objects.create(
            name="Test Item",
            category=self.category
        )
        stock_item = StockItem.objects.create(
            item=item,
            organization=self.organization,
            quantity=10,
            location="Test Location",
            detail="Size Large, Red Color",
            date_received=timezone.now().date()
        )
        self.assertEqual(stock_item.detail, "Size Large, Red Color")

    def test_stockitem_ordering_by_detail(self):
        """Test that stock items are ordered by detail field first"""
        item = Item.objects.create(
            name="Test Item",
            category=self.category
        )
        
        # Create stock items with different details
        stock1 = StockItem.objects.create(
            item=item,
            organization=self.organization,
            quantity=10,
            location="Location 1",
            detail="B - Medium",
            date_received=timezone.now().date()
        )
        stock2 = StockItem.objects.create(
            item=item,
            organization=self.organization,
            quantity=5,
            location="Location 2",
            detail="A - Small",
            date_received=timezone.now().date()
        )
        stock3 = StockItem.objects.create(
            item=item,
            organization=self.organization,
            quantity=8,
            location="Location 3",
            detail="C - Large",
            date_received=timezone.now().date()
        )
        
        # Get ordered stock items
        ordered_stocks = list(item.stock_items.all())
        
        # Should be ordered by detail field
        self.assertEqual(ordered_stocks[0].detail, "A - Small")
        self.assertEqual(ordered_stocks[1].detail, "B - Medium")
        self.assertEqual(ordered_stocks[2].detail, "C - Large")


class ItemWithStockFormGTINTest(TestCase):
    def setUp(self):
        """Set up test data for form tests"""
        from .models import Subcategory
        self.category = Category.objects.create(name="Test Category")
        self.subcategory = Subcategory.objects.create(
            name="Test Subcategory",
            category=self.category
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            description="Test organization"
        )

    def test_form_requires_stock_location(self):
        """Test that form validation requires stock location"""
        from .forms import ItemWithStockForm
        
        # Try to create a form without stock_location
        form_data = {
            'name': 'Test Item',
            'gtin': '',
            'subcategory': self.subcategory.id,
            'organization': self.organization.id,
            'quantity': 1,
            'date_received': date.today(),
            # Missing stock_location
        }
        
        form = ItemWithStockForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('stock_location', form.errors)

    def test_quantity_add_form_requires_location(self):
        """Test that Search_QuantityAdd form requires location"""
        from .forms import Search_QuantityAdd
        
        # Create an item first
        item = Item.objects.create(
            name="Test Item",
            category=self.category,
            subcategory=self.subcategory
        )
        
        # Try to create a form without location
        form_data = {
            'item': item.id,
            'organization': self.organization.id,
            'quantity': 5,
            'date_received': date.today(),
            # Missing location
        }
        
        form = Search_QuantityAdd(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('location', form.errors)

    def test_stock_item_model_form_requires_location(self):
        """Test that StockItemForm requires location due to model constraint"""
        from .forms import StockItemForm
        
        # Try to create a form without location
        form_data = {
            'organization': self.organization.id,
            'quantity': 5,
            'date_received': date.today(),
            # Missing location
        }
        
        form = StockItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('location', form.errors)

    def test_stock_item_model_form_accepts_location(self):
        """Test that StockItemForm accepts when location is provided"""
        from .forms import StockItemForm
        
        # Create a form with location
        form_data = {
            'organization': self.organization.id,
            'quantity': 5,
            'location': 'Warehouse B',
            'date_received': date.today(),
        }
        
        form = StockItemForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_gtin_validation_duplicate(self):
        """Test that form validation catches duplicate GTIN on stock items"""
        from .forms import ItemWithStockForm
        
        # Create an existing item with stock item that has GTIN
        existing_item = Item.objects.create(
            name="Existing Item",
            category=self.category,
            subcategory=self.subcategory
        )
        StockItem.objects.create(
            item=existing_item,
            organization=self.organization,
            quantity=10,
            location="Existing Location",
            gtin="1234567890123",
            date_received=date.today()
        )
        
        # Try to create a new item with the same GTIN
        form_data = {
            'name': 'New Item',
            'gtin': '1234567890123',  # Duplicate GTIN
            'subcategory': self.subcategory.id,
            'organization': self.organization.id,
            'quantity': 1,
            'stock_location': 'Test Location',
            'date_received': date.today(),
        }
        
        form = ItemWithStockForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('gtin', form.errors)
        # Check that the error message contains the expected text about duplicate GTIN
        gtin_errors = form.errors['gtin']
        self.assertTrue(any('already exists' in str(error) for error in gtin_errors))

    def test_form_gtin_validation_unique(self):
        """Test that form validation allows unique GTIN"""
        from .forms import ItemWithStockForm
        
        # Create an existing item with stock item that has GTIN
        existing_item = Item.objects.create(
            name="Existing Item",
            category=self.category,
            subcategory=self.subcategory
        )
        StockItem.objects.create(
            item=existing_item,
            organization=self.organization,
            quantity=10,
            location="Existing Location",
            gtin="1234567890123",
            date_received=date.today()
        )
        
        # Try to create a new item with a different GTIN
        form_data = {
            'name': 'New Item',
            'gtin': '9876543210987',  # Different GTIN
            'subcategory': self.subcategory.id,
            'organization': self.organization.id,
            'quantity': 1,
            'stock_location': 'Test Location',
            'date_received': date.today(),
        }
        
        form = ItemWithStockForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_gtin_validation_empty(self):
        """Test that form validation allows empty GTIN"""
        from .forms import ItemWithStockForm
        
        # Create an existing item with stock item that has GTIN
        existing_item = Item.objects.create(
            name="Existing Item",
            category=self.category,
            subcategory=self.subcategory
        )
        StockItem.objects.create(
            item=existing_item,
            organization=self.organization,
            quantity=10,
            location="Existing Location",
            gtin="1234567890123",
            date_received=date.today()
        )
        
        # Try to create a new item with empty GTIN
        form_data = {
            'name': 'New Item',
            'gtin': '',  # Empty GTIN
            'subcategory': self.subcategory.id,
            'organization': self.organization.id,
            'quantity': 1,
            'stock_location': 'Test Location',
            'date_received': date.today(),
        }
        
        form = ItemWithStockForm(data=form_data)
        self.assertTrue(form.is_valid())


# Create your other tests here.
