"""Loader for execution metrics (Data Type 5)."""
from typing import Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient


class MetricsLoader(BaseLoader):
    """Loads execution metrics from query profiles."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str) -> Dict[str, Any]:
        """Load execution metrics for a query.

        Args:
            source: job_id of the query

        Returns:
            Execution metrics
        """
        profile = self.client.get_query_profile(source)
        return self._extract_metrics(source, profile)

    def _extract_metrics(self, job_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract execution metrics from profile."""
        query_profile = profile.get("queryProfile", {})

        return {
            "job_id": job_id,
            "cpu_time_ms": query_profile.get("cpuTime", 0),
            "memory_allocated_mb": query_profile.get("memoryAllocated", 0) / (1024 * 1024),
            "peak_memory_mb": query_profile.get("peakMemory", 0) / (1024 * 1024),
            "disk_spill_mb": query_profile.get("diskSpill", 0) / (1024 * 1024),
            "runtime_ms": query_profile.get("runtime", 0),
            "setup_time_ms": query_profile.get("setupTime", 0),
            "wait_time_ms": query_profile.get("waitTime", 0),
        }
