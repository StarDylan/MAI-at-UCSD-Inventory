from django.contrib.auth.models import AbstractUser
from django.db.models.functions import Lower
from django.db import models
import uuid

from inventory.managers import ActiveManager

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "category"

        constraints = [
            models.UniqueConstraint(fields=['name'], name='unique_active_category_name')
        ]

    def __str__(self):
        return self.name

class Subcategory(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    category = models.ForeignKey(
        Category,
        related_name="subcategories",
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'category'], name='unique_active_subcategory_name')
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Organization(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_organization_name')
        ]
    
    def __str__(self):
        return self.name


class Item(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    category = models.ForeignKey(
        Category,
        related_name="items",
        on_delete=models.PROTECT,
        db_column="category_id",
    )
    subcategory = models.ForeignKey(
        Subcategory,
        related_name="items",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="subcategory_id",
    )

    name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255, blank=True, default="", help_text="Product manufacturer or brand name")
    gtin = models.CharField(max_length=14, blank=True, default="", help_text="Global Trade Item Number (GTIN-8, GTIN-12, GTIN-13, or GTIN-14)")
    items_per_box = models.PositiveIntegerField(null=True, blank=True, help_text="Number of individual items in a single box/package")
    cost_per_item = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        null=True, 
        blank=True,
        help_text="Cost per individual item"
    )
    notes_public = models.TextField(blank=True, default="")
    notes_private = models.TextField(blank=True, default="")
    url = models.URLField(blank=True)

    is_deleted = models.BooleanField(default=False)

    objects = models.Manager()  # The default manager.

    # All `Post.active_objects` queries will now
    # automatically exclude deleted posts.
    active_objects = ActiveManager()
    
    class Meta:
        permissions = [
            ("view_deleteditem", "Can view deleted items"),
            ("restore_deleteditem", "Can restore deleted items"),
            ("view_internalstockingdetails", "Can view internal stocking"),
            ("view_advancedpropertiesitem", "Can view advanced properties"),
        ]
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_item_name'),
            models.UniqueConstraint(
                fields=['gtin'], 
                condition=models.Q(gtin__gt=''),
                name='unique_item_gtin'
            )
        ]

    def __str__(self):
        return self.name
    
    @property
    def total_stock_quantity(self):
        """Calculate total quantity from all active stock items"""
        return sum(stock.quantity for stock in self.stock_items.filter(quantity__gt=0))

    @property
    def aggregated_locations(self):
        """Get comma-separated list of unique locations from active stock items"""
        locations = self.stock_items.filter(quantity__gt=0).exclude(location='').values_list('location', flat=True).distinct()
        return ', '.join(sorted(locations)) if locations else ""
    
    @property
    def has_stock_item_gtin(self):
        """Check if any stock items have a GTIN"""
        return self.stock_items.filter(gtin__gt='').exists()
    
    def get_gtins(self):
        """Get list of all GTINs associated with this item"""
        gtins = []
        
        # Add item GTIN if it exists
        if self.gtin:
            gtins.append(self.gtin)
        
        # Add stock item GTINs
        stock_gtins = self.stock_items.filter(gtin__gt='').values_list('gtin', flat=True).distinct()
        gtins.extend(stock_gtins)
        
        return gtins


class StockItem(models.Model):
    SURPLUS_STATUS_CHOICES = [
        ('pending', 'Surplus Needs to Check'),
        ('wanted', 'Wanted by Surplus'),
        ('not_wanted', 'Not Wanted by Surplus'),
    ]
    
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    item = models.ForeignKey(
        Item,
        related_name="stock_items",
        on_delete=models.CASCADE,
        db_column="item_id",
    )
    organization = models.ForeignKey(
        Organization,
        related_name="stock_items",
        on_delete=models.PROTECT,
        db_column="organization_id",
    )
    quantity = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=100, blank=False, help_text="Specific location where this stock is stored")
    gtin = models.CharField(max_length=14, blank=True, default="", help_text="Global Trade Item Number (GTIN-8, GTIN-12, GTIN-13, or GTIN-14)")
    detail = models.CharField(max_length=255, blank=True, default="", help_text="Additional details like size, color, variant, etc.")
    date_received = models.DateField()
    expiration_date = models.DateField(null=True, blank=True, help_text="Leave blank for non-perishable items")
    lot_number = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    surplus_status = models.CharField(
        max_length=20,
        choices=SURPLUS_STATUS_CHOICES,
        default='pending',
        help_text="Surplus approval status for this stock item"
    )

    class Meta:
        ordering = ['detail', 'expiration_date', 'date_received']
        permissions = [
            ("view_surplus_report", "Can view surplus reports"),
            ("download_surplus_report", "Can download surplus reports"),
            ("upload_surplus_report", "Can upload surplus reports"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['gtin'], 
                condition=models.Q(gtin__gt=''),
                name='unique_stockitem_gtin'
            )
        ]

    
    def __str__(self):
        detail_str = f" - {self.detail}" if self.detail else ""
        return f"{self.item.name}{detail_str} - {self.quantity} units from {self.location}"
    
    @property
    def is_expired(self):
        """Check if this stock item has expired"""
        if not self.expiration_date:
            return False
        from django.utils import timezone
        return self.expiration_date < timezone.now().date()
    
    @property
    def surplus_status_display(self):
        """Get human-readable surplus status"""
        return dict(self.SURPLUS_STATUS_CHOICES)[self.surplus_status]
    
    @property
    def is_surplus_approved(self):
        """Check if this stock item is approved by surplus (not pending)"""
        return self.surplus_status != 'pending'


class User(AbstractUser):
    user_picture = models.CharField(max_length=255, default="/static/inventory/original_logo_square.png")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['username'], name='unique_user_username'),
            models.UniqueConstraint(fields=['email'], name='unique_user_email'),
        ]

        permissions = [
            ("restore_user", "Can restore user")
        ]

    def __str__(self):
        # If first and last name are not defined, than show username and email
        if not self.first_name and not self.last_name:
            return f"{self.username} <{self.email}>"
        return f"{self.first_name} {self.last_name}"

class Image(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    image_url = models.URLField()
    public_id = models.CharField(max_length=255, blank=True, null=True)
    item = models.ForeignKey(
        Item, related_name="images", on_delete=models.CASCADE, db_column="item_id"
    )

    def __str__(self):
        return self.image_url


class CheckOut(models.Model):
    """
    Bulk checkout system - represents a collection of items being checked out.
    Can be in 'active' state (being built) or 'completed' state (finalized).
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    organization = models.ForeignKey(
        Organization,
        related_name="checkouts",
        on_delete=models.PROTECT,
        db_column="organization_id",
        help_text="Organization that items are being checked out to"
    )
    created_by = models.ForeignKey(
        User,
        related_name="created_checkouts",
        on_delete=models.PROTECT,
        db_column="created_by_id"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    completed_by = models.ForeignKey(
        User,
        related_name="completed_checkouts",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="completed_by_id"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    
    total_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Total weight of all items in the checkout (filled at completion)"
    )
    notes = models.TextField(blank=True, default="", help_text="Additional notes for this checkout")
    is_completed = models.BooleanField(default=False)
    is_donation = models.BooleanField(
        default=True, 
        help_text="Whether this checkout represents a donation (unchecked for internal transfers, sales, etc.)"
    )
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("complete_checkout", "Can complete checkout"),
            ("undo_checkout", "Can undo completed checkout"),
        ]
        
    def __str__(self):
        status = "Completed" if self.is_completed else "Active"
        donation_type = "Donation" if self.is_donation else "Non-Donation"
        return f"{status} {donation_type.lower()} checkout for {self.organization.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_items_count(self):
        """Calculate total number of individual items in this checkout"""
        return sum(item.quantity for item in self.checkout_items.all())
    
    @property
    def total_cost(self):
        """Calculate total cost of all items in checkout"""
        total = 0
        for checkout_item in self.checkout_items.all():
            if checkout_item.stock_item.item.cost_per_item:
                total += checkout_item.stock_item.item.cost_per_item * checkout_item.quantity
        return total
    
    @property
    def has_insufficient_stock(self):
        """Check if any items in the checkout have insufficient stock"""
        return any(item.remaining_after_checkout < 0 for item in self.checkout_items.all())
    
    @property
    def donation_type_display(self):
        """Get human-readable donation type"""
        return "Donation" if self.is_donation else "Non-Donation"
    

class CheckOutItem(models.Model):
    """
    Individual line item in a checkout - links specific stock items with quantities and costs.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    checkout = models.ForeignKey(
        CheckOut,
        related_name="checkout_items",
        on_delete=models.CASCADE,
        db_column="checkout_id"
    )
    stock_item = models.ForeignKey(
        StockItem,
        related_name="checkout_items",
        on_delete=models.PROTECT,
        db_column="stock_item_id"
    )
    quantity = models.PositiveIntegerField(help_text="Quantity to check out from this stock item")
    notes = models.TextField(blank=True, default="", help_text="Notes specific to this line item")
    
    class Meta:
        ordering = ['stock_item__item__name', 'stock_item__detail']
        constraints = [
            # Prevent duplicate stock items in the same checkout
            models.UniqueConstraint(fields=['checkout', 'stock_item'], name='unique_checkout_stock_item')
        ]
    
    def __str__(self):
        return f"{self.quantity}x {self.stock_item.item.name} from {self.stock_item.location}"
    
    @property
    def total_cost(self):
        """Calculate total cost for this line item"""
        if self.stock_item.item.cost_per_item:
            return self.stock_item.item.cost_per_item * self.quantity
        return None
    
    @property 
    def remaining_after_checkout(self):
        """Calculate remaining stock after this checkout item"""
        return self.stock_item.quantity - self.quantity


class AuditEvent(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, editable=False)
    entity_type = models.CharField(max_length=50, db_column="type", editable=False)
    entity_id = models.UUIDField(editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, editable=False)
    event = models.CharField(max_length=255, editable=False)
    before = models.TextField(blank=True, default="", editable=False)
    after = models.TextField(blank=True, default="", editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["entity_type", "id", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.created_at}] {self.entity_type}:{self.id} {self.event}"


# -----------------------
# LOG DB MODELS
# -----------------------
# If you keep logs in a separate SQLite file (mai-log.db), you can place these in a
# separate Django app and route them to a different DATABASES alias via a database router.

class ErrorLog(models.Model):
    date = models.DateTimeField()
    source = models.CharField(max_length=255)
    log_level = models.IntegerField()
    log_level_name = models.CharField(max_length=50)
    message = models.TextField()
    args = models.TextField(blank=True, default="")
    module = models.CharField(max_length=255, blank=True, default="")
    function_name = models.CharField(max_length=255, blank=True, default="")
    line_num = models.IntegerField(null=True, blank=True)
    exception = models.TextField(blank=True, default="")
    process = models.IntegerField(null=True, blank=True)
    thread = models.CharField(max_length=255, blank=True, default="")
    thread_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "error_log"


class AccessLog(models.Model):
    date = models.DateTimeField()
    source = models.CharField(max_length=255)
    log_level = models.IntegerField()
    log_level_name = models.CharField(max_length=50)
    message = models.TextField()
    args = models.TextField(blank=True, default="")
    module = models.CharField(max_length=255, blank=True, default="")
    function_name = models.CharField(max_length=255, blank=True, default="")
    line_num = models.IntegerField(null=True, blank=True)
    exception = models.TextField(blank=True, default="")
    process = models.IntegerField(null=True, blank=True)
    thread = models.CharField(max_length=255, blank=True, default="")
    thread_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "access_log"


class LatencyLog(models.Model):
    date = models.DateTimeField()
    path = models.CharField(max_length=512)
    time = models.IntegerField(help_text="Latency in milliseconds")

    class Meta:
        db_table = "latency_log"
