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

    def test_item_with_gtin(self):
        """Test creating an item with GTIN"""
        item = Item.objects.create(
            name="Test Item with GTIN",
            gtin="1234567890123",
            category=self.category
        )
        self.assertEqual(item.gtin, "1234567890123")

    def test_item_without_gtin(self):
        """Test creating an item without GTIN (blank)"""
        item = Item.objects.create(
            name="Test Item without GTIN",
            category=self.category
        )
        self.assertEqual(item.gtin, "")

    def test_gtin_uniqueness_constraint(self):
        """Test that GTIN must be unique when provided"""
        # Create first item with GTIN
        Item.objects.create(
            name="First Item",
            gtin="1234567890123",
            category=self.category
        )
        
        # Try to create second item with same GTIN - should raise IntegrityError
        with self.assertRaises(Exception):  # Django will raise IntegrityError
            Item.objects.create(
                name="Second Item",
                gtin="1234567890123",
                category=self.category
            )

    def test_gtin_uniqueness_allows_empty(self):
        """Test that multiple items can have empty GTIN"""
        # Create two items with empty GTIN
        item1 = Item.objects.create(
            name="First Item",
            gtin="",
            category=self.category
        )
        item2 = Item.objects.create(
            name="Second Item",
            gtin="",
            category=self.category
        )
        
        # Should succeed without errors
        self.assertEqual(item1.gtin, "")
        self.assertEqual(item2.gtin, "")

    def test_different_gtins_allowed(self):
        """Test that different GTINs can be used on different items"""
        item1 = Item.objects.create(
            name="First Item",
            gtin="1234567890123",
            category=self.category
        )
        item2 = Item.objects.create(
            name="Second Item",
            gtin="9876543210987",
            category=self.category
        )
        
        self.assertEqual(item1.gtin, "1234567890123")
        self.assertEqual(item2.gtin, "9876543210987")


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
        """Test that form validation catches duplicate GTIN"""
        from .forms import ItemWithStockForm
        
        # Create an existing item with GTIN
        Item.objects.create(
            name="Existing Item",
            gtin="1234567890123",
            category=self.category,
            subcategory=self.subcategory
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
        self.assertIn('duplicate_gtin', str(form.errors['gtin']))

    def test_form_gtin_validation_unique(self):
        """Test that form validation allows unique GTIN"""
        from .forms import ItemWithStockForm
        
        # Create an existing item with GTIN
        Item.objects.create(
            name="Existing Item",
            gtin="1234567890123",
            category=self.category,
            subcategory=self.subcategory
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
        
        # Create an existing item with GTIN
        Item.objects.create(
            name="Existing Item",
            gtin="1234567890123",
            category=self.category,
            subcategory=self.subcategory
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
