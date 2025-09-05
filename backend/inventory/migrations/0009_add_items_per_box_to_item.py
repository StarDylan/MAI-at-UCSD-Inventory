# Generated for tracking items per box

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_item_gtin_item_unique_item_gtin'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='items_per_box',
            field=models.PositiveIntegerField(blank=True, help_text='Number of individual items in a single box/package', null=True),
        ),
    ]