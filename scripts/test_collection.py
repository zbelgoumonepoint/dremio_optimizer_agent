"""Test data collection from Dremio."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.dremio_collector import DremioCollector
from src.clients.dremio_client import DremioClient


def main():
    """Test data collection."""
    print("Testing Dremio connection and data collection...")
    print("=" * 60)

    try:
        # Initialize client
        print("\n1. Initializing Dremio client...")
        client = DremioClient()

        # Test connection
        print("2. Testing Dremio connection...")
        try:
            system_info = client.get_system_info()
            print(f"   ✓ Connected to Dremio version: {system_info.get('version', 'unknown')}")
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
            sys.exit(1)

        # Initialize collector
        print("\n3. Initializing data collector...")
        collector = DremioCollector(client)

        # Run collection
        print("\n4. Starting data collection...")
        print("-" * 60)
        stats = collector.collect_all(lookback_hours=24)

        # Print results
        print("\n" + "=" * 60)
        print("Collection Summary:")
        print("=" * 60)
        for key, count in stats.items():
            print(f"  {key.capitalize()}: {count}")

        print("\n✓ Data collection completed successfully!")

    except Exception as e:
        print(f"\n✗ Error during collection: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
