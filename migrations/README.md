# GitGuide Database Migrations

This folder contains database migration scripts that have been executed on the production database.

## Migration History

### ✅ `001_migrate_database_EXECUTED.py`
**Status**: EXECUTED  
**Date**: Previously executed  
**Purpose**: 
- Added rich learning content features to existing schema
- Added `project_overview`, `repo_name`, `tech_stack`, `is_processed` columns to projects table
- Added new tables for concepts, subtopics, tasks
- Enhanced database structure for AI-generated learning paths

### ✅ `002_add_days_migration_EXECUTED.py`
**Status**: EXECUTED  
**Date**: 2025-07-24  
**Purpose**:
- Added 14-day learning progression system
- Created `days` table with progressive unlocking system
- Added `day_id` foreign key to `concepts` table
- Created 14 days for existing projects (only Day 1 unlocked)
- New hierarchy: Project → Days (14) → Concepts → Subtopics → Tasks

## Current Database Schema

```
📚 Project
├── 📅 Days (14) - Progressive unlocking system
│   ├── 📖 Concepts - Learning concepts for each day
│   │   ├── 📝 Subtopics - Detailed breakdowns  
│   │   │   └── ✅ Tasks - Actionable learning items
```

## Important Notes

⚠️ **DO NOT RE-RUN THESE MIGRATIONS** - They have already been executed.

✅ **New Projects**: Automatically get 14 days created via `create_14_days_for_project()` function.

✅ **Rollback**: Each migration includes rollback functionality if needed (use with extreme caution).

## For New Developers

If setting up a fresh database:
1. Run the main database setup: `python -c "from app.database_models import Base; from app.database_config import engine; import asyncio; asyncio.run(Base.metadata.create_all(engine))"`
2. These migrations are NOT needed for fresh setups - the schema is already up to date.

## For Production Deployments

If deploying to a new environment with existing data:
1. Check if migrations are needed by inspecting the database schema
2. Run migrations in order if the environment doesn't have the latest schema
3. Mark migrations as executed in your deployment notes 