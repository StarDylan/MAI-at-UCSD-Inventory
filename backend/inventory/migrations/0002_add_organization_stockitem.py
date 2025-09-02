# Generated manually for the addition of Organization and StockItem models

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('contact_email', models.EmailField(blank=True, max_length=254)),
                ('contact_phone', models.CharField(blank=True, default='', max_length=20)),
                ('address', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='StockItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('date_received', models.DateField()),
                ('expiration_date', models.DateField(blank=True, help_text='Leave blank for non-perishable items', null=True)),
                ('lot_number', models.CharField(blank=True, default='', max_length=100)),
                ('notes', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True, help_text='False if this stock has been consumed/disposed')),
                ('item', models.ForeignKey(db_column='item_id', on_delete=django.db.models.deletion.CASCADE, related_name='stock_items', to='inventory.item')),
                ('organization', models.ForeignKey(db_column='organization_id', on_delete=django.db.models.deletion.PROTECT, related_name='stock_items', to='inventory.organization')),
            ],
            options={
                'permissions': [('view_stockitem', 'Can view stock items')],
            },
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.UniqueConstraint(fields=['name'], name='unique_organization_name'),
        ),
        migrations.AddIndex(
            model_name='stockitem',
            index=models.Index(fields=['item', 'expiration_date'], name='inventory_st_item_id_e850b3_idx'),
        ),
        migrations.AddIndex(
            model_name='stockitem',
            index=models.Index(fields=['organization', 'date_received'], name='inventory_st_organiz_62b53d_idx'),
        ),
    ]