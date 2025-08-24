import json
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template import loader
from django.contrib.auth.decorators import login_required

from inventory.forms import CategoryForm
from inventory.models import AuditEvent, Category, Image, Subcategory

def index(request):
    # Redirect to dashboard
    return HttpResponseRedirect(reverse("dashboard"))

def dashboard(request):
    template = loader.get_template("dashboard.html")
    return HttpResponse(template.render({}, request))

def view_database(request):
    # Fetch all categories and prefetch related subcategories
    categories = Category.objects.prefetch_related('subcategories').all()

    context = {
        'categories': categories,
    }

    template = loader.get_template("view.html")
    return HttpResponse(template.render(context, request))


def audit_view(request):
    """
    Renders the audit log page.
    """
    events = AuditEvent.objects.all().order_by('-created_at')

    # Prepare data for the template
    for event in events:
        # Manually serialize the relevant data to a JSON string
        event.json_data = json.dumps({
            'before': event.before,
            'after': event.after,
        })
        
    context = {
        'events': events,
    }
    template = loader.get_template("audit.html")
    return HttpResponse(template.render(context, request))

def delete_category_list_view(request):
    categories = Category.objects.all().order_by('name')
    template = loader.get_template("delete/category.html")
    return HttpResponse(template.render({'categories': categories}, request))

@login_required
def delete_category(request, uuid):
    # Check for admin privileges
    # if not request.user.has_perm('inventory.delete_category'):
    #     return #redirect('permission_error') # You need to create this URL

    # Get the category object or return a 404 error if not found
    category = get_object_or_404(Category, pk=uuid)

    # Perform the deletion
    category.delete()

    return redirect('dashboard')

def delete_image_list_view(request):
    # Use select_related('item') to join the Image and Item tables in the database query.
    # This makes the data available without additional queries in the template.
    images = Image.objects.select_related('item').all().order_by('item__name')

    print(images)
    
    # The template loader is not strictly necessary here, render() is a shortcut for this
    template = loader.get_template("delete/image.html")
    return HttpResponse(template.render({'images': images}, request))

def profile_view(request):
    return HttpResponseRedirect(reverse("dashboard"))

def delete_subcategory_list_view(request):
    """
    Fetches all subcategories from the database and pre-fetches
    their related category data using select_related() for efficiency.
    """
    subcategories = Subcategory.objects.select_related('category').all().order_by('name')


    context = {
        'subcategories': subcategories
    }
    
    # Render the template and pass the context data.
    template = loader.get_template("delete/subcategory.html")
    return HttpResponse(template.render(context, request))


@login_required
def delete_subcategory(request, uuid):
    # Check for admin privileges
    # if not request.user.has_perm('inventory.delete_subcategory'):
    #     return #redirect('permission_error') # You need to create this URL

    # Get the subcategory object or return a 404 error if not found
    subcategory = get_object_or_404(Subcategory, pk=uuid)

    # Perform the deletion
    subcategory.delete()

    return redirect('dashboard')


@login_required
def edit_category(request, uuid):
    category = get_object_or_404(Category, id=uuid)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # Replace with the URL you want to redirect to after a successful edit
    else:
        form = CategoryForm(instance=category)

    return render(request, 'edit/category.html', {'form': form})

