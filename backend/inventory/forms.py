import datetime
from django import forms
from .models import Category, Subcategory, Organization, StockItem
from inventory import models
from allauth.account.forms import LoginForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from datetime import date


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

class ItemForm(forms.ModelForm):
    # This field will be the one the user sees and interacts with.
    # It will display subcategories grouped by their categories.
    subcategory = forms.ModelChoiceField(
        queryset=models.Subcategory.objects.all(),
        label="Category"
    )

    class Meta:
        model = models.Item
        # Use StockItem for quantity tracking instead of quantity_active
        fields = ['name', 'subcategory', "url", 'notes_public', 'notes_private']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get all subcategories and their parent categories
        subcategories = models.Subcategory.objects.select_related('category').all().order_by('category__name', 'name')
        
        # Create a list of tuples for grouped choices
        grouped_choices = []
        current_category = None
        category_group = []

        for subcategory in subcategories:
            if current_category and subcategory.category != current_category:
                # Add the previous category's group to the main list
                grouped_choices.append((current_category.name, category_group))
                category_group = []
            
            # Add the subcategory to the current group
            category_group.append((subcategory.pk, subcategory.name))
            current_category = subcategory.category

        # Add the last category's group
        if category_group:
            assert current_category is not None  # For type checker, we always assign a category and subcategory
            grouped_choices.append((current_category.name, category_group))

        # Set the choices for the subcategory field
        self.fields['subcategory'].choices = grouped_choices

    def save(self, commit=True):
        # Call the parent save method to get the Item instance
        item = super().save(commit=False)
        
        # Get the selected subcategory object from the form data
        selected_subcategory = self.cleaned_data['subcategory']
        
        # Set the category field of the Item instance based on the subcategory
        item.category = selected_subcategory.category
        item.subcategory = selected_subcategory
        
        if commit:
            item.save()
        
        return item

class SubcategoryForm(forms.ModelForm):
    name = forms.CharField(max_length=100, label="Subcategory Name")
    class Meta:
        model = Subcategory
        fields = ['category', 'name']


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'description', 'contact_email', 'contact_phone', 'address']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = ['organization', 'quantity', 'location', 'date_received', 'expiration_date', 'lot_number', 'notes']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date', 'value': date.today()}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')
        self.fields['date_received'].initial = date.today()


class ItemWithStockForm(forms.Form):
    """Combined form for creating both Item and initial StockItem"""
    # Item fields
    name = forms.CharField(max_length=255, label="Item Name")
    subcategory = forms.ModelChoiceField(
        queryset=models.Subcategory.objects.all(),
        label="Category"
    )
    url = forms.URLField(required=False, label="URL")
    notes_public = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Public Notes")
    notes_private = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Private Notes")
    
    # StockItem fields
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label="Received From Organization"
    )
    quantity = forms.IntegerField(min_value=1, initial=1, label="Initial Quantity")
    stock_location = forms.CharField(max_length=100, required=False, label="Stock Location")
    date_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Received"
    )
    expiration_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Expiration Date (optional for non-perishable items)"
    )
    lot_number = forms.CharField(max_length=100, required=False, label="Lot Number")
    stock_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}), 
        required=False, 
        label="Stock Notes"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up subcategory choices grouped by category
        subcategories = models.Subcategory.objects.select_related('category').all().order_by('category__name', 'name')
        grouped_choices = []
        current_category_name = None
        category_group = []

        for subcategory in subcategories:
            if current_category_name and subcategory.category.name != current_category_name:
                grouped_choices.append((current_category_name, category_group))
                category_group = []
            
            category_group.append((subcategory.pk, subcategory.name))
            current_category_name = subcategory.category.name

        if category_group:
            grouped_choices.append((current_category_name, category_group))

        self.fields['subcategory'].choices = grouped_choices
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')
    def clean_name(self):
        """
        Validates that the item name is unique.
        """
        # Get the cleaned data for this specific field
        name = self.cleaned_data['name']

        # Check if an Item with this name already exists (case-insensitive)
        if models.Item.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                "An item with this name already exists. Please choose a different name.",
                code='duplicate_name'
            )

        # Always return the cleaned data for this field
        return name

    def save(self, commit=True):
        """Create both Item and initial StockItem"""
        # The cleaned_data from the form is used to create both objects
        data = self.cleaned_data

        # Create Item
        selected_subcategory = data['subcategory']
        item = models.Item(
            name=data['name'],
            category=selected_subcategory.category,
            subcategory=selected_subcategory,
            url=data['url'],
            notes_public=data['notes_public'],
            notes_private=data['notes_private']
        )
        
        if commit:
            item.save()
            
            # Create initial StockItem
            stock_item = StockItem(
                item=item,
                organization=data['organization'],
                quantity=data['quantity'],
                location=data['stock_location'],
                date_received=data['date_received'],
                expiration_date=data['expiration_date'],
                lot_number=data['lot_number'],
                notes=data['stock_notes']
            )
            stock_item.save()
            return item, stock_item
        
        return item, None

class ItemWithLocationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: models.Item):
        # Get all locations from the stock items
        return f"{obj.name} [{obj.aggregated_locations}]"


class StockItemEditForm(forms.ModelForm):
    """Form for editing individual stock items"""
    class Meta:
        model = StockItem
        fields = ['organization', 'quantity', 'location', 'date_received', 'expiration_date', 'lot_number', 'notes']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.all().order_by('name')


class Search_QuantityAdd(forms.Form):
    """Form for adding new stock (check-in) - creates new StockItem"""
    item = ItemWithLocationChoiceField(
        queryset=models.Item.active_objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all().order_by('name'),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Received From Organization"
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Quantity to add",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 12"})
    )
    location = forms.CharField(
        max_length=100,
        required=False,
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
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), 
        required=False, 
        label="Notes"
    )


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
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), 
        required=False, 
        label="Checkout Notes"
    )
    
    def __init__(self, item=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if item:
            self.fields['stock_items'].queryset = item.stock_items.filter(quantity__gt=0).order_by('expiration_date', 'date_received')

class UserCreationForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

class CrispyLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Log In'))