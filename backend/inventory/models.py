from django.contrib.auth.models import AbstractUser
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
    location = models.CharField(max_length=100, blank=True, default="")
    quantity_active = models.PositiveIntegerField(default=0)
    
    notes_public = models.TextField(blank=True, default="")
    notes_private = models.TextField(blank=True, default="")
    url = models.URLField(blank=True)

    is_deleted = models.BooleanField(default=False)
    
    # All `Post.objects` queries will now
    # automatically exclude deleted posts.
    active_objects = ActiveManager()
    
    class Meta:
        permissions = [
            ("view_deleteditem", "Can view deleted items"),
            ("restore_deleteditem", "Can restore deleted items"),
            ("view_internalstockingdetails", "Can view internal stocking"),
            ("view_advancedpropertiesitem", "Can view advanced properties"),
        ]

    def __str__(self):
        return self.name

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
