#!/usr/bin/env python3
"""
Script to add admin role to user by telegram_id
Usage: python scripts/add_admin.py <telegram_id>
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models.user import User

def add_admin(telegram_id):
    """Add admin role to user"""
    app = create_app()
    
    with app.app_context():
        try:
            telegram_id_int = int(telegram_id)
            user = User.query.filter_by(telegram_id=telegram_id_int).first()
            
            if not user:
                print(f"❌ User with telegram_id {telegram_id} not found")
                print("Creating new user with admin role...")
                user = User(
                    telegram_id=telegram_id_int,
                    web_role='admin',
                    bot_role='premium'
                )
                db.session.add(user)
                db.session.commit()
                print(f"✅ Created new user with telegram_id {telegram_id} and admin role")
            else:
                old_role = user.web_role
                user.web_role = 'admin'
                db.session.commit()
                print(f"✅ User {user.user_id} (telegram_id: {telegram_id}, username: {user.username})")
                print(f"   Role changed from '{old_role}' to 'admin'")
            
            return True
        except ValueError:
            print(f"❌ Invalid telegram_id: {telegram_id}. Must be a number.")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_admin.py <telegram_id>")
        sys.exit(1)
    
    telegram_id = sys.argv[1]
    success = add_admin(telegram_id)
    sys.exit(0 if success else 1)

