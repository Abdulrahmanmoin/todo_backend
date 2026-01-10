# Database Setup, Migrations, and Seeding

This directory contains all the database setup, migration, and seeding functionality for the Todo application using SQLModel and Alembic with Neon PostgreSQL.

## Files Structure

- `connection.py` - Database connection configuration with both async and sync engines
- `init_db.py` - Database initialization script with migration support
- `seed_db.py` - Database seeding script with sample data for testing
- `alembic/` - Alembic configuration and migration files
  - `env.py` - Alembic environment configuration
  - `script.py.mako` - Template for migration files
- `scripts/run_migrations.py` - Command-line script for managing migrations
- `scripts/setup_db_with_seed.py` - Combined script for initialization and seeding

## Database Configuration

The application uses Neon PostgreSQL with the following configuration:
- Async engine for application operations (using asyncpg)
- Sync engine for migrations and sync operations
- Connection pooling with configurable size and overflow
- SSL mode configuration for Neon compatibility

## Migration Commands

### Using the initialization script:
```bash
# Run migrations using alembic (default)
python backend/src/database/init_db.py

# Create tables directly without migrations
python backend/src/database/init_db.py --direct

# Create initial migration file
python backend/src/database/init_db.py --create-initial
```

### Using the migration script:
```bash
# Upgrade to latest migration
python backend/scripts/run_migrations.py upgrade

# Create a new migration
python backend/scripts/run_migrations.py create --message "Add new field to user"

# Show current migration status
python backend/scripts/run_migrations.py current

# Show migration history
python backend/scripts/run_migrations.py history

# Downgrade to a specific revision
python backend/scripts/run_migrations.py downgrade --revision <revision_id>
```

## Seeding Commands

### Using the seeding script:
```bash
# Seed the database with sample data
python backend/src/database/seed_db.py --seed

# Clear all data from the database (WARNING: destructive operation)
python backend/src/database/seed_db.py --clear

# Clear and re-seed the database
python backend/src/database/seed_db.py --reseed
```

### Using the combined setup script:
```bash
# Initialize database and seed with sample data (using migrations by default)
python backend/scripts/setup_db_with_seed.py

# Initialize database and seed with sample data (using direct table creation)
python backend/scripts/setup_db_with_seed.py --direct
```

## Sample Data

The seeding script creates the following sample data:

### Users
- **admin@example.com** (username: admin) - Password: AdminPass123!
- **testuser1@example.com** (username: testuser1) - Password: TestPass123!
- **testuser2@example.com** (username: testuser2) - Password: TestPass456@
- **demo@example.com** (username: demo) - Password: DemoPass789#

### Tasks
Each user gets several tasks with different completion statuses:
- Some completed tasks with completion timestamps
- Some pending tasks
- Various titles and descriptions for testing

## Environment Variables

The database configuration supports the following environment variables:

```bash
# Direct database URL (preferred)
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database?ssl=require

# Individual components (fallback)
DB_USER=todo_user
DB_PASSWORD=your_password
DB_HOST=ep-todo-db.us-east-1.aws.neon.tech
DB_NAME=todo_db
DB_SSL_MODE=require
DB_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=300
ENVIRONMENT=development

# JWT configuration for auth
JWT_SECRET_KEY=your-super-secret-jwt-key
```

## Development vs Production

- In development mode (`ENVIRONMENT=development`), the application can drop and recreate tables
- In production mode, only migrations are used to modify the schema
- Connection pooling is configured appropriately for each environment

## Models

The database includes the following models:
- `User` - User accounts with authentication fields
- `Task` - Task items associated with users

Both models use UUID primary keys and include proper relationship definitions.