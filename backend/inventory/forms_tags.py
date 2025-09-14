"""
Forms for tag management and tag-based item forms.

This module contains forms specifically for the new tagging system,
including tag group and tag management, as well as updated item forms
that use tags instead of categories.
"""
from django import forms
from django.urls import reverse
from .models import Tag, TagGroup, Organization, StockItem, Item
from inventory import models
from datetime import date
from django.utils import timezone


class TagGroupForm(forms.ModelForm):
    """Form for creating and editing tag groups"""
    
    class Meta:
        model = TagGroup
        fields = ['name', 'description', 'color', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Medical Supplies'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description of this tag group...'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color', 'value': '#6c757d'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
        }
        help_texts = {
            'color': 'Choose a color to visually represent this tag group',
            'sort_order': 'Lower numbers appear first (0 = first, 10 = after groups with sort order 0-9)'
        }


class TagForm(forms.ModelForm):
    """Form for creating and editing individual tags"""
    
    class Meta:
        model = Tag
        fields = ['name', 'tag_group', 'description', 'color', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PPE, Disposable, Electronics'}),
            'tag_group': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description...'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
        }
        help_texts = {
            'color': 'Optional: Override the tag group color for this specific tag',
            'sort_order': 'Order within the tag group (lower numbers appear first)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tag_group'].queryset = TagGroup.objects.filter(is_active=True).order_by('sort_order', 'name')


class TaggedItemForm(forms.ModelForm):
    """Updated item form that uses tags instead of categories"""
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select one or more tags that describe this item"
    )
    
    class Meta:
        model = Item
        fields = ['name', 'manufacturer', 'gtin', 'items_per_box', 'cost_per_item', 'tags', 'url', 'notes_public', 'notes_private']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Samsung, Apple, 3M'}),
            'gtin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1234567890123'}),
            'items_per_box': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'cost_per_item': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'notes_public': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes_private': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Organize tags by tag group for better UX
        active_tags = Tag.objects.filter(
            is_active=True, 
            tag_group__is_active=True
        ).select_related('tag_group').order_by(
            'tag_group__sort_order', 
            'tag_group__name', 
            'sort_order', 
            'name'
        )
        
        self.fields['tags'].queryset = active_tags
        
        # Disable GTIN field if any stock items have GTIN
        if self.instance and self.instance.pk and self.instance.has_stock_item_gtin:
            self.fields['gtin'].disabled = True
            self.fields['gtin'].help_text = "GTIN is disabled because one or more stock items already have GTIN values."

    def save(self, commit=True):
        item = super().save(commit=commit)
        if commit:
            # Handle many-to-many relationship for tags
            self.save_m2m()
        return item


class TaggedItemWithStockForm(forms.Form):
    """Combined form for creating both Item with tags and initial StockItem"""
    
    # Item fields
    name = forms.CharField(max_length=255, label="Item Name", widget=forms.TextInput(attrs={'class': 'form-control'}))
    manufacturer = forms.CharField(
        max_length=255, 
        required=False, 
        label="Manufacturer",
        help_text="Product manufacturer or brand name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Samsung, Apple, 3M'})
    )
    
    # Tags selection
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags",
        help_text="Select one or more tags that describe this item"
    )
    
    # Single GTIN field with toggle
    gtin = forms.CharField(
        required=False, 
        label="GTIN (Global Trade Item Number)",
        help_text="Optional: GTIN-8, GTIN-12, GTIN-13, or GTIN-14 barcode number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1234567890123'})
    )
    gtin_applies_to = forms.ChoiceField(
        choices=[
            ('item', 'Entire Item (only one size/variant)'),
            ('variant', 'This Specific Variant Only'),
        ],
        initial='item',
        widget=forms.RadioSelect,
        label="GTIN applies to",
    )
    
    detail = forms.CharField(
        max_length=255,
        required=False,
        label="Variant Detail (Optional)",
        help_text="Additional details like size, color, variant, etc.",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Size L, Red, 16oz"}),
    )
    url = forms.URLField(required=False, label="URL", widget=forms.URLInput(attrs={'class': 'form-control'}))
    
    # StockItem fields
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label="Received From Organization",
        empty_label="Select an organization",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(min_value=1, initial=1, label="Quantity", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    items_per_box = forms.IntegerField(
        min_value=1,
        required=False,
        label="Items Per Box (Optional)",
        help_text="Number of individual items in a single box/package",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 12'})
    )
    cost_per_item = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label="Value per Qty (Optional)",
        help_text="Value in dollars ($) per individual item",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'placeholder': 'e.g. 10.12'})
    )
    stock_location = forms.CharField(max_length=100, required=True, label="Stock Location", widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date Received"
    )
    expiration_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        label="Expiration Date (optional for non-perishable items)"
    )
    lot_number = forms.CharField(max_length=100, required=False, label="Lot Number", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    stock_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'e.g. Received in good condition, slight box damage'}), 
        required=False, 
        label="Stock Notes",
        help_text="Public Notes specific to this stock entry",
    )
    notes_public = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), 
        required=False, 
        label="Public Item Notes", 
        help_text="Notes visible to all users"
    )
    notes_private = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), 
        required=False, 
        label="Private Item Notes", 
        help_text="Notes visible only to MAI members"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up tags queryset organized by tag group
        active_tags = Tag.objects.filter(
            is_active=True, 
            tag_group__is_active=True
        ).select_related('tag_group').order_by(
            'tag_group__sort_order', 
            'tag_group__name', 
            'sort_order', 
            'name'
        )
        self.fields['tags'].queryset = active_tags
        
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')

    def clean_name(self):
        """Validates that the item name is unique."""
        name = self.cleaned_data['name']
        if models.Item.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                "An item with this name already exists. Please choose a different name.",
                code='duplicate_name'
            )
        return name

    def clean_gtin(self):
        """Validates that the GTIN is unique if provided."""
        gtin = self.cleaned_data.get('gtin', '').strip()

        if gtin:
            if len(gtin) > 14:
                raise forms.ValidationError(
                    "GTIN must be at most 14 characters long.",
                    code='invalid_gtin_length'
                )
            # Check if GTIN exists on any item
            if models.Item.objects.filter(gtin=gtin).exists():
                existing_item = models.Item.objects.filter(gtin=gtin).first()
                raise forms.ValidationError(
                    f"An item with GTIN '{gtin}' already exists: '{existing_item.name}'.",
                    code='duplicate_item_gtin'
                )
            
            # Check if GTIN exists on any stock item
            if models.StockItem.objects.filter(gtin=gtin).exists():
                existing_stock = models.StockItem.objects.filter(gtin=gtin).first()
                raise forms.ValidationError(
                    f"A stock item with GTIN '{gtin}' already exists for item '{existing_stock.item.name}'.",
                    code='duplicate_stock_gtin'
                )
        
        return gtin

    def save(self, commit=True):
        """Create both Item and initial StockItem"""
        data = self.cleaned_data

        # Determine where to place the GTIN based on the toggle
        gtin = data.get('gtin', '').strip()
        gtin_applies_to = data.get('gtin_applies_to', 'item')
        
        item_gtin = gtin if gtin_applies_to == 'item' else ''
        stock_gtin = gtin if gtin_applies_to == 'variant' else ''

        # Create Item with only tags - no legacy category fields
        item = models.Item(
            name=data['name'],
            manufacturer=data['manufacturer'],
            gtin=item_gtin,
            items_per_box=data.get('items_per_box'),
            cost_per_item=data.get('cost_per_item'),
            url=data['url'],
            notes_public=data['notes_public'],
            notes_private=data['notes_private']
        )
        
        if commit:
            item.save()
            
            # Add tags to the item
            selected_tags = data.get('tags', [])
            if selected_tags:
                item.tags.set(selected_tags)
            
            # Create initial StockItem
            stock_item = StockItem(
                item=item,
                organization=data['organization'],
                quantity=data['quantity'],
                location=data['stock_location'],
                gtin=stock_gtin,
                detail=data['detail'],
                date_received=data['date_received'],
                expiration_date=data['expiration_date'],
                lot_number=data['lot_number'],
                notes=data['stock_notes']
            )
            stock_item.save()
            return item, stock_item
        
        return item, None


class TagFilterForm(forms.Form):
    """Form for filtering items by tags in search interfaces"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, manufacturer, or GTIN...'
        }),
        label="Search Items"
    )
    
    tag_groups = forms.ModelMultipleChoiceField(
        queryset=TagGroup.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Filter by Tag Groups"
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Filter by Specific Tags"
    )
    
    exclude_expired = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Exclude expired items"
    )
    
    include_zero_qty = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Include zero quantity items"
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('date_added', 'Date Added'),
            ('name', 'Name'),
            ('manufacturer', 'Manufacturer'),
            ('tags', 'Tags'),
            ('quantity', 'Quantity'),
        ],
        initial='date_added',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Sort By"
    )
    
    sort_order = forms.ChoiceField(
        choices=[
            ('asc', 'Ascending'),
            ('desc', 'Descending'),
        ],
        initial='desc',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Sort Order"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate tag groups and tags
        self.fields['tag_groups'].queryset = TagGroup.objects.filter(
            is_active=True
        ).order_by('sort_order', 'name')
        
        self.fields['tags'].queryset = Tag.objects.filter(
            is_active=True,
            tag_group__is_active=True
        ).select_related('tag_group').order_by(
            'tag_group__sort_order',
            'tag_group__name',
            'sort_order',
            'name'
        )