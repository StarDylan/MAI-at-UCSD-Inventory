from django import forms
from .models import Category, Subcategory
from inventory import models
from allauth.account.forms import LoginForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


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
        # We only need 'subcategory' in the fields here, as the category
        # will be set automatically based on the chosen subcategory.
        fields = ['name', 'subcategory', "location", "url", "quantity_active", 'notes_public', 'notes_private']

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

class ItemWithLocationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: models.Item):
        return f"{obj.name} [{obj.location}]"


class Search_QuantityAdd(forms.Form):
    item = ItemWithLocationChoiceField(
        queryset=models.Item.objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Quantity to add",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 12"})
    )

class Search_QuantityRemove(forms.Form):
    item = ItemWithLocationChoiceField(
        queryset=models.Item.objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Quantity to remove",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 12"})
    )

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