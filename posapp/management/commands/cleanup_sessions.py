from django.core.management.base import BaseCommand
from django.utils import timezone
from posapp.session_manager import cleanup_expired_sessions

class Command(BaseCommand):
    help = 'Clean up expired user sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually doing it',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'Starting session cleanup at {timezone.now()}')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
            # In a real implementation, you'd show what would be cleaned
            from posapp.models import UserSession
            from django.contrib.sessions.models import Session
            
            tracked_sessions = UserSession.objects.values_list('session_key', flat=True)
            valid_sessions = Session.objects.filter(
                session_key__in=tracked_sessions,
                expire_date__gt=timezone.now()
            ).values_list('session_key', flat=True)
            
            expired_sessions = UserSession.objects.exclude(session_key__in=valid_sessions)
            
            self.stdout.write(
                f'Would clean up {expired_sessions.count()} expired session records'
            )
            
            for session in expired_sessions:
                self.stdout.write(f'  - {session.user.username} (expired session)')
        else:
            cleaned_count = cleanup_expired_sessions()
            
            if cleaned_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully cleaned up {cleaned_count} expired sessions')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No expired sessions found to clean up')
                ) 