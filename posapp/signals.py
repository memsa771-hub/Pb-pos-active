from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, UserRole, Order, OrderItem, AuditLog, EndDay
import random
import string
from django.utils import timezone

# Import session manager to register signal handlers
from . import session_manager

# Create a user profile when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Determine role based on user status
        if instance.is_superuser or instance.is_staff:
            # Get or create Admin role for superusers/staff
            admin_role, _ = UserRole.objects.get_or_create(
                name='Admin',
                defaults={'description': 'Administrator with full access'}
            )
            role = admin_role
        else:
            # Get the default role (Cashier) for regular users
            role, _ = UserRole.objects.get_or_create(
                name='Cashier',
                defaults={'description': 'Cashier with limited access'}
            )
        
        # Create a user profile safely (avoid duplicates)
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': role,
                'is_active': True
            }
        )

# Handle order number generation
@receiver(pre_save, sender=Order)
def generate_order_number(sender, instance, **kwargs):
    # Always set a proper daily order number, even if order_number exists
    # Get the last end day record
    last_end_day = EndDay.get_last_end_day()
    
    # If we have a last end day, count orders since that date
    # Otherwise count all orders for today
    if last_end_day:
        # Count orders created since the last end day
        daily_count = Order.objects.filter(created_at__gt=last_end_day.end_date).count() + 1
    else:
        # Count orders for today if no end day exists
        today = timezone.now().date()
        daily_count = Order.objects.filter(created_at__date=today).count() + 1
        
    # Set the daily order number (always set this, not just for new orders)
    instance.daily_order_number = daily_count
    
    # Generate reference number if it doesn't exist
    if not instance.reference_number:
        # Generate a unique reference number with format PB + 4 digits
        while True:
            # Generate random 4-digit number
            random_digits = ''.join(random.choices(string.digits, k=4))
            reference_number = f'PB{random_digits}'
            
            # Check if the reference number already exists
            if not Order.objects.filter(reference_number=reference_number).exists():
                instance.reference_number = reference_number
                break
    
    # Only set the persistent order number if it doesn't exist yet
    if not instance.order_number:
        # Generate the persistent unique order number (never resets)
        # Get count of existing orders and increment by 1
        order_count = Order.objects.count() + 1
        # Format as simple numeric order number
        instance.order_number = f'{order_count:05d}'

# Update user profile role when user status changes
@receiver(post_save, sender=User)
def update_user_profile_role(sender, instance, created, **kwargs):
    # Only for existing users (not created ones, as they're handled above)
    if not created:
        try:
            profile = UserProfile.objects.get(user=instance)
            
            # If user became superuser/staff, update to Admin role
            if (instance.is_superuser or instance.is_staff) and profile.role.name != 'Admin':
                admin_role, _ = UserRole.objects.get_or_create(
                    name='Admin',
                    defaults={'description': 'Administrator with full access'}
                )
                profile.role = admin_role
                profile.save()
                
            # If user is no longer superuser/staff and has Admin role, revert to default
            elif not (instance.is_superuser or instance.is_staff) and profile.role.name == 'Admin':
                cashier_role, _ = UserRole.objects.get_or_create(
                    name='Cashier',
                    defaults={'description': 'Cashier with limited access'}
                )
                profile.role = cashier_role
                profile.save()
                
        except UserProfile.DoesNotExist:
            # If profile doesn't exist, create it (fallback)
            if instance.is_superuser or instance.is_staff:
                admin_role, _ = UserRole.objects.get_or_create(
                    name='Admin',
                    defaults={'description': 'Administrator with full access'}
                )
                role = admin_role
            else:
                role, _ = UserRole.objects.get_or_create(
                    name='Cashier',
                    defaults={'description': 'Cashier with limited access'}
                )
            
            UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'role': role,
                    'is_active': True
                }
            )

# Log user activity
@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(
            user=None,  # System activity
            action='User Created',
            entity='User',
            entity_id=instance.id,
            details=f'User {instance.username} was created'
        )
    else:
        AuditLog.objects.create(
            user=None,  # System activity
            action='User Updated',
            entity='User',
            entity_id=instance.id,
            details=f'User {instance.username} was updated'
        ) 