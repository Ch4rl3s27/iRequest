"""
Migration script to transition from monolithic app.py to clean architecture
"""

import os
import shutil
from datetime import datetime

def backup_original_files():
    """Backup original files before migration"""
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'app.py',
        'main.py',
        'config.py',
        'requirements.txt'
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(backup_dir, file))
            print(f"✅ Backed up {file}")
    
    print(f"📁 Backup created in {backup_dir}/")
    return backup_dir

def create_migration_guide():
    """Create migration guide for the user"""
    guide = """
# Migration Guide: From Monolithic to Clean Architecture

## What Changed

### 1. Database Models
- **Old**: Raw SQL queries in app.py
- **New**: SQLAlchemy models in `app/models/`
- **Files**: `app/models/user.py`, `app/models/clearance.py`

### 2. Business Logic
- **Old**: Mixed with route handlers
- **New**: Service classes in `app/services/`
- **Files**: `app/services/auth_service.py`, `app/services/email_service.py`

### 3. Route Handlers
- **Old**: All routes in app.py (4600+ lines)
- **New**: Modular blueprints in `app/routes/`
- **Files**: `app/routes/auth_routes.py`, `app/routes/student_routes.py`

### 4. Utilities
- **Old**: Helper functions scattered in app.py
- **New**: Organized utilities in `app/utils/`
- **Files**: `app/utils/validators.py`, `app/utils/helpers.py`, `app/utils/exceptions.py`

### 5. Configuration
- **Old**: Hardcoded values in app.py
- **New**: Environment-based configuration
- **Files**: Updated `config.py`, new `env.example`

## Next Steps

1. **Install new dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

3. **Test the new structure**:
   ```bash
   python main.py
   ```

4. **Gradually migrate routes**:
   - The old app.py is still available as backup
   - New routes are in `app/routes/`
   - Update your frontend to use new API endpoints

## Benefits

✅ **Maintainable**: Code is organized into logical modules
✅ **Testable**: Each component can be tested independently  
✅ **Scalable**: Easy to add new features without affecting existing code
✅ **Secure**: Proper input validation and error handling
✅ **Professional**: Follows Flask best practices

## API Changes

### Authentication
- **Old**: `/login` (POST)
- **New**: `/api/auth/login` (POST)

### Student Routes
- **Old**: `/api/student/me`
- **New**: `/api/student/me` (same, but cleaner implementation)

## Need Help?

If you encounter issues:
1. Check the backup files in the backup directory
2. Compare old vs new implementations
3. Update your frontend JavaScript to use new endpoints
"""
    
    with open('MIGRATION_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print("📖 Migration guide created: MIGRATION_GUIDE.md")

def main():
    """Main migration function"""
    print("🚀 Starting migration to clean architecture...")
    
    # Backup original files
    backup_dir = backup_original_files()
    
    # Create migration guide
    create_migration_guide()
    
    print("\n" + "="*50)
    print("✅ Migration preparation complete!")
    print("="*50)
    print(f"📁 Original files backed up to: {backup_dir}/")
    print("📖 Migration guide: MIGRATION_GUIDE.md")
    print("\nNext steps:")
    print("1. Install new dependencies: pip install -r requirements.txt")
    print("2. Set up environment variables: cp env.example .env")
    print("3. Test the new structure: python main.py")

if __name__ == '__main__':
    main()
