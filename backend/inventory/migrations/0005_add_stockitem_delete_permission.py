# Generated manually to add delete permission for StockItem

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_move_gtin_to_stockitem_add_detail'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='stockitem',
            options={
                'ordering': ['detail', 'expiration_date', 'date_received'], 
                'permissions': [('delete_stockitem', 'Can delete stock items')]
            },
        ),
    ]