#!/usr/bin/env python
"""
create_admin.py — First-time setup script for Project Sandy.

Creates a Level-3 Admin account that can log into the app and manage
all other accounts via the Admin Management page.

Usage:
    python create_admin.py

Run this from the project root with the virtual environment active:
    source venv/Scripts/activate   (Windows)
    source venv/bin/activate       (Mac/Linux)
    python create_admin.py
"""

import os
import sys
import django

# ── Bootstrap Django ──────────────────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

django.setup()

# ── Imports (after setup) ─────────────────────────────────────────────────────
import uuid
import re
from django.contrib.auth.hashers import make_password
from admins.models import Admin


def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('at least 8 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('at least one uppercase letter')
    if not re.search(r'\d', password):
        errors.append('at least one number')
    if not re.search(r'[^A-Za-z0-9]', password):
        errors.append('at least one special character (e.g. ! @ # $)')
    return errors


def main():
    print()
    print('=' * 55)
    print('  Project Sandy — Create Level-3 Admin Account')
    print('=' * 55)
    print()

    # Tenant ID
    existing = Admin.objects.first()
    if existing:
        tenant_id = str(existing.tenant_id)
        print(f'  Using existing tenant ID: {tenant_id}')
    else:
        tenant_id = str(uuid.uuid4())
        print(f'  No existing accounts found.')
        print(f'  Generated tenant ID:  {tenant_id}')
        print(f'  (Keep this ID — all accounts must share the same tenant.)')
    print()

    # Username
    while True:
        admin_name = input('  Username: ').strip()
        if not admin_name:
            print('  Username cannot be empty.')
            continue
        if Admin.objects.filter(admin_name=admin_name).exists():
            print(f'  Username "{admin_name}" is already taken.')
            continue
        break

    # Email
    while True:
        email = input('  Email:    ').strip()
        if not email or '@' not in email:
            print('  Enter a valid email address.')
            continue
        if Admin.objects.filter(email=email).exists():
            print(f'  Email "{email}" is already registered.')
            continue
        break

    # Password
    import getpass
    while True:
        password = getpass.getpass('  Password: ')
        errors = validate_password(password)
        if errors:
            print(f'  Password must contain: {", ".join(errors)}')
            continue
        confirm = getpass.getpass('  Confirm:  ')
        if password != confirm:
            print('  Passwords do not match.')
            continue
        break

    # Create
    print()
    try:
        admin = Admin.objects.create(
            tenant_id=tenant_id,
            admin_name=admin_name,
            email=email,
            password_hash=make_password(password, hasher='bcrypt_sha256'),
            role='admin',
            authorization_level=3,
            is_active=True,
            must_change_password=False,
        )
        print('  ✓ Account created successfully!')
        print()
        print(f'    Username : {admin.admin_name}')
        print(f'    Role     : admin  (Level 3)')
        print(f'    Tenant   : {admin.tenant_id}')
        print()
        print('  You can now log in at http://localhost:5173')
        print('  The Admin Management page will appear in the sidebar.')
    except Exception as e:
        print(f'  Error: {e}')
        sys.exit(1)

    print()
    print('=' * 55)


if __name__ == '__main__':
    main()
