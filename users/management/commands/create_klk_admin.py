"""
Create (or repair) a KLK superadmin in one step, with the management-portal
fields set correctly from the start.

    python manage.py create_klk_admin --username admin --email admin@klk.org --password 'secret'

Safe to re-run: an existing account with that username is repaired and its
password reset rather than duplicated.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import User


class Command(BaseCommand):
    help = 'Create or repair a KLK superadmin account.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', default='')
        parser.add_argument('--password', required=True)
        parser.add_argument('--first-name', default='')
        parser.add_argument('--last-name', default='')

    def handle(self, *args, **o):
        user, created = User.objects.get_or_create(
            username=o['username'],
            defaults={'email': o['email']},
        )
        user.email = o['email'] or user.email
        user.first_name = o['first_name'] or user.first_name
        user.last_name = o['last_name'] or user.last_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.role = 'admin'
        user.portal = 'admin'
        user.account_status = 'approved'
        user.approved_at = user.approved_at or timezone.now()
        user.auth_provider = 'password'
        user.set_password(o['password'])
        user.save()

        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} superadmin "{user.username}" — role=admin, portal=admin, status=approved.'
        ))
