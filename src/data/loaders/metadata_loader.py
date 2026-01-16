"""Loader for table/dataset metadata (Data Type 3)."""
from typing import List, Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient


class MetadataLoader(BaseLoader):
    """Loads table/dataset metadata from Dremio catalog."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str = None) -> List[Dict[str, Any]]:
        """Load dataset metadata.

        Args:
            source: Optional dataset_id or path

        Returns:
            List of dataset metadata
        """
        if source:
            # Load specific dataset
            dataset = self.client.get_catalog_by_id(source)
            return [self._transform_dataset(dataset)]
        else:
            # Load all datasets via search
            datasets = self.client.search_datasets(limit=1000)
            return [self._transform_dataset(ds) for ds in datasets if ds.get("type") in ["DATASET", "PHYSICAL_DATASET"]]

    def _transform_dataset(self, dataset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Dremio dataset data to internal format."""
        # Extract dataset metadata
        dataset_config = dataset_data.get("datasetConfig", {})
        fields = dataset_config.get("fields", [])

        return {
            "dataset_id": dataset_data.get("id"),
            "dataset_path": ".".join(dataset_data.get("path", [])),
            "dataset_type": dataset_data.get("type"),
            "columns": [{"name": f.get("name"), "type": f.get("type")} for f in fields],
            "partition_columns": self._extract_partition_columns(dataset_config),
            "sort_columns": self._extract_sort_columns(dataset_config),
            "file_format": dataset_config.get("format"),
            "total_size_mb": 0,  # Would need to extract from storage stats
            "row_count": 0,  # Would need to extract from stats
            "file_count": 0,  # Would need to extract from storage stats
        }

    def _extract_partition_columns(self, config: Dict) -> List[str]:
        """Extract partition columns from dataset config."""
        # Simplified extraction
        return config.get("partitionColumns", [])

    def _extract_sort_columns(self, config: Dict) -> List[str]:
        """Extract sort columns from dataset config."""
        # Simplified extraction
        return config.get("sortColumns", [])
