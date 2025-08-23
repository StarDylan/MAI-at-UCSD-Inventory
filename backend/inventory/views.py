from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import loader

from inventory.models import Category

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