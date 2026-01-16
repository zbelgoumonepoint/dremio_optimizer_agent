"""Loader for storage-layer metadata (Data Type 6)."""
from typing import Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient


class StorageLoader(BaseLoader):
    """Loads storage-layer metadata (file counts, sizes, partition layout)."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str) -> Dict[str, Any]:
        """Load storage metadata for a dataset.

        Args:
            source: dataset_id or path

        Returns:
            Storage metadata
        """
        dataset = self.client.get_catalog_by_id(source)
        return self._extract_storage_info(source, dataset)

    def _extract_storage_info(self, dataset_id: str, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Extract storage information from dataset."""
        # This is simplified - actual storage info would come from dataset statistics
        dataset_config = dataset.get("datasetConfig", {})

        return {
            "dataset_id": dataset_id,
            "file_count": 0,  # Would extract from stats
            "total_size_bytes": 0,  # Would extract from stats
            "avg_file_size_mb": 0,  # Calculated
            "partition_count": len(dataset_config.get("partitionColumns", [])),
            "file_format": dataset_config.get("format"),
        }
