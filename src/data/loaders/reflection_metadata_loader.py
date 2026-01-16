"""Loader for reflection metadata (Data Type 4)."""
from typing import List, Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient
from datetime import datetime


class ReflectionMetadataLoader(BaseLoader):
    """Loads Dremio reflection metadata."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str = None) -> List[Dict[str, Any]]:
        """Load reflection metadata.

        Args:
            source: Optional reflection_id

        Returns:
            List of reflection metadata
        """
        if source:
            reflection = self.client.get_reflection_by_id(source)
            return [self._transform_reflection(reflection)]
        else:
            reflections = self.client.get_reflections()
            return [self._transform_reflection(r) for r in reflections]

    def _transform_reflection(self, reflection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Dremio reflection data to internal format."""
        # Parse timestamps
        last_used = None
        last_refresh = None

        if reflection_data.get("lastAccessTime"):
            last_used = datetime.fromtimestamp(reflection_data["lastAccessTime"] / 1000.0)

        if reflection_data.get("lastRefreshTime"):
            last_refresh = datetime.fromtimestamp(reflection_data["lastRefreshTime"] / 1000.0)

        return {
            "reflection_id": reflection_data.get("id"),
            "reflection_name": reflection_data.get("name"),
            "reflection_type": reflection_data.get("type"),  # "AGGREGATION" or "RAW"
            "dataset_id": reflection_data.get("datasetId"),
            "dataset_path": ".".join(reflection_data.get("datasetPath", [])),
            "hit_count": reflection_data.get("hitCount", 0),
            "last_used": last_used,
            "refresh_frequency": reflection_data.get("refreshPolicy", {}).get("refreshSchedule"),
            "last_refresh": last_refresh,
            "size_mb": reflection_data.get("currentSizeBytes", 0) / (1024 * 1024),
        }
