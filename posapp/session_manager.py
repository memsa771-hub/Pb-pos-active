from django.contrib.sessions.models import Session
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import UserSession
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_user_agent(request):
    """Get the user agent from the request"""
    return request.META.get('HTTP_USER_AGENT', '')[:255]

@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """
    Handle user login event - enforce single session per user
    """
    try:
        # Get the current session key
        current_session_key = request.session.session_key
        if not current_session_key:
            # Create session if it doesn't exist
            request.session.save()
            current_session_key = request.session.session_key

        # Get client info
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Check if user already has an active session
        try:
            existing_session = UserSession.objects.get(user=user)
            
            # If the existing session is different from current, invalidate the old one
            if existing_session.session_key != current_session_key:
                try:
                    # Delete the old session from Django's session store
                    old_session = Session.objects.get(session_key=existing_session.session_key)
                    old_session.delete()
                    logger.info(f"Invalidated old session for user {user.username}")
                except Session.DoesNotExist:
                    # Old session was already expired/deleted
                    pass
                
                # Update the existing UserSession record with new session info
                existing_session.session_key = current_session_key
                existing_session.login_time = timezone.now()
                existing_session.ip_address = ip_address
                existing_session.user_agent = user_agent
                existing_session.save()
            else:
                # Same session, just update last activity
                existing_session.last_activity = timezone.now()
                existing_session.save()
                
        except UserSession.DoesNotExist:
            # Create new session record
            UserSession.objects.create(
                user=user,
                session_key=current_session_key,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        logger.info(f"User {user.username} logged in from {ip_address}")
        
    except Exception as e:
        logger.error(f"Error handling user login for {user.username}: {str(e)}")

@receiver(user_logged_out)
def handle_user_logout(sender, request, user, **kwargs):
    """
    Handle user logout event - clean up session tracking
    """
    try:
        if user:
            # Remove the UserSession record
            UserSession.objects.filter(user=user).delete()
            logger.info(f"User {user.username} logged out")
    except Exception as e:
        logger.error(f"Error handling user logout for {user.username if user else 'Unknown'}: {str(e)}")

def cleanup_expired_sessions():
    """
    Utility function to clean up expired sessions
    Can be called from a management command or scheduled task
    """
    try:
        # Get all session keys from UserSession
        tracked_sessions = UserSession.objects.values_list('session_key', flat=True)
        
        # Get all valid session keys from Django's session store
        valid_sessions = Session.objects.filter(
            session_key__in=tracked_sessions,
            expire_date__gt=timezone.now()
        ).values_list('session_key', flat=True)
        
        # Remove UserSession records for expired sessions
        expired_count = UserSession.objects.exclude(session_key__in=valid_sessions).delete()[0]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired session records")
            
        return expired_count
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {str(e)}")
        return 0

def force_logout_user(user):
    """
    Force logout a specific user by invalidating their session
    """
    try:
        user_session = UserSession.objects.get(user=user)
        
        # Delete the session from Django's session store
        try:
            session = Session.objects.get(session_key=user_session.session_key)
            session.delete()
        except Session.DoesNotExist:
            pass
            
        # Delete the UserSession record
        user_session.delete()
        
        logger.info(f"Force logged out user {user.username}")
        return True
    except UserSession.DoesNotExist:
        logger.info(f"User {user.username} was not logged in")
        return False
    except Exception as e:
        logger.error(f"Error force logging out user {user.username}: {str(e)}")
        return False

def get_active_users():
    """
    Get list of currently active users
    """
    try:
        # Get session keys that haven't expired
        valid_sessions = Session.objects.filter(
            expire_date__gt=timezone.now()
        ).values_list('session_key', flat=True)
        
        # Get users with valid sessions
        active_users = UserSession.objects.filter(
            session_key__in=valid_sessions
        ).select_related('user').order_by('login_time')
        
        return active_users
    except Exception as e:
        logger.error(f"Error getting active users: {str(e)}")
        return UserSession.objects.none() 