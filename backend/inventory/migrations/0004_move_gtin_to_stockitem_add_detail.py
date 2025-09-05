# Generated manually to move GTIN from Item to StockItem and add detail field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_make_location_required'),
    ]

    operations = [
        # Add new fields to StockItem
        migrations.AddField(
            model_name='stockitem',
            name='gtin',
            field=models.CharField(blank=True, default='', help_text='Global Trade Item Number (GTIN-8, GTIN-12, GTIN-13, or GTIN-14)', max_length=14),
        ),
        migrations.AddField(
            model_name='stockitem',
            name='detail',
            field=models.CharField(blank=True, default='', help_text='Additional details like size, color, variant, etc.', max_length=255),
        ),
        
        # Remove the old constraint from Item before removing the field
        migrations.RemoveConstraint(
            model_name='item',
            name='unique_item_gtin',
        ),
        
        # Remove GTIN field from Item
        migrations.RemoveField(
            model_name='item',
            name='gtin',
        ),
        
        # Add uniqueness constraint for GTIN on StockItem (only for non-empty GTINs)
        migrations.AddConstraint(
            model_name='stockitem',
            constraint=models.UniqueConstraint(
                fields=['gtin'], 
                condition=models.Q(gtin__gt=''),
                name='unique_stockitem_gtin'
            ),
        ),
    ]