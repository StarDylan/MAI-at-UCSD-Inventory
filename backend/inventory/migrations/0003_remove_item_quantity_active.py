# Generated manually to remove quantity_active field from Item model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_add_organization_stockitem'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='quantity_active',
        ),
    ]