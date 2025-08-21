from django.db import models

# Create your models here.

class Item(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    categories = models.ManyToManyField('Category', blank=True)

    location = models.CharField(max_length=100)
    expiration_date = models.DateField(null=True, blank=True)
    
    date_received = models.DateField()
    donating_organization = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)


class Category(models.Model):
    name = models.CharField(max_length=100)
