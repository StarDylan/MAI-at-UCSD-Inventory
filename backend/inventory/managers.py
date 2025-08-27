from django.db import models


class ActiveManager(models.Manager):
    """
    A custom manager that returns only active (is_deleted=False) objects.
    This will be the default manager on our models.
    """
    def get_queryset(self):
        # We override the get_queryset method to add a filter.
        # super().get_queryset() gets the standard queryset.
        return super().get_queryset().filter(is_deleted=False)

