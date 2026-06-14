#!/usr/bin/env python
"""
Reset POS database data but keep superuser admin account(s).

Usage:
    python scripts/del.py              # ask for confirmation
    python scripts/del.py --yes        # skip confirmation
    python scripts/del.py --dry-run    # show counts only

Keeps:
  - Django superuser(s) and their profiles
  - Standard roles: Admin, Branch Manager, Cashier
  - Business settings (Setting, BusinessSettings)

Removes:
  - Orders, products, categories, inventory, discounts, delivery staff
  - End-day records, adjustments, audit logs, sessions
  - All non-superuser accounts
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'posproject.settings')

import django

django.setup()

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import transaction

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    Purchase,
    PurchaseItem,
    Recipe,
    StockAdjustment,
    Supplier,
)
from posapp.models import (
    AdvanceAdjustment,
    AuditLog,
    BillAdjustment,
    BillAdjustmentImage,
    DeliveryPerson,
    Discount,
    EndDay,
    Order,
    OrderItem,
    PaymentTransaction,
    PosCategory,
    PosProduct,
    UserProfile,
    UserRole,
    UserSession,
)

STANDARD_ROLES = ('Admin', 'Branch Manager', 'Cashier')


def _count(qs):
    return qs.count()


def _admin_users():
    return User.objects.filter(is_superuser=True)


def _non_admin_users():
    return User.objects.filter(is_superuser=False)


def collect_deletion_plan():
    admins = list(_admin_users().values_list('username', flat=True))
    return {
        'admins_kept': admins,
        'bill_adjustment_images': _count(BillAdjustmentImage.objects.all()),
        'bill_adjustments': _count(BillAdjustment.objects.all()),
        'advance_adjustments': _count(AdvanceAdjustment.objects.all()),
        'payment_transactions': _count(PaymentTransaction.objects.all()),
        'order_items': _count(OrderItem.objects.all()),
        'orders': _count(Order.objects.all()),
        'end_days': _count(EndDay.objects.all()),
        'audit_logs': _count(AuditLog.objects.all()),
        'user_sessions': _count(UserSession.objects.all()),
        'django_sessions': _count(Session.objects.all()),
        'recipes': _count(Recipe.objects.all()),
        'stock_adjustments': _count(StockAdjustment.objects.all()),
        'purchase_items': _count(PurchaseItem.objects.all()),
        'purchases': _count(Purchase.objects.all()),
        'inventory_items': _count(InventoryItem.objects.all()),
        'inventory_categories': _count(InventoryCategory.objects.all()),
        'suppliers': _count(Supplier.objects.all()),
        'products': _count(PosProduct.objects.all()),
        'categories': _count(PosCategory.objects.all()),
        'discounts': _count(Discount.objects.all()),
        'delivery_persons': _count(DeliveryPerson.objects.all()),
        'users_removed': _count(_non_admin_users()),
        'orphan_roles': _count(
            UserRole.objects.exclude(name__in=STANDARD_ROLES)
        ),
    }


def print_plan(plan):
    print('\n=== Database reset plan ===')
    print(f"Admin kept: {', '.join(plan['admins_kept']) or '(none!)'}")
    print(f"Users to remove: {plan['users_removed']}")
    print(f"Orders: {plan['orders']} (+ {plan['order_items']} line items)")
    print(f"Products: {plan['products']} | POS categories: {plan['categories']}")
    print(f"Inventory items: {plan['inventory_items']} | Purchases: {plan['purchases']}")
    print(f"End days: {plan['end_days']} | Adjustments: {plan['bill_adjustments']} bill, {plan['advance_adjustments']} advance")
    print(f"Sessions: {plan['user_sessions']} tracked + {plan['django_sessions']} django")
    print(f"Custom roles to remove: {plan['orphan_roles']}")
    print('===========================\n')


@transaction.atomic
def run_reset():
    if not _admin_users().exists():
        raise RuntimeError(
            'No superuser found. Create admin first:\n'
            '  python manage.py createsuperuser'
        )

    deleted = {}

    deleted['bill_adjustment_images'] = BillAdjustmentImage.objects.all().delete()[0]
    deleted['bill_adjustments'] = BillAdjustment.objects.all().delete()[0]
    deleted['advance_adjustments'] = AdvanceAdjustment.objects.all().delete()[0]
    deleted['payment_transactions'] = PaymentTransaction.objects.all().delete()[0]
    deleted['order_items'] = OrderItem.objects.all().delete()[0]
    deleted['orders'] = Order.objects.all().delete()[0]
    deleted['end_days'] = EndDay.objects.all().delete()[0]
    deleted['audit_logs'] = AuditLog.objects.all().delete()[0]
    deleted['user_sessions'] = UserSession.objects.all().delete()[0]
    deleted['django_sessions'] = Session.objects.all().delete()[0]

    deleted['recipes'] = Recipe.objects.all().delete()[0]
    deleted['stock_adjustments'] = StockAdjustment.objects.all().delete()[0]
    deleted['purchase_items'] = PurchaseItem.objects.all().delete()[0]
    deleted['purchases'] = Purchase.objects.all().delete()[0]
    deleted['inventory_items'] = InventoryItem.objects.all().delete()[0]
    deleted['inventory_categories'] = InventoryCategory.objects.all().delete()[0]
    deleted['suppliers'] = Supplier.objects.all().delete()[0]

    deleted['products'] = PosProduct.objects.all().delete()[0]
    deleted['categories'] = PosCategory.objects.all().delete()[0]
    deleted['discounts'] = Discount.objects.all().delete()[0]
    deleted['delivery_persons'] = DeliveryPerson.objects.all().delete()[0]

    deleted['users_removed'] = _non_admin_users().delete()[0]
    deleted['orphan_roles'] = UserRole.objects.exclude(name__in=STANDARD_ROLES).delete()[0]

    # Ensure admin profiles point to Admin role if misassigned
    admin_role = UserRole.objects.filter(name='Admin').first()
    if admin_role:
        UserProfile.objects.filter(user__is_superuser=True).update(role=admin_role)

    return deleted


def main():
    parser = argparse.ArgumentParser(
        description='Delete all POS data except superuser admin account(s).',
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only show what would be deleted',
    )
    args = parser.parse_args()

    plan = collect_deletion_plan()
    print_plan(plan)

    if not plan['admins_kept']:
        print('ERROR: No superuser account exists. Aborting.')
        sys.exit(1)

    if args.dry_run:
        print('Dry run complete. No changes made.')
        return

    if not args.yes:
        answer = input('Type DELETE to confirm this cannot be undone: ').strip()
        if answer != 'DELETE':
            print('Cancelled.')
            sys.exit(0)

    try:
        deleted = run_reset()
    except Exception as exc:
        print(f'ERROR: {exc}')
        sys.exit(1)

    print('Reset complete.')
    for key, value in deleted.items():
        if value:
            print(f'  - {key}: {value} deleted')
    print(f"Admin account(s) kept: {', '.join(plan['admins_kept'])}")


if __name__ == '__main__':
    main()
