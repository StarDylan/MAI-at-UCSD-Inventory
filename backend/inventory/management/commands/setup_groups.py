# accounts/management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from inventory import models

class Command(BaseCommand):
    help = 'Creates default groups and assigns permissions.'

    def handle(self, *args, **options):
        user_group, created = Group.objects.get_or_create(name='User')
        if created:
            print("  Created new group: User")

        member_group, created = Group.objects.get_or_create(name='Member')
        if created:
            print("  Created new group: Member")

        admin_group, created = Group.objects.get_or_create(name='Admin')
        if created:
            print("  Created new group: Admin")

        # Get ContentType for your models
        audit_event_ct = ContentType.objects.get_for_model(model=models.AuditEvent)
        category_ct = ContentType.objects.get_for_model(model=models.Category)
        subcategory_ct = ContentType.objects.get_for_model(model=models.Subcategory)
        user_ct = ContentType.objects.get_for_model(model=models.User)
        item_ct = ContentType.objects.get_for_model(model=models.Item)
        image_ct = ContentType.objects.get_for_model(model=models.Image)
        organization_ct = ContentType.objects.get_for_model(model=models.Organization)
        stockitem_ct = ContentType.objects.get_for_model(model=models.StockItem)
        checkout_ct = ContentType.objects.get_for_model(model=models.CheckOut)

        user_permissions = []

        # Define a list of permissions for the member group
        member_permissions = user_permissions + [

            Permission.objects.get(codename='view_auditevent', content_type=audit_event_ct),
            
            Permission.objects.get(codename='add_item', content_type=item_ct),
            Permission.objects.get(codename='change_item', content_type=item_ct),
            Permission.objects.get(codename='view_internalstockingdetails', content_type=item_ct),

            Permission.objects.get(codename='delete_item', content_type=item_ct),
            Permission.objects.get(codename='add_image', content_type=image_ct),

            # Stock item permissions for members
            Permission.objects.get(codename='view_stockitem', content_type=stockitem_ct),
            Permission.objects.get(codename='add_stockitem', content_type=stockitem_ct),
            Permission.objects.get(codename='change_stockitem', content_type=stockitem_ct),
            Permission.objects.get(codename='delete_stockitem', content_type=stockitem_ct),
            
            Permission.objects.get(codename='view_checkout', content_type=checkout_ct),

        ]

        admin_permissions = member_permissions + [

            Permission.objects.get(codename='delete_image', content_type=image_ct),

            Permission.objects.get(codename='add_user', content_type=user_ct),
            Permission.objects.get(codename='change_user', content_type=user_ct),
            Permission.objects.get(codename='delete_user', content_type=user_ct),
            Permission.objects.get(codename='view_user', content_type=user_ct),
            Permission.objects.get(codename='restore_user', content_type=user_ct),


            Permission.objects.get(codename='add_category', content_type=category_ct),
            Permission.objects.get(codename='add_subcategory', content_type=subcategory_ct),
            Permission.objects.get(codename='change_category', content_type=category_ct),
            Permission.objects.get(codename='delete_category', content_type=category_ct),
            Permission.objects.get(codename='change_subcategory', content_type=subcategory_ct),
            Permission.objects.get(codename='delete_subcategory', content_type=subcategory_ct),

            Permission.objects.get(codename='view_deleteditem', content_type=item_ct),
            Permission.objects.get(codename='restore_deleteditem', content_type=item_ct),

            Permission.objects.get(codename='view_advancedpropertiesitem', content_type=item_ct),

            Permission.objects.get(codename='view_allauditevents', content_type=audit_event_ct),

            # Organization and stock item admin permissions
            Permission.objects.get(codename='add_organization', content_type=organization_ct),
            Permission.objects.get(codename='change_organization', content_type=organization_ct),
            Permission.objects.get(codename='delete_organization', content_type=organization_ct),
            Permission.objects.get(codename='view_organization', content_type=organization_ct),

            # Surplus report permissions for members
            Permission.objects.get(codename='view_surplus_report', content_type=stockitem_ct),
            Permission.objects.get(codename='download_surplus_report', content_type=stockitem_ct),
            Permission.objects.get(codename='upload_surplus_report', content_type=stockitem_ct),
            
            Permission.objects.get(codename='add_viaspreadsheet_item', content_type=item_ct),
            
            Permission.objects.get(codename='complete_checkout', content_type=checkout_ct),
            Permission.objects.get(codename='undo_checkout', content_type=checkout_ct),
            Permission.objects.get(codename='delete_checkout', content_type=checkout_ct),
            Permission.objects.get(codename='add_checkout', content_type=checkout_ct),
            Permission.objects.get(codename='change_checkout', content_type=checkout_ct),
        ]

        # Add the permissions to the Member group

        user_group.permissions.set(user_permissions)
        member_group.permissions.set(member_permissions)
        admin_group.permissions.set(admin_permissions)