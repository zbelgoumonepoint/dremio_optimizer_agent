"""Loader for Dremio query history (Data Type 1)."""
from typing import List, Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient
from datetime import datetime


class QueryLoader(BaseLoader):
    """Loads SQL query text and metadata from Dremio history."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str = None) -> List[Dict[str, Any]]:
        """Load query history.

        Args:
            source: Not used for batch loading

        Returns:
            List of queries with metadata
        """
        queries = self.client.get_query_history(limit=1000)

        return [self._transform_query(q) for q in queries]

    def _transform_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Dremio query data to internal format."""
        # Parse timestamps
        start_time = None
        end_time = None
        duration_ms = None

        if query_data.get("startTime"):
            start_time = datetime.fromtimestamp(query_data["startTime"] / 1000.0)

        if query_data.get("endTime"):
            end_time = datetime.fromtimestamp(query_data["endTime"] / 1000.0)

        if start_time and end_time:
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "job_id": query_data.get("id"),
            "sql_text": query_data.get("sql", ""),
            "user": query_data.get("user"),
            "queue_name": query_data.get("queueName"),
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": duration_ms,
            "status": query_data.get("jobState"),
        }
