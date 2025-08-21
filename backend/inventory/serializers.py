from rest_framework import serializers
from inventory.models import Item, Category


class ItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "quantity",
            "categories",
            "location",
            "expiration_date",
            "date_received",
            "donating_organization",
            "created",
        ]


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]
