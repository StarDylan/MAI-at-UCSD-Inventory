from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from . import models

admin.site.site_header = "MAI Admin"
admin.site.site_title = "MAI Admin"
admin.site.index_title = "Administration"
admin.site.empty_value_display = "—"


# ---------- Shared actions for soft-delete models ----------

@admin.action(description="Mark selected as deleted")
def mark_deleted(modeladmin, request, queryset):
    queryset.update(deleted=True)

@admin.action(description="Restore selected (clear deleted)")
def restore_deleted(modeladmin, request, queryset):
    queryset.update(deleted=False)


# ---------- Inlines ----------

class ItemImageInline(admin.TabularInline):
    model = models.Image
    extra = 0
    fields = ("image_url", "deletion_hash")
    show_change_link = True


# ---------- Core data models ----------

@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "deleted")
    list_filter = ("deleted",)
    search_fields = ("id", "name")
    ordering = ("name",)
    actions = (mark_deleted, restore_deleted)
    list_per_page = 25


@admin.register(models.Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "deleted")
    list_filter = ("deleted", "category")
    search_fields = ("id", "name", "category__name")
    ordering = ("category__name", "name")
    autocomplete_fields = ("category",)
    actions = (mark_deleted, restore_deleted)
    list_per_page = 25


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "subcategory",
        "location",
        "quantity_active",
        "deleted",
        "url_link",
    )
    list_filter = ("deleted", "category", "subcategory")
    search_fields = (
        "id",
        "name",
        "location",
        "url",
        "notes_public",
        "notes_private",
        "category__name",
        "subcategory__name",
    )
    ordering = ("name",)
    autocomplete_fields = ("category", "subcategory")
    inlines = [ItemImageInline]
    list_per_page = 25

    @admin.display(description="URL")
    def url_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">Open</a>', obj.url)
        return ""


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "image_url", "deletion_hash")
    search_fields = ("id", "image_url", "item__name", "item__id")
    list_select_related = ("item",)
    autocomplete_fields = ("item",)
    ordering = ("item__name",)
    list_per_page = 25


@admin.register(models.User)
class MyUserAdmin(UserAdmin):
    model = models.User

    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('user_picture',)}),
    )

@admin.register(models.AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "entity_type", "entity_id", "event", "user_label")
    list_filter = ("entity_type",)
    search_fields = ("entity_type", "entity_id", "event", "user_label", "before", "after")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50

    # Make audit log read-only in admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------- Log DB models ----------

class _ReadOnlyAdmin(admin.ModelAdmin):
    """Base admin to present read-only log tables."""
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(models.ErrorLog)
class ErrorLogAdmin(_ReadOnlyAdmin):
    list_display = ("date", "source", "log_level_name", "message_short", "module", "function_name", "line_num")
    list_filter = ("log_level_name", "source", "module")
    search_fields = ("message", "module", "function_name", "source", "exception", "thread_name")
    date_hierarchy = "date"
    ordering = ("-date",)
    list_per_page = 50

    @admin.display(description="Message")
    def message_short(self, obj):
        return (obj.message or "")[:120] + ("…" if obj.message and len(obj.message) > 120 else "")


@admin.register(models.AccessLog)
class AccessLogAdmin(_ReadOnlyAdmin):
    list_display = ("date", "source", "log_level_name", "message_short", "module", "function_name", "line_num")
    list_filter = ("log_level_name", "source", "module")
    search_fields = ("message", "module", "function_name", "source", "thread_name")
    date_hierarchy = "date"
    ordering = ("-date",)
    list_per_page = 50

    @admin.display(description="Message")
    def message_short(self, obj):
        return (obj.message or "")[:120] + ("…" if obj.message and len(obj.message) > 120 else "")


@admin.register(models.LatencyLog)
class LatencyLogAdmin(_ReadOnlyAdmin):
    list_display = ("date", "path", "time")
    search_fields = ("path",)
    date_hierarchy = "date"
    ordering = ("-date", "-time")
    list_per_page = 50
