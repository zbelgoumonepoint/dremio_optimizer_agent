"""Loader for user/workload context (Data Type 7)."""
from typing import List, Dict, Any
from .base_loader import BaseLoader
from ...clients.dremio_client import DremioClient


class WorkloadLoader(BaseLoader):
    """Loads user and workload context information."""

    def __init__(self, client: DremioClient):
        self.client = client

    def load(self, source: str = None) -> List[Dict[str, Any]]:
        """Load workload context.

        Args:
            source: Not used for batch loading

        Returns:
            List of workload context entries
        """
        # Load query history with user information
        queries = self.client.get_query_history(limit=1000)

        # Group by user and extract patterns
        user_patterns = {}
        for query in queries:
            user = query.get("user")
            if user not in user_patterns:
                user_patterns[user] = {"query_count": 0, "client_types": set(), "queue_names": set()}

            user_patterns[user]["query_count"] += 1
            if query.get("clientType"):
                user_patterns[user]["client_types"].add(query["clientType"])
            if query.get("queueName"):
                user_patterns[user]["queue_names"].add(query["queueName"])

        # Transform to list format
        return [
            {
                "user": user,
                "query_count": info["query_count"],
                "client_types": list(info["client_types"]),
                "queue_names": list(info["queue_names"]),
            }
            for user, info in user_patterns.items()
        ]
