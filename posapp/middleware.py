import time
import pytz
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from .models import UserSession
import logging

logger = logging.getLogger(__name__)

# High-frequency POS API paths — skip extra session DB work
_FAST_API_PREFIXES = ('/api/orders/', '/api/tables/active/', '/api/products/')

_timezone_cache = {'name': None, 'tz': None, 'loaded_at': 0}
_TIMEZONE_CACHE_TTL = 300


def _is_fast_api_path(path):
    return path.startswith(_FAST_API_PREFIXES)


class SessionActivityMiddleware:
    """
    Middleware to update user session activity and provide session management
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.update_session_activity(request)
        return self.get_response(request)

    def update_session_activity(self, request):
        try:
            if _is_fast_api_path(request.path):
                return

            if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
                session_key = request.session.session_key
                if not session_key:
                    return

                now = time.time()
                last_update = request.session.get('_activity_ts', 0)
                if now - last_update < 30:
                    return

                UserSession.objects.filter(
                    user=request.user,
                    session_key=session_key
                ).update(last_activity=timezone.now())
                request.session['_activity_ts'] = now

        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")


class SingleSessionMiddleware:
    """
    Middleware to enforce single session per user
    This provides an additional layer of protection
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.check_session_validity(request)
        return self.get_response(request)

    def check_session_validity(self, request):
        try:
            if _is_fast_api_path(request.path):
                return

            if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
                session_key = request.session.session_key
                if not session_key:
                    return

                now = time.time()
                last_check = request.session.get('_session_check_ts', 0)
                if now - last_check < 60:
                    return

                try:
                    user_session = UserSession.objects.only('session_key').get(user=request.user)
                    if user_session.session_key != session_key:
                        from django.contrib.auth import logout
                        logout(request)
                        logger.info(f"Logged out user {request.user.username} due to session mismatch")
                except UserSession.DoesNotExist:
                    from django.contrib.auth import logout
                    logout(request)
                    logger.info(f"Logged out user {request.user.username} due to missing session record")

                request.session['_session_check_ts'] = now

        except Exception as e:
            logger.error(f"Error checking session validity: {str(e)}")


class TimezoneMiddleware:
    """
    Middleware to activate the timezone configured in system settings.
    Defaults to Asia/Karachi (Pakistan Standard Time) if not set.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _timezone_cache
        try:
            now = time.time()
            if _timezone_cache['tz'] and (now - _timezone_cache['loaded_at']) < _TIMEZONE_CACHE_TTL:
                tz = _timezone_cache['tz']
            else:
                from .models import Setting
                tz_name = Setting.get_value('timezone', 'Asia/Karachi')
                tz = pytz.timezone(tz_name)
                _timezone_cache['name'] = tz_name
                _timezone_cache['tz'] = tz
                _timezone_cache['loaded_at'] = now
        except Exception:
            tz = pytz.timezone('Asia/Karachi')

        timezone.activate(tz)
        response = self.get_response(request)
        timezone.deactivate()
        return response
