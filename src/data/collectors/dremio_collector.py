"""Orchestrates all data collection from Dremio."""
from typing import Dict
from ..loaders.query_loader import QueryLoader
from ..loaders.profile_loader import ProfileLoader
from ..loaders.metadata_loader import MetadataLoader
from ..loaders.reflection_metadata_loader import ReflectionMetadataLoader
from ...clients.dremio_client import DremioClient
from ...database.connection import get_db_session
from ...database.repositories.query_repository import QueryRepository
from ...database.repositories.profile_repository import ProfileRepository
from ...database.models import ReflectionMetadata, DatasetMetadata


class DremioCollector:
    """Collects and persists all Dremio data."""

    def __init__(self, client: DremioClient = None):
        self.client = client or DremioClient()

        # Initialize loaders
        self.query_loader = QueryLoader(self.client)
        self.profile_loader = ProfileLoader(self.client)
        self.metadata_loader = MetadataLoader(self.client)
        self.reflection_loader = ReflectionMetadataLoader(self.client)

    def collect_all(self, lookback_hours: int = 24) -> Dict[str, int]:
        """Collect all data types and persist to database.

        Args:
            lookback_hours: Hours of history to collect (not currently used, collects most recent)

        Returns:
            Dict with counts of collected items
        """
        stats = {}

        with get_db_session() as session:
            query_repo = QueryRepository(session)
            profile_repo = ProfileRepository(session)

            # 1. Collect queries
            print(f"Collecting queries from last {lookback_hours} hours...")
            queries = self.query_loader.load()
            print(f"Found {len(queries)} queries")

            # Insert queries (handle duplicates)
            inserted_queries = 0
            for query in queries:
                try:
                    # Check if already exists
                    existing = query_repo.get_by_job_id(query["job_id"])
                    if not existing:
                        query_repo.insert_from_dict(query)
                        inserted_queries += 1
                except Exception as e:
                    print(f"Error inserting query {query.get('job_id')}: {e}")
                    continue

            stats["queries"] = inserted_queries
            print(f"Inserted {inserted_queries} new queries")

            # 2. Collect profiles for recent queries (top 100)
            print("Collecting query profiles...")
            profile_count = 0
            for query in queries[:100]:  # Top 100 most recent
                job_id = query["job_id"]
                try:
                    # Check if profile already exists
                    existing_profile = profile_repo.get_by_job_id(job_id)
                    if not existing_profile:
                        profile = self.profile_loader.load(job_id)
                        profile_repo.insert_from_dict(profile)
                        profile_count += 1
                except Exception as e:
                    print(f"Error collecting profile for {job_id}: {e}")
                    continue

            stats["profiles"] = profile_count
            print(f"Collected {profile_count} profiles")

            # 3. Collect reflection metadata
            print("Collecting reflection metadata...")
            try:
                reflections = self.reflection_loader.load()
                reflection_count = 0

                for reflection_data in reflections:
                    # Check if exists
                    existing = (
                        session.query(ReflectionMetadata)
                        .filter(ReflectionMetadata.reflection_id == reflection_data["reflection_id"])
                        .first()
                    )

                    if existing:
                        # Update existing
                        for key, value in reflection_data.items():
                            setattr(existing, key, value)
                    else:
                        # Insert new
                        reflection = ReflectionMetadata(**reflection_data)
                        session.add(reflection)
                        reflection_count += 1

                session.flush()
                stats["reflections"] = reflection_count
                print(f"Collected {reflection_count} reflections")
            except Exception as e:
                print(f"Error collecting reflections: {e}")
                stats["reflections"] = 0

            # 4. Collect dataset metadata
            print("Collecting dataset metadata...")
            try:
                datasets = self.metadata_loader.load()
                dataset_count = 0

                for dataset_data in datasets[:100]:  # Limit to 100 datasets for now
                    try:
                        # Check if exists
                        existing = (
                            session.query(DatasetMetadata)
                            .filter(DatasetMetadata.dataset_id == dataset_data["dataset_id"])
                            .first()
                        )

                        if existing:
                            # Update existing
                            for key, value in dataset_data.items():
                                setattr(existing, key, value)
                        else:
                            # Insert new
                            dataset = DatasetMetadata(**dataset_data)
                            session.add(dataset)
                            dataset_count += 1
                    except Exception as e:
                        print(f"Error inserting dataset {dataset_data.get('dataset_id')}: {e}")
                        continue

                session.flush()
                stats["datasets"] = dataset_count
                print(f"Collected {dataset_count} datasets")
            except Exception as e:
                print(f"Error collecting datasets: {e}")
                stats["datasets"] = 0

        print("\nCollection complete!")
        return stats

    def collect_query(self, job_id: str) -> Dict[str, bool]:
        """Collect data for a specific query.

        Args:
            job_id: Dremio job ID

        Returns:
            Dict with collection status
        """
        result = {"query": False, "profile": False}

        with get_db_session() as session:
            query_repo = QueryRepository(session)
            profile_repo = ProfileRepository(session)

            # Collect query if not exists
            existing_query = query_repo.get_by_job_id(job_id)
            if not existing_query:
                try:
                    profile = self.client.get_query_profile(job_id)
                    # Extract query info from profile
                    query_loader = QueryLoader(self.client)
                    queries = query_loader.load()
                    matching_query = next((q for q in queries if q["job_id"] == job_id), None)

                    if matching_query:
                        query_repo.insert_from_dict(matching_query)
                        result["query"] = True
                except Exception as e:
                    print(f"Error collecting query {job_id}: {e}")

            # Collect profile if not exists
            existing_profile = profile_repo.get_by_job_id(job_id)
            if not existing_profile:
                try:
                    profile = self.profile_loader.load(job_id)
                    profile_repo.insert_from_dict(profile)
                    result["profile"] = True
                except Exception as e:
                    print(f"Error collecting profile for {job_id}: {e}")

        return result
