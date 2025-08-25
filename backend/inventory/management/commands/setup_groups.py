# accounts/management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from inventory.models import DeletedCategory

class Command(BaseCommand):
    help = 'Creates default groups and assigns permissions.'

    def handle(self, *args, **options):
        # Create the 'Admin' and 'Normal' groups if they don't exist
        admin_group, created_admin = Group.objects.get_or_create(name='Admin')
        normal_group, created_normal = Group.objects.get_or_create(name='Normal')

        if created_admin:
            self.stdout.write(self.style.SUCCESS('Successfully created "Admin" group.'))
        if created_normal:
            self.stdout.write(self.style.SUCCESS('Successfully created "Normal" group.'))

        # Find the custom permission for 'view_deletedcategory'
        try:
            content_type = ContentType.objects.get_for_model(DeletedCategory)
            view_deleted_permission = Permission.objects.get(
                codename='view_deletedcategory',
                content_type=content_type
            )
        except (ContentType.DoesNotExist, Permission.DoesNotExist):
            self.stdout.write(self.style.ERROR("The 'view_deletedcategory' permission does not exist. Did you run migrations?"))
            return

        # Assign the custom permission to the Admin group
        if view_deleted_permission not in admin_group.permissions.all():
            admin_group.permissions.add(view_deleted_permission)
            self.stdout.write(self.style.SUCCESS("Successfully assigned 'view_deletedcategory' permission to 'Admin' group."))
        else:
            self.stdout.write(self.style.WARNING("'view_deletedcategory' permission is already assigned to 'Admin' group."))

        # Check if the 'Normal' group is empty (it should be)
        if normal_group.permissions.count() == 0:
            self.stdout.write(self.style.SUCCESS("'Normal' group is set up with no special permissions."))

