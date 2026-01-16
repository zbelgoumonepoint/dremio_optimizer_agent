"""Base loader interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union


class BaseLoader(ABC):
    """Abstract base class for data loaders."""

    @abstractmethod
    def load(self, source: str = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Load data from source.

        Args:
            source: Optional source identifier (e.g., job_id, dataset_id)

        Returns:
            Loaded data as list of dicts or single dict
        """
        pass
