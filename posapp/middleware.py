import pytz
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from .models import UserSession
import logging

logger = logging.getLogger(__name__)

class SessionActivityMiddleware:
    """
    Middleware to update user session activity and provide session management
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update session activity before processing the request
        self.update_session_activity(request)
        
        response = self.get_response(request)
        
        return response

    def update_session_activity(self, request):
        """Update the last activity time for the current user session"""
        try:
            # Only update for authenticated users
            if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
                session_key = request.session.session_key
                
                if session_key:
                    # Update the last activity time
                    UserSession.objects.filter(
                        user=request.user,
                        session_key=session_key
                    ).update(last_activity=timezone.now())
                    
        except Exception as e:
            # Log the error but don't break the request
            logger.error(f"Error updating session activity: {str(e)}")

class SingleSessionMiddleware:
    """
    Middleware to enforce single session per user
    This provides an additional layer of protection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check session validity before processing the request
        self.check_session_validity(request)
        
        response = self.get_response(request)
        
        return response

    def check_session_validity(self, request):
        """Check if the current session is valid for the user"""
        try:
            # Only check for authenticated users
            if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
                session_key = request.session.session_key
                
                if session_key:
                    # Check if this session is the active one for the user
                    try:
                        user_session = UserSession.objects.get(user=request.user)
                        
                        # If the session keys don't match, this session is invalid
                        if user_session.session_key != session_key:
                            # Log the user out
                            from django.contrib.auth import logout
                            logout(request)
                            logger.info(f"Logged out user {request.user.username} due to session mismatch")
                            
                    except UserSession.DoesNotExist:
                        # No active session record, log the user out
                        from django.contrib.auth import logout
                        logout(request)
                        logger.info(f"Logged out user {request.user.username} due to missing session record")
                        
        except Exception as e:
            # Log the error but don't break the request
            logger.error(f"Error checking session validity: {str(e)}")


class TimezoneMiddleware:
    """
    Middleware to activate the timezone configured in system settings.
    Defaults to Asia/Karachi (Pakistan Standard Time) if not set.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from .models import Setting
            tz_name = Setting.get_value('timezone', 'Asia/Karachi')
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.timezone('Asia/Karachi')

        timezone.activate(tz)
        response = self.get_response(request)
        timezone.deactivate()
        return response 