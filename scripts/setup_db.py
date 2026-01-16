"""Database initialization script."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import init_db


def main():
    """Initialize database tables."""
    print("Initializing database tables...")

    try:
        init_db()
        print("✓ Database tables created successfully!")
        print("\nTables created:")
        print("  - queries")
        print("  - query_profiles")
        print("  - baselines")
        print("  - recommendations")
        print("  - measurements")
        print("  - reflection_metadata")
        print("  - dataset_metadata")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
