from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.db import OperationalError
from django.utils.html import format_html
from . import models

admin.site.site_header = "MAI Admin"
admin.site.site_title = "MAI Admin"
admin.site.index_title = "Administration"
admin.site.empty_value_display = "—"


# ---------- Shared actions for soft-delete models ----------

@admin.action(description="Mark selected as deleted")
def mark_deleted(modeladmin, request, queryset):
    queryset.update(is_deleted=True)

@admin.action(description="Restore selected (clear deleted)")
def restore_deleted(modeladmin, request, queryset):
    queryset.update(is_deleted=False)


# ---------- Inlines ----------

class ItemImageInline(admin.TabularInline):
    model = models.Image
    extra = 0
    show_change_link = True


class StockItemInline(admin.TabularInline):
    model = models.StockItem
    extra = 0
    show_change_link = True
    fields = ("organization", "quantity", "date_received", "expiration_date", "lot_number", "is_active")


# ---------- Core data models ----------

@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("id", "name")
    ordering = ("name",)
    actions = (mark_deleted, restore_deleted)
    list_per_page = 25


@admin.register(models.Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category")
    list_filter = ("category",)
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
        "total_stock_display",
        "is_deleted",
        "url_link",
    )
    list_filter = ("is_deleted", "category", "subcategory")
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
    inlines = [ItemImageInline, StockItemInline]
    list_per_page = 25

    @admin.display(description="URL")
    def url_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">Open</a>', obj.url)
        return ""
    
    @admin.display(description="Stock Items Total")
    def total_stock_display(self, obj):
        return obj.total_stock_quantity


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "image_url", "public_id")
    search_fields = ("id", "image_url", "item__name", "item__id")
    list_select_related = ("item",)
    autocomplete_fields = ("item",)
    ordering = ("item__name",)
    list_per_page = 25


@admin.register(models.Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact_email", "contact_phone")
    search_fields = ("id", "name", "description", "contact_email")
    ordering = ("name",)
    list_per_page = 25


@admin.register(models.StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "organization", 
        "quantity",
        "date_received",
        "expiration_date",
        "is_active",
        "is_expired_display",
    )
    list_filter = ("is_active", "organization", "date_received", "expiration_date")
    search_fields = (
        "id",
        "item__name",
        "organization__name",
        "lot_number",
        "notes",
    )
    ordering = ("-date_received",)
    autocomplete_fields = ("item", "organization")
    list_per_page = 25
    
    @admin.display(description="Expired", boolean=True)
    def is_expired_display(self, obj):
        return obj.is_expired


@admin.register(models.User)
class MyUserAdmin(UserAdmin):
    model = models.User

    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('user_picture',)}),
    )


# A helper function to get the 'Normal' group, which we will use as a callable
def get_normal_group():
    """Returns the 'Normal' group object, or None if the table doesn't exist yet."""
    try:
        return Group.objects.get(name='Normal')
    except (Group.DoesNotExist, OperationalError):
        # This will happen during the makemigrations command, so we return None
        return None

# Define a custom form for creating a new user in the admin
class CustomUserCreationForm(UserCreationForm):
    # This field will list the groups you want to show
    group = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=['Admin', 'Normal']),
        label='User Group',
        # Use our helper function as a callable for the initial value
        # This defers the database query until the form is instantiated
        initial=get_normal_group,
        help_text='Select the user\'s group.',
        empty_label=None # Don't show a blank option
    )

    class Meta(UserCreationForm.Meta):
        # We need to explicitly define the fields from the base form
        # and add our custom 'group' field
        fields = ('username',)

# Define our custom UserAdmin class
class CustomUserAdmin(UserAdmin):
    # Use our custom form for the user creation page
    add_form = CustomUserCreationForm

    # Hide the default 'Groups' and 'User permissions' fields
    # so we can use our custom 'group' field
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    # Add the custom 'group' field to the list of fields displayed in the add_form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'group'), # Add our custom field here
        }),
    )

    def save_model(self, request, obj, form, change):
        # This method is called when a user is saved via the admin
        super().save_model(request, obj, form, change)
        if not change: # Only on creation of a new user
            group = form.cleaned_data['group']
            obj.groups.add(group)

# Unregister the default UserAdmin and register our custom one
admin.site.register(User, CustomUserAdmin)

@admin.register(models.AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "entity_type", "entity_id", "event", "user_id")
    list_filter = ("entity_type",)
    search_fields = ("entity_type", "entity_id", "event", "user_id", "before", "after")
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
