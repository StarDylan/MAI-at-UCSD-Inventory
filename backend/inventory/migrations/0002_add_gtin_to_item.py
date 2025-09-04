# Generated manually for GTIN tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='gtin',
            field=models.CharField(blank=True, default='', help_text='Global Trade Item Number (GTIN-8, GTIN-12, GTIN-13, or GTIN-14)', max_length=14),
        ),
        migrations.AddConstraint(
            model_name='item',
            constraint=models.UniqueConstraint(condition=models.Q(('gtin__gt', '')), fields=('gtin',), name='unique_item_gtin'),
        ),
    ]