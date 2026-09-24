"""
Repair accounts whose role / portal / status fields contradict each other.

The classic case this fixes: a superuser made with `manage.py createsuperuser`
before the custom manager existed. Django set is_superuser=True but left the
KLK fields at their model defaults — role='beneficiary', portal='beneficiary',
account_status='pending' — so signing in landed on the scholar side and showed
"wait for a staff member to verify you".

Run once after upgrading:

    python manage.py repair_accounts

Add --dry-run to see what would change without writing anything.
"""
from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = 'Fix accounts with inconsistent role/portal/account_status fields.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report changes without saving them.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        fixed = 0

        for user in User.objects.all():
            before = (user.role, user.portal, user.account_status)
            if user.normalize_access(commit=not dry):
                after = (user.role, user.portal, user.account_status)
                self.stdout.write(
                    f'  {user.username}: '
                    f'{before[0]}/{before[1]}/{before[2]}  ->  '
                    f'{after[0]}/{after[1]}/{after[2]}'
                )
                fixed += 1

        if fixed == 0:
            self.stdout.write(self.style.SUCCESS('All accounts are already consistent.'))
        elif dry:
            self.stdout.write(self.style.WARNING(f'{fixed} account(s) would be repaired (dry run).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Repaired {fixed} account(s).'))
