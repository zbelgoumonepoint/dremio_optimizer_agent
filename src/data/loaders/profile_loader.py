"""Loader for query profiles and plans (Data Type 2)."""
from typing import Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient


class ProfileLoader(BaseLoader):
    """Loads query execution profiles and plans."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str) -> Dict[str, Any]:
        """Load query profile by job_id.

        Args:
            source: job_id of the query

        Returns:
            Profile with extracted metrics
        """
        profile = self.client.get_query_profile(source)
        return self._transform_profile(source, profile)

    def _transform_profile(self, job_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Dremio profile data to internal format."""
        # Extract key metrics from profile
        # Note: Actual extraction depends on Dremio's profile structure
        # This is a simplified version

        query_profile = profile_data.get("queryProfile", {})
        plan_phases = profile_data.get("planPhases", [])

        # Extract memory metrics
        memory_allocated = query_profile.get("memoryAllocated", 0)
        peak_memory = query_profile.get("peakMemory", 0)

        # Extract row counts
        rows_scanned = query_profile.get("rowsScanned", 0)
        rows_returned = query_profile.get("rowsReturned", 0)

        # Extract data scanned
        data_scanned_bytes = query_profile.get("dataScanned", 0)
        data_scanned_mb = data_scanned_bytes / (1024 * 1024) if data_scanned_bytes else 0

        # Extract reflection info
        reflection_info = self._extract_reflection_usage(profile_data)

        # Extract partition info
        partition_info = self._extract_partition_info(profile_data)

        return {
            "job_id": job_id,
            "profile_json": profile_data,
            "plan_json": plan_phases,
            "total_memory_mb": memory_allocated / (1024 * 1024) if memory_allocated else 0,
            "peak_memory_mb": peak_memory / (1024 * 1024) if peak_memory else 0,
            "rows_scanned": rows_scanned,
            "rows_returned": rows_returned,
            "data_scanned_mb": data_scanned_mb,
            "reflection_used": reflection_info.get("reflection_id"),
            "reflection_hit": reflection_info.get("hit", False),
            "partitions_pruned": partition_info.get("partitions_pruned", 0),
            "partitions_scanned": partition_info.get("partitions_scanned", 0),
        }

    def _extract_reflection_usage(self, profile: Dict) -> Dict:
        """Extract which reflections were used."""
        # Parse profile JSON to find reflection usage
        # This is simplified - actual implementation depends on Dremio's structure
        acceleration = profile.get("acceleration", {})
        if acceleration.get("reflections"):
            reflections = acceleration["reflections"]
            if reflections:
                return {"reflection_id": reflections[0].get("id"), "hit": True}
        return {"reflection_id": None, "hit": False}

    def _extract_partition_info(self, profile: Dict) -> Dict:
        """Extract partition pruning information."""
        # Parse plan to identify partition filters
        # This is simplified - actual implementation depends on Dremio's structure
        scan_info = profile.get("scanInfo", {})
        return {
            "partitions_available": scan_info.get("totalPartitions", 0),
            "partitions_scanned": scan_info.get("scannedPartitions", 0),
            "partitions_pruned": scan_info.get("totalPartitions", 0) - scan_info.get("scannedPartitions", 0),
        }
