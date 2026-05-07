from django.core.management.base import BaseCommand
from django.utils import timezone
from admins.models import TokenBlacklist


class Command(BaseCommand):
    help = 'Delete expired entries from the token blacklist.'

    def handle(self, *args, **options):
        deleted, _ = TokenBlacklist.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(f'Deleted {deleted} expired token blacklist entries.')
