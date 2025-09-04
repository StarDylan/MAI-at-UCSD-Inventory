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
            date_received=date.today()
        )
        StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=5,
            date_received=date.today()
        )
        StockItem.objects.create(
            item=self.item,
            organization=self.organization,
            quantity=0,  # This should not be counted (inactive)
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
            date_received=date.today()
        )
        expected_str = f"{self.item.name} - 7 units from {self.organization.name}"
        self.assertEqual(str(stock), expected_str)


# Create your other tests here.
