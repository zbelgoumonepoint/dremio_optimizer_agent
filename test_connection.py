"""Test Dremio connection with your access token."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.clients.dremio_client import DremioClient
from src.config.settings import get_settings


def main():
    """Test Dremio connection."""
    print("Testing Dremio Connection")
    print("=" * 60)

    settings = get_settings()

    # Show configuration (without exposing full token)
    print(f"\nConfiguration:")
    print(f"  Dremio URL: {settings.dremio_url}")
    if settings.dremio_token:
        token_preview = settings.dremio_token[:20] + "..." if len(settings.dremio_token) > 20 else settings.dremio_token
        print(f"  Authentication: Token ({token_preview})")
    else:
        print(f"  Authentication: Username/Password ({settings.dremio_username})")

    print("\n" + "-" * 60)

    try:
        # Initialize client
        print("\n1. Initializing Dremio client...")
        client = DremioClient()

        # Test connection
        print("2. Testing connection to Dremio...")
        system_info = client.get_system_info()
        print(f"   ✓ Connected successfully!")
        print(f"   ✓ Dremio version: {system_info.get('version', 'unknown')}")

        # Test query history access
        print("\n3. Testing query history access...")
        queries = client.get_query_history(limit=5)
        print(f"   ✓ Successfully fetched {len(queries)} recent queries")

        if queries:
            print("\n   Recent queries:")
            for i, query in enumerate(queries[:3], 1):
                job_id = query.get("id", "unknown")
                sql = query.get("sql", "")
                sql_preview = sql[:60] + "..." if len(sql) > 60 else sql
                user = query.get("user", "unknown")
                state = query.get("jobState", "unknown")
                print(f"   {i}. [{state}] {job_id}")
                print(f"      User: {user}")
                print(f"      SQL: {sql_preview}")

        # Test catalog access
        print("\n4. Testing catalog access...")
        try:
            catalog = client.get_catalog()
            print(f"   ✓ Successfully accessed catalog ({len(catalog)} root entries)")
        except Exception as e:
            print(f"   ⚠ Catalog access limited: {e}")

        # Test reflections access
        print("\n5. Testing reflections access...")
        try:
            reflections = client.get_reflections()
            print(f"   ✓ Successfully accessed reflections ({len(reflections)} reflections)")
        except Exception as e:
            print(f"   ⚠ Reflections access limited: {e}")

        print("\n" + "=" * 60)
        print("✓ All tests passed! Your Dremio connection is working.")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Initialize database: python scripts/setup_db.py")
        print("  2. Collect data: python scripts/test_collection.py")

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify DREMIO_URL is correct in .env")
        print("  2. Check that your token is valid and not expired")
        print("  3. Ensure your token has proper permissions")
        print("  4. Try accessing Dremio UI to confirm it's reachable")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
