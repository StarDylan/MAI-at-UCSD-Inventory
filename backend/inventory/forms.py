from django import forms
from django.urls import reverse
from .models import Organization, StockItem
from inventory import models
from allauth.account.forms import LoginForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from datetime import date
from django.utils import timezone


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'description', 'contact_email', 'contact_phone', 'address']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class StockItemForm(forms.ModelForm):
    def clean_date_received(self):
        value = self.cleaned_data.get('date_received')
        if value and (value.year < 1900 or value.year > 3000):
            raise forms.ValidationError('Date received must be between 1900 and 3000.')
        return value

    def clean_expiration_date(self):
        value = self.cleaned_data.get('expiration_date')
        if value and (value.year < 1900 or value.year > 3000):
            raise forms.ValidationError('Expiration date must be between 1900 and 3000.')
        return value
    class Meta:
        model = StockItem
        fields = ['organization', 'quantity', 'location', 'gtin', 'detail', 'date_received', 'expiration_date', 'lot_number', 'notes']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date', 'value': date.today()}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Received in good condition, slight box damage'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')
        self.fields['date_received'].initial = date.today()
        self.fields['notes'].help_text = "Public Notes specific to this stock entry"


class ItemWithLocationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: models.Item):
        # Get all locations from the stock items
        return f"{obj.name} [{obj.aggregated_locations}]"


class StockItemEditForm(forms.ModelForm):
    def clean_date_received(self):
        value = self.cleaned_data.get('date_received')
        if value and (value.year < 1900 or value.year > 3000):
            raise forms.ValidationError('Date received must be between 1900 and 3000.')
        return value

    def clean_expiration_date(self):
        value = self.cleaned_data.get('expiration_date')
        if value and (value.year < 1900 or value.year > 3000):
            raise forms.ValidationError('Expiration date must be between 1900 and 3000.')
        return value
        
    def clean_gtin(self):
        """Validates that the GTIN is unique across items if provided."""
        gtin = self.cleaned_data.get('gtin', '').strip()

        if gtin:
            if len(gtin) > 14:
                raise forms.ValidationError(
                    "GTIN must be at most 14 characters long.",
                    code='invalid_gtin_length'
                )
            
            # Get the current item for this stock item
            current_item = self.instance.item if self.instance and self.instance.pk else None
            
            # Check if GTIN exists on any non-deleted item (except the current item's GTIN)
            existing_item = models.Item.active_objects.filter(gtin=gtin).first()
            if existing_item and current_item and existing_item.id != current_item.id:
                raise forms.ValidationError(
                    f"An item with GTIN '{gtin}' already exists: '{existing_item.name}'. GTINs must be unique across items.",
                    code='duplicate_item_gtin'
                )
            
            # Check if GTIN exists on stock items belonging to OTHER non-deleted items
            stock_filter = models.StockItem.objects.filter(gtin=gtin, item__is_deleted=False)
            if self.instance and self.instance.pk:
                stock_filter = stock_filter.exclude(pk=self.instance.pk)
            
            if current_item:
                stock_filter = stock_filter.exclude(item=current_item)
            
            existing_stock = stock_filter.first()
            if existing_stock:
                raise forms.ValidationError(
                    f"A stock item with GTIN '{gtin}' already exists for a different item: '{existing_stock.item.name}'. GTINs must be unique across items.",
                    code='duplicate_cross_item_gtin'
                )
        
        return gtin
        
    """Form for editing individual stock items"""
    class Meta:
        model = StockItem
        fields = ['organization', 'quantity', 'location', 'gtin', 'detail', 'date_received', 'expiration_date', 'lot_number', 'notes']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Received in good condition, slight box damage'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')
        self.fields['notes'].help_text = "Public Notes specific to this stock entry"
        
        # Disable GTIN field if the item has a GTIN
        if self.instance and self.instance.pk and self.instance.item.gtin:
            self.fields['gtin'].disabled = True
            self.fields['gtin'].help_text = "GTIN is disabled because the item already has a GTIN value."
        
        # Set up crispy form helper to ensure field errors are displayed properly
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Layout, Field
        
        self.helper = FormHelper()
        self.helper.form_tag = False  # Don't render a form tag
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        
        # Create a layout with each field explicitly defined
        self.helper.layout = Layout(
            Field('organization'),
            Field('quantity'),
            Field('location'),
            Field('gtin', wrapper_class='field-with-errors'),  # Add a special class for GTIN field
            Field('detail'),
            Field('date_received'),
            Field('expiration_date'),
            Field('lot_number'),
            Field('notes'),
        )


class Search_QuantityAdd(forms.Form):
    def clean_date_received(self):
        value = self.cleaned_data.get('date_received')
        if value and (value.year < 1900 or value.year > 3000):
            raise forms.ValidationError('Date received must be between 1900 and 3000.')
        return value

    def clean_expiration_date(self):
        value = self.cleaned_data.get('expiration_date')
        if value and (value.year < 1900 or value.year > 3000):
            raise forms.ValidationError('Expiration date must be between 1900 and 3000.')
        return value

    def clean_gtin(self):
        """Validates that the GTIN is unique across items if provided."""
        gtin = self.cleaned_data.get('gtin', '').strip()

        if gtin:
            if len(gtin) > 14:
                raise forms.ValidationError(
                    "GTIN must be at most 14 characters long.",
                    code='invalid_gtin_length'
                )
            
            # Get the selected item for this check-in
            selected_item = self.cleaned_data.get('item')
            
            # Check if GTIN exists on any OTHER non-deleted item (not the current one)
            existing_item = models.Item.active_objects.filter(gtin=gtin).first()
            if existing_item and existing_item != selected_item:
                raise forms.ValidationError(
                    f"An item with GTIN '{gtin}' already exists: '{existing_item.name}'. GTINs must be unique across items.",
                    code='duplicate_item_gtin'
                )
            
            # Check if GTIN exists on stock items belonging to OTHER non-deleted items
            stock_filter = models.StockItem.objects.filter(gtin=gtin, item__is_deleted=False)
            if selected_item:
                stock_filter = stock_filter.exclude(item=selected_item)
            
            existing_stock = stock_filter.first()
            if existing_stock:
                raise forms.ValidationError(
                    f"A stock item with GTIN '{gtin}' already exists for a different item: '{existing_stock.item.name}'. GTINs must be unique across items.",
                    code='duplicate_cross_item_gtin'
                )
        
        return gtin

    """Form for adding new stock (check-in) - creates new StockItem"""
    item = forms.ModelChoiceField(
        queryset=models.Item.active_objects.none(),  # Start with empty queryset for performance
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Search and select an item..."
    )
    detail = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Size L, Red, 16oz"}),
        label="Detail",
        help_text="Additional details like size, color, variant, etc."
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all().order_by('name'),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Received From Organization",
        empty_label="Select an organization"
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Quantity to add",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 12"})
    )
    gtin = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 1234567890123"}),
        label="GTIN (Global Trade Item Number)",
        help_text="Optional: GTIN-8, GTIN-12, GTIN-13, or GTIN-14 barcode number"
    )
    location = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Box A"}),
        label="Stock Location"
    )
    date_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date Received"
    )
    expiration_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        label="Expiration Date (optional)"
    )
    lot_number = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. LOT2024001"}),
        label="Lot Number"
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'e.g. Received in good condition, slight box damage'}), 
        required=False, 
        label="Notes",
        help_text="Public Notes specific to this stock entry"
    )

    def __init__(self, *args, **kwargs):
        # Check if a specific item is pre-selected (from URL)
        initial_item = kwargs.pop('initial_item', None)
        super().__init__(*args, **kwargs)

        # If POST, ensure the selected item is in the queryset so validation passes
        data = self.data or getattr(self, 'data', None)
        item_id = None
        if data and 'item' in data:
            item_id = data.get('item')
        elif self.initial.get('item'):
            item_id = self.initial['item'].id
        elif initial_item:
            item_id = initial_item.id

        if item_id:
            self.fields['item'].queryset = models.Item.active_objects.filter(id=item_id)
            # Disable GTIN field if the selected item has a GTIN
            try:
                item_obj = models.Item.active_objects.get(id=item_id)
                if item_obj.gtin:
                    self.fields['gtin'].disabled = True
                    self.fields['gtin'].help_text = "GTIN is disabled because the item already has a GTIN value."
            except models.Item.DoesNotExist:
                pass
        else:
            # For the search interface, we'll populate this via AJAX
            self.fields['item'].queryset = models.Item.active_objects.none()


class Search_QuantityRemove(forms.Form):
    """Form for removing stock (check-out) - allows selection of specific stock items"""
    item = ItemWithLocationChoiceField(
        queryset=models.Item.active_objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # We'll add stock item selection fields dynamically via JavaScript


class StockItemCheckoutForm(forms.Form):
    """Form for checking out from specific stock items"""
    stock_items = forms.ModelMultipleChoiceField(
        queryset=StockItem.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Select stock items to check out from"
    )
    quantities = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="JSON string of quantities for each stock item"
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'e.g. Received in good condition, slight box damage'}), 
        required=False, 
        label="Checkout Notes",
        help_text="Public Notes specific to this checkout"
    )
    
    def __init__(self, item=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if item:
            self.fields['stock_items'].queryset = item.stock_items.filter(quantity__gt=0).order_by('detail', 'expiration_date', 'date_received')

class CheckOutForm(forms.ModelForm):
    """Form for creating and editing bulk checkouts"""
    
    class Meta:
        model = models.CheckOut
        fields = ['organization', 'is_donation', 'notes']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'is_donation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional notes for this checkout...'}),
        }
        labels = {
            'is_donation': 'This is a donation',
        }
        help_texts = {
            'is_donation': 'Uncheck this box for internal transfers, sales, or other non-donation transactions',
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')


class CheckOutItemForm(forms.ModelForm):
    """Form for adding/editing individual items in a checkout"""
    
    class Meta:
        model = models.CheckOutItem
        fields = ['quantity', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional notes for this line item...'}),
        }
        
    def __init__(self, stock_item=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if stock_item:
            # Set max quantity based on available stock
            self.fields['quantity'].widget.attrs['max'] = stock_item.quantity
            self.fields['quantity'].help_text = f"Max available: {stock_item.quantity}"


class CheckOutCompleteForm(forms.Form):
    """Form for completing a checkout"""
    total_weight = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,  # Will be validated conditionally
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
        label="Total Weight (lbs)",
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional completion notes...'}),
        required=False,
        label="Completion Notes",
        help_text="Additional notes about the checkout completion"
    )
    
    def __init__(self, *args, checkout=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkout = checkout
        
        # If this is a donation, weight is required
        if checkout and checkout.is_donation:
            self.fields['total_weight'].required = True
            self.fields['total_weight'].help_text = "Weight is required for donations"
        else:
            self.fields['total_weight'].help_text = "Weight is optional for non-donations"
    
    def clean_total_weight(self):
        total_weight = self.cleaned_data.get('total_weight')
        
        # If this is a donation checkout, weight is required
        if self.checkout and self.checkout.is_donation and not total_weight:
            raise forms.ValidationError("Total weight is required for donation checkouts")
            
        return total_weight


class CheckOutItemEditForm(forms.ModelForm):
    """Form for editing quantity in a checkout item"""
    
    class Meta:
        model = models.CheckOutItem
        fields = ['quantity', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'style': 'width: 80px; display: inline;'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional notes for this line item...'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.stock_item:
            # Set max quantity based on available stock + current quantity
            max_qty = self.instance.stock_item.quantity + self.instance.quantity
            self.fields['quantity'].widget.attrs['max'] = max_qty
            self.fields['quantity'].help_text = f"Max available: {max_qty}"


class CheckOutItemDetailEditForm(forms.Form):
    """Form for editing both checkout item quantity and item cost in a dedicated page"""
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    cost_per_item = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'placeholder': '0.00'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes for this checkout item'})
    )
    
    def __init__(self, *args, checkout_item=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkout_item = checkout_item
        
        if checkout_item:
            # Set initial values
            self.fields['quantity'].initial = checkout_item.quantity
            self.fields['cost_per_item'].initial = checkout_item.stock_item.item.cost_per_item
            self.fields['notes'].initial = checkout_item.notes
            
            # Set max quantity based on available stock + current quantity
            max_qty = checkout_item.stock_item.quantity + checkout_item.quantity
            self.fields['quantity'].widget.attrs['max'] = max_qty
            self.fields['quantity'].help_text = f"Max available: {max_qty} units (includes current checkout quantity)"
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.checkout_item:
            # Check against available stock + current checkout quantity
            max_qty = self.checkout_item.stock_item.quantity + self.checkout_item.quantity
            if quantity > max_qty:
                raise forms.ValidationError(f"Only {max_qty} units available")
        return quantity


class StockItemSelectWidget(forms.Select):
    """Custom widget for stock item selection that includes data attributes for quantity and location"""
    
    def __init__(self, stock_items=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock_items = stock_items or []
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        if value and str(value) != '':
            # Find the matching stock item from our stored list
            for stock_item in self.stock_items:
                if str(stock_item.id) == str(value):
                    option['attrs']['data-quantity'] = stock_item.quantity
                    option['attrs']['data-location'] = stock_item.location or ''
                    option['attrs']['data-detail'] = stock_item.detail or ''
                    break
                
        return option


class AddToCheckOutForm(forms.Form):
    """Form for adding items to an existing checkout from item detail page"""
    checkout = forms.ModelChoiceField(
        queryset=models.CheckOut.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Add to Checkout",
        help_text="Select an active checkout to add items to"
    )
    stock_item = forms.ModelChoiceField(
        queryset=models.StockItem.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Stock Item"
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        label="Quantity",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label="Notes",
        help_text="Optional notes for this checkout item"
    )
    
    def __init__(self, *args, **kwargs):
        item = kwargs.pop('item', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Store item reference for validation
        self._item = item
        
        if user:
            # Only show active checkouts
            self.fields['checkout'].queryset = models.CheckOut.objects.filter(
                is_completed=False
            ).order_by('-created_at')
        if item:
            # Populate stock items for this item with available quantity
            # Include all stock items regardless of surplus status
            stock_items = item.stock_items.filter(
                quantity__gt=0
            ).order_by('detail', 'expiration_date', 'date_received')
            
            self.fields['stock_item'].queryset = stock_items
            
    def clean(self):
        cleaned_data = super().clean()
        stock_item = cleaned_data.get('stock_item')
        quantity = cleaned_data.get('quantity')
        checkout = cleaned_data.get('checkout')
        
        if stock_item and quantity:
            # Check if enough quantity is available
            if quantity > stock_item.quantity:
                raise forms.ValidationError(
                    f"Only {stock_item.quantity} units available for {stock_item}"
                )
                
            # Check if this stock item is already in the checkout
            if checkout and models.CheckOutItem.objects.filter(
                checkout=checkout, 
                stock_item=stock_item
            ).exists():
                raise forms.ValidationError(
                    "This stock item is already in the selected checkout"
                )
        
        return cleaned_data


class UserCreationForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)


class UserEditForm(forms.ModelForm):
    """Form for editing user profile information"""
    
    class Meta:
        model = models.User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'})
        }
        help_texts = {
            'username': 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
            'user_picture': 'Optional URL to a profile picture image.',
        }
        
    def __init__(self, *args, **kwargs):
        self.user_being_edited = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        
    def clean_username(self):
        username = self.cleaned_data['username']
        
        # Check if username already exists (but allow the current user to keep their username)
        if models.User.objects.filter(username=username).exclude(pk=self.user_being_edited.pk if self.user_being_edited else None).exists():
            raise forms.ValidationError('A user with that username already exists.')
            
        return username
        
    def clean_email(self):
        email = self.cleaned_data['email']
        
        # Check if email already exists (but allow the current user to keep their email)
        if models.User.objects.filter(email=email).exclude(pk=self.user_being_edited.pk if self.user_being_edited else None).exists():
            raise forms.ValidationError('A user with that email already exists.')
            
        return email
    
class CrispyLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Log In'))