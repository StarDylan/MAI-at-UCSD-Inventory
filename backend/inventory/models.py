from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=100)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "category"

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
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "subcategory"

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

    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "item"

    def __str__(self):
        return self.name

class User(AbstractUser):
    user_picture = models.URLField(default="/static/mai_logo.png")

    def __str__(self):
        return f"{self.username} <{self.email}>"

class Image(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    image_url = models.URLField()
    deletion_hash = models.CharField(max_length=255, blank=True, null=True)
    item = models.ForeignKey(
        Item, related_name="images", on_delete=models.CASCADE, db_column="item_id"
    )

    class Meta:
        db_table = "image"

    def __str__(self):
        return self.image_url


class AuditEvent(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    created_at = models.DateTimeField(db_column="date", editable=False)
    entity_type = models.CharField(max_length=50, db_column="type", editable=False)
    entity_id = models.UUIDField(default=uuid.uuid4, editable=False)
    user_label = models.CharField(max_length=255, db_column="user", editable=False)
    event = models.CharField(max_length=255, editable=False)
    before = models.TextField(blank=True, default="", editable=False)
    after = models.TextField(blank=True, default="", editable=False)

    class Meta:
        db_table = "audit"
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
