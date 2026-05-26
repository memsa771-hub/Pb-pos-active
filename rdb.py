#!/usr/bin/env python
"""
Database Reset Script (rdb.py)
==============================

This script empties the POS database except for Products, Categories and Users.

PRESERVED DATA:
- Users (auth_user)
- Products (posapp_product)
- Categories (posapp_category)
- User Roles (posapp_userrole)

CLEARED DATA:
- Orders and Order Items
- User Profiles
- Business Settings
- System Settings
- Business Logo
- Discounts
- Payment Transactions
- Audit Logs
- Bill Adjustments
- Advance Adjustments
- End Day Records
- Delivery Persons
- User Sessions

Usage:
    python rdb.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt and proceed directly
    --dry-run    Show what would be deleted without actually deleting
    --help       Show this help message

WARNING: This action cannot be undone. Always backup your database first!
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'posproject.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from posapp.models import (
    # Models to PRESERVE
    Product, Category, UserRole,
    
    # Models to CLEAR (everything else)
    Order, OrderItem, Discount, PaymentTransaction, AuditLog, 
    BillAdjustment, BillAdjustmentImage, AdvanceAdjustment, EndDay,
    UserProfile, BusinessSettings, Setting, BusinessLogo,
    DeliveryPerson, UserSession
)

class DatabaseResetManager:
    """Manages the database reset process"""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.models_to_clear = [
            # Order related (must be first due to foreign keys)
            (OrderItem, "Order Items"),
            (PaymentTransaction, "Payment Transactions"),
            (Order, "Orders"),
            
            # Discount related
            (Discount, "Discounts"),
            
            # Adjustment related
            (BillAdjustmentImage, "Bill Adjustment Images"),
            (BillAdjustment, "Bill Adjustments"),
            (AdvanceAdjustment, "Advance Adjustments"),
            
            # User management (everything except User model and UserRole)
            (UserSession, "User Sessions"),
            (UserProfile, "User Profiles"),
            
            # System settings and business data
            (BusinessLogo, "Business Logo"),
            (BusinessSettings, "Business Settings"),
            (Setting, "System Settings"),
            
            # Delivery persons
            (DeliveryPerson, "Delivery Persons"),
            
            # System logs and records
            (AuditLog, "Audit Logs"),
            (EndDay, "End Day Records"),
        ]
        
        self.preserved_models = [
            (User, "Users"),
            (Product, "Products"),
            (Category, "Categories"),
            (UserRole, "User Roles"),
        ]
    
    def get_statistics(self):
        """Get current database statistics"""
        stats = {}
        
        print("📊 CURRENT DATABASE STATISTICS")
        print("=" * 50)
        
        # Models to be cleared
        print("\n🗑️  DATA TO BE CLEARED:")
        total_to_clear = 0
        for model, name in self.models_to_clear:
            try:
                count = model.objects.count()
                stats[name] = count
                total_to_clear += count
                print(f"   {name}: {count:,} records")
            except Exception as e:
                print(f"   {name}: Error counting records - {e}")
        
        # Ensure output is flushed
        sys.stdout.flush()
        
        # Models to be preserved
        print("\n✅ DATA TO BE PRESERVED:")
        total_preserved = 0
        for model, name in self.preserved_models:
            try:
                count = model.objects.count()
                stats[name] = count
                total_preserved += count
                print(f"   {name}: {count:,} records")
            except Exception as e:
                print(f"   {name}: Model not available or error - {e}")
        
        # Ensure output is flushed
        sys.stdout.flush()
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total records to clear: {total_to_clear:,}")
        print(f"   Total records to preserve: {total_preserved:,}")
        
        # Ensure output is flushed
        sys.stdout.flush()
        
        return stats
    
    def clear_database(self):
        """Clear the database while preserving essential data"""
        if self.dry_run:
            print("\n🔍 DRY RUN MODE - No data will be actually deleted")
            return True
        
        try:
            with transaction.atomic():
                print("\n🚀 Starting database reset...")
                
                for model, name in self.models_to_clear:
                    count = model.objects.count()
                    if count > 0:
                        print(f"   Clearing {name}: {count:,} records...", end="")
                        model.objects.all().delete()
                        print(" ✅ Done")
                    else:
                        print(f"   {name}: No records to clear")
                
                print("\n✅ Database reset completed successfully!")
                return True
                
        except Exception as e:
            print(f"\n❌ Error during database reset: {str(e)}")
            return False
    
    def reset_sequences(self):
        """Reset auto-increment sequences for cleared tables"""
        if self.dry_run:
            return
        
        try:
            from django.db import connection
            
            print("\n🔄 Resetting auto-increment sequences...")
            
            with connection.cursor() as cursor:
                # Reset sequences for MySQL
                if 'mysql' in settings.DATABASES['default']['ENGINE']:
                    tables_to_reset = [
                        'posapp_order',
                        'posapp_orderitem', 
                        'posapp_discount',
                        'posapp_paymenttransaction',
                        'posapp_auditlog',
                        'posapp_billadjustment',
                        'posapp_billadjustmentimage',
                        'posapp_advanceadjustment',
                        'posapp_endday',
                        'posapp_usersession',
                        'posapp_userprofile',
                        'posapp_businesssettings',
                        'posapp_setting',
                        'posapp_businesslogo',
                        'posapp_deliveryperson',
                    ]
                    
                    for table in tables_to_reset:
                        try:
                            cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                            print(f"   Reset sequence for {table}")
                        except Exception as e:
                            print(f"   Warning: Could not reset sequence for {table}: {e}")
                
                print("✅ Sequences reset completed")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not reset sequences: {e}")
    
    def verify_reset(self):
        """Verify that the reset was successful"""
        print("\n🔍 VERIFYING RESET...")
        
        all_clear = True
        for model, name in self.models_to_clear:
            count = model.objects.count()
            if count == 0:
                print(f"   ✅ {name}: 0 records")
            else:
                print(f"   ❌ {name}: {count} records remaining")
                all_clear = False
        
        if all_clear:
            print("\n✅ Database reset verification successful!")
        else:
            print("\n❌ Database reset verification failed - some data remains")
        
        return all_clear

def show_help():
    """Show help message"""
    print(__doc__)

def get_user_confirmation():
    """Get user confirmation before proceeding"""
    print("\n⚠️  WARNING: This will permanently delete ALL data except:")
    print("   ✅ Users (login accounts)")
    print("   ✅ Products (inventory items)")  
    print("   ✅ Categories (product categories)")
    print("   ✅ User Roles (Admin, Cashier, etc.)")
    print("   🗑️  Everything else will be DELETED!")
    print("   This action cannot be undone.")
    
    while True:
        response = input("\n❓ Do you want to continue? (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("   Please enter 'yes' or 'no'")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset POS database while preserving Users, Products, Categories and User Roles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip confirmation prompt')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--help-full', action='store_true',
                       help='Show full help message')
    
    args = parser.parse_args()
    
    if args.help_full:
        show_help()
        return
    
    print("🗄️  POS DATABASE RESET UTILITY")
    print("=" * 50)
    
    # Initialize reset manager
    reset_manager = DatabaseResetManager(dry_run=args.dry_run)
    
    # Show current statistics
    reset_manager.get_statistics()
    
    # Get confirmation unless --confirm flag is used
    if not args.confirm and not args.dry_run:
        if not get_user_confirmation():
            print("\n❌ Operation cancelled by user")
            return
    
    # Perform the reset
    success = reset_manager.clear_database()
    
    if success and not args.dry_run:
        # Reset sequences
        reset_manager.reset_sequences()
        
        # Verify the reset
        reset_manager.verify_reset()
        
        print("\n🎉 Database reset completed successfully!")
        print("   All data has been cleared except:")
        print("   ✅ Users (login accounts)")
        print("   ✅ Products (inventory items)")
        print("   ✅ Categories (product categories)")
        print("   ✅ User Roles (Admin, Cashier, etc.)")
        
    elif args.dry_run:
        print("\n🔍 Dry run completed - no data was actually modified")
    else:
        print("\n❌ Database reset failed")

if __name__ == "__main__":
    main() 