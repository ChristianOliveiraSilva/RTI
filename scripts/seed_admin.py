#!/usr/bin/env python3
"""Seed an admin user in the database.

Usage (inside Docker container):
    docker compose exec app python scripts/seed_admin.py --email admin@ifms.edu.br --name "Admin IFMS"

Or without arguments (uses the first email from ADMIN_EMAILS in .env):
    docker compose exec app python scripts/seed_admin.py

If the user already exists, it promotes them to admin.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import SessionLocal
from app.models import User, UserRole


def seed_admin(email: str, name: str) -> None:
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.admin:
                existing.role = UserRole.admin
                db.commit()
                print(f"User '{email}' promoted to admin.")
            else:
                print(f"User '{email}' is already an admin.")
            return

        user = User(
            name=name,
            email=email,
            role=UserRole.admin,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {email} (name={name})")


def main():
    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", type=str, default=None, help="Admin email")
    parser.add_argument("--name", type=str, default=None, help="Admin name")
    args = parser.parse_args()

    email = args.email
    name = args.name

    if not email:
        if settings.admin_emails_list:
            email = settings.admin_emails_list[0]
        else:
            print("ERROR: No --email provided and ADMIN_EMAILS is empty in .env")
            sys.exit(1)

    if not name:
        name = "Admin"

    seed_admin(email.lower().strip(), name)


if __name__ == "__main__":
    main()
