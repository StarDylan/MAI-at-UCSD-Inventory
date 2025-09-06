# Generated manually for bulk checkout system

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_add_items_per_box_to_item'),
    ]

    operations = [
        migrations.CreateModel(
            name='CheckOut',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('total_weight', models.DecimalField(blank=True, decimal_places=2, help_text='Total weight of all items in the checkout (filled at completion)', max_digits=10, null=True)),
                ('notes', models.TextField(blank=True, default='', help_text='Additional notes for this checkout')),
                ('is_completed', models.BooleanField(default=False)),
                ('completed_by', models.ForeignKey(blank=True, db_column='completed_by_id', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='completed_checkouts', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(db_column='created_by_id', on_delete=django.db.models.deletion.PROTECT, related_name='created_checkouts', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(db_column='organization_id', help_text='Organization that items are being checked out to', on_delete=django.db.models.deletion.PROTECT, related_name='checkouts', to='inventory.organization')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CheckOutItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantity', models.PositiveIntegerField(help_text='Quantity to check out from this stock item')),
                ('cost_per_item', models.DecimalField(blank=True, decimal_places=2, help_text='Cost per individual item (can be filled during checkout)', max_digits=10, null=True)),
                ('notes', models.TextField(blank=True, default='', help_text='Notes specific to this line item')),
                ('checkout', models.ForeignKey(db_column='checkout_id', on_delete=django.db.models.deletion.CASCADE, related_name='checkout_items', to='inventory.checkout')),
                ('stock_item', models.ForeignKey(db_column='stock_item_id', on_delete=django.db.models.deletion.PROTECT, related_name='checkout_items', to='inventory.stockitem')),
            ],
            options={
                'ordering': ['stock_item__item__name', 'stock_item__detail'],
            },
        ),
        migrations.AddConstraint(
            model_name='checkoutitem',
            constraint=models.UniqueConstraint(fields=('checkout', 'stock_item'), name='unique_checkout_stock_item'),
        ),
    ]