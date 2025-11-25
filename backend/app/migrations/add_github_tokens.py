"""
Database migration: Add GitHubToken table
Run this script to update the database schema.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import engine, Base
from app.models import GitHubToken  # Import to register the table


async def migrate():
    """Create all tables that don't exist yet."""
    async with engine.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Database migration completed successfully")
        print("✓ GitHubToken table created (if it didn't exist)")


if __name__ == "__main__":
    asyncio.run(migrate())

