"""Dremio REST API client."""
import requests
from typing import Dict, List, Any, Optional
from ..config.settings import get_settings
import time
import certifi


class DremioClient:
    """Client for Dremio REST API interactions."""

    def __init__(self, base_url: str = None, username: str = None, password: str = None, token: str = None, project_id: str = None, verify_ssl: bool = None):
        settings = get_settings()
        self.base_url = base_url or settings.dremio_url
        self.username = username or settings.dremio_username
        self.password = password or settings.dremio_password
        self._token = token or getattr(settings, 'dremio_token', None)  # Support pre-generated token
        self._token_expiry = 0 if not self._token else float('inf')  # Pre-generated tokens don't expire in client
        self.project_id = project_id or getattr(settings, 'dremio_project_id', None)  # For Dremio Cloud
        self.is_cloud = "dremio.cloud" in self.base_url  # Detect if using Dremio Cloud

        # SSL verification - use certifi if enabled, False if disabled
        if verify_ssl is not None:
            self.verify_ssl = certifi.where() if verify_ssl else False
        else:
            self.verify_ssl = certifi.where() if settings.dremio_verify_ssl else False

    def _authenticate(self) -> str:
        """Authenticate and get token."""
        response = requests.post(
            f"{self.base_url}/apiv2/login",
            json={"userName": self.username, "password": self.password},
            verify=self.verify_ssl
        )
        response.raise_for_status()
        self._token = response.json()["token"]
        # Token typically expires after 24 hours, set expiry to 23 hours from now
        self._token_expiry = time.time() + (23 * 3600)
        return self._token

    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        # Check if token is expired or missing
        if not self._token or time.time() >= self._token_expiry:
            self._authenticate()

        # Dremio Cloud uses Bearer token, on-prem uses _dremio prefix
        auth_header = f"Bearer {self._token}" if self.is_cloud else f"_dremio{self._token}"

        return {"Authorization": auth_header, "Content-Type": "application/json"}

    def _request(
        self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None, retries: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries):
            try:
                response = requests.request(
                    method=method, url=url, headers=self._headers(), params=params, json=json_data, timeout=30,
                    verify=self.verify_ssl
                )

                # If 401, token might be expired, retry with new token
                if response.status_code == 401 and attempt < retries - 1:
                    self._authenticate()
                    continue

                response.raise_for_status()
                return response.json() if response.content else {}

            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500 and attempt < retries - 1:
                    # Retry on 5xx errors
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                raise
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise

        raise Exception(f"Failed to {method} {endpoint} after {retries} retries")

    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query via Dremio Cloud SQL API.

        Args:
            sql: SQL query to execute

        Returns:
            Dict with job_id and results

        Note:
            This is primarily for Dremio Cloud. For on-prem, use get_query_history instead.
        """
        if not self.is_cloud or not self.project_id:
            raise Exception("execute_sql is only supported for Dremio Cloud")

        endpoint = f"/v0/projects/{self.project_id}/sql"
        response = self._request("POST", endpoint, json_data={"sql": sql})
        return response

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a SQL job.

        Args:
            job_id: Job ID from execute_sql

        Returns:
            Dict with job status including jobState, rowCount, errorMessage
        """
        if not self.is_cloud or not self.project_id:
            raise Exception("get_job_status is only supported for Dremio Cloud")

        endpoint = f"/v0/projects/{self.project_id}/job/{job_id}"
        response = self._request("GET", endpoint)
        return response

    def wait_for_job(self, job_id: str, timeout: int = 30, poll_interval: float = 0.5) -> Dict[str, Any]:
        """Wait for job to complete.

        Args:
            job_id: Job ID to wait for
            timeout: Maximum seconds to wait
            poll_interval: Seconds between status checks

        Returns:
            Final job status

        Raises:
            Exception: If job fails or times out
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            state = status.get("jobState")

            if state == "COMPLETED":
                return status
            elif state == "FAILED":
                error_msg = status.get("errorMessage", "Unknown error")
                raise Exception(f"Job {job_id} failed: {error_msg}")
            elif state == "CANCELED":
                raise Exception(f"Job {job_id} was canceled")

            time.sleep(poll_interval)

        raise Exception(f"Job {job_id} timed out after {timeout} seconds")

    def get_job_results(self, job_id: str, offset: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Get results from a completed SQL job.

        Args:
            job_id: Job ID from execute_sql
            offset: Result offset for pagination
            limit: Maximum rows to return

        Returns:
            Dict with job results
        """
        if not self.is_cloud or not self.project_id:
            raise Exception("get_job_results is only supported for Dremio Cloud")

        endpoint = f"/v0/projects/{self.project_id}/job/{job_id}/results"
        params = {"offset": offset, "limit": limit}
        response = self._request("GET", endpoint, params=params)
        return response

    def get_query_history(self, limit: int = 100, offset: int = 0, filter_expr: str = None) -> List[Dict[str, Any]]:
        """Fetch query history.

        Args:
            limit: Maximum number of jobs to return
            offset: Offset for pagination
            filter_expr: Optional filter expression (e.g., 'qt==UI')

        Returns:
            List of job dictionaries

        Note:
            For Dremio Cloud, this queries the sys.project.history.jobs system table.
            For on-prem, this uses the /api/v3/job endpoint.
        """
        # Dremio Cloud uses SQL API to query system tables
        if self.is_cloud and self.project_id:
            # Query the system table for job history
            # For Dremio Cloud, we don't need a WHERE clause for recent history
            # The table already contains recent jobs (last 30 days typically)
            sql = f"""
            SELECT
                job_id,
                user_name,
                query,
                submitted_ts,
                final_state_ts,
                status,
                query_type,
                queue_name,
                engine,
                rows_returned,
                rows_scanned,
                bytes_scanned,
                execution_cpu_time_ns,
                accelerated
            FROM sys.project.history.jobs
            ORDER BY submitted_ts DESC
            LIMIT {limit}
            OFFSET {offset}
            """

            # Execute SQL query
            sql_response = self.execute_sql(sql)
            job_id = sql_response.get("id")

            if not job_id:
                return []

            # Wait for query to complete
            self.wait_for_job(job_id)

            # Get results
            results_response = self.get_job_results(job_id)
            rows = results_response.get("rows", [])

            # Transform to match expected format
            jobs = []
            for row in rows:
                # Calculate duration if we have both timestamps
                duration_ms = None
                if row.get("submitted_ts") and row.get("final_state_ts"):
                    try:
                        # Timestamps are in ISO format strings
                        from datetime import datetime as dt
                        start = dt.fromisoformat(row["submitted_ts"].replace('Z', '+00:00'))
                        end = dt.fromisoformat(row["final_state_ts"].replace('Z', '+00:00'))
                        duration_ms = int((end - start).total_seconds() * 1000)
                    except:
                        pass

                jobs.append({
                    "id": row.get("job_id"),
                    "user": row.get("user_name"),
                    "sql": row.get("query"),
                    "startTime": row.get("submitted_ts"),
                    "endTime": row.get("final_state_ts"),
                    "status": row.get("status"),
                    "queryType": row.get("query_type"),
                    "queueName": row.get("queue_name"),
                    "engineName": row.get("engine"),
                    "rowsReturned": row.get("rows_returned"),
                    "rowsScanned": row.get("rows_scanned"),
                    "bytesScanned": row.get("bytes_scanned"),
                    "cpuTimeNs": row.get("execution_cpu_time_ns"),
                    "accelerated": row.get("accelerated"),
                    "durationMs": duration_ms,
                })

            return jobs
        else:
            # On-prem uses traditional REST API
            params = {"limit": limit, "offset": offset}
            if filter_expr:
                params["filter"] = filter_expr

            endpoint = "/api/v3/job"
            response = self._request("GET", endpoint, params=params)
            return response.get("jobs", [])

    def get_query_profile(self, job_id: str) -> Dict[str, Any]:
        """Fetch detailed query profile.

        Args:
            job_id: Dremio job ID

        Returns:
            Dict with full profile and plan JSON
        """
        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/job/{job_id}"
        else:
            endpoint = f"/api/v3/job/{job_id}"

        response = self._request("GET", endpoint)
        return response

    def get_query_sql(self, job_id: str) -> str:
        """Fetch SQL text for a query.

        Args:
            job_id: Dremio job ID

        Returns:
            SQL query text
        """
        job = self.get_query_profile(job_id)
        return job.get("sql", "")

    def get_reflections(self) -> List[Dict[str, Any]]:
        """Fetch all reflections.

        Returns:
            List of reflection metadata
        """
        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/reflection"
        else:
            endpoint = "/api/v3/reflection"

        response = self._request("GET", endpoint)
        return response.get("data", [])

    def get_reflection_by_id(self, reflection_id: str) -> Dict[str, Any]:
        """Fetch specific reflection by ID.

        Args:
            reflection_id: Reflection ID

        Returns:
            Reflection metadata
        """
        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/reflection/{reflection_id}"
        else:
            endpoint = f"/api/v3/reflection/{reflection_id}"

        response = self._request("GET", endpoint)
        return response

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Fetch catalog root.

        Returns:
            List of catalog entries
        """
        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/catalog"
        else:
            endpoint = "/api/v3/catalog"

        response = self._request("GET", endpoint)
        return response.get("data", [])

    def get_catalog_by_id(self, catalog_id: str) -> Dict[str, Any]:
        """Fetch specific catalog entity by ID.

        Args:
            catalog_id: Catalog entity ID

        Returns:
            Catalog entity details
        """
        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/catalog/{catalog_id}"
        else:
            endpoint = f"/api/v3/catalog/{catalog_id}"

        response = self._request("GET", endpoint)
        return response

    def get_dataset_by_path(self, path: List[str]) -> Dict[str, Any]:
        """Fetch dataset by path.

        Args:
            path: Dataset path as list (e.g., ['space', 'folder', 'dataset'])

        Returns:
            Dataset metadata
        """
        path_str = "/".join(path)

        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/catalog/by-path/{path_str}"
        else:
            endpoint = f"/api/v3/catalog/by-path/{path_str}"

        response = self._request("GET", endpoint)
        return response

    def search_datasets(self, query: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for datasets in catalog.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching datasets
        """
        params = {"limit": limit}
        if query:
            params["query"] = query

        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/catalog/search"
        else:
            endpoint = "/api/v3/catalog/search"

        response = self._request("GET", endpoint, params=params)
        return response.get("data", [])

    def get_job_stats(self, limit: int = 100) -> Dict[str, Any]:
        """Fetch job statistics.

        Args:
            limit: Maximum number of jobs to include in stats

        Returns:
            Job statistics summary
        """
        # Dremio Cloud uses different endpoint structure
        if self.is_cloud and self.project_id:
            endpoint = f"/v0/projects/{self.project_id}/job/stats"
        else:
            endpoint = "/api/v3/job/stats"

        response = self._request("GET", endpoint, params={"limit": limit})
        return response

    def get_system_info(self) -> Dict[str, Any]:
        """Fetch Dremio system information.

        Returns:
            System information

        Note:
            This endpoint may not be available on Dremio Cloud.
            For Cloud, returns basic connection status instead.
        """
        # Dremio Cloud may not have server_status endpoint
        # Use a lightweight endpoint to verify connectivity
        if self.is_cloud and self.project_id:
            # Use catalog endpoint as health check for Cloud
            try:
                response = self._request("GET", f"/v0/projects/{self.project_id}/catalog", params={"limit": 1})
                return {"status": "connected", "cloud": True, "project_id": self.project_id}
            except Exception as e:
                return {"status": "error", "cloud": True, "error": str(e)}
        else:
            response = self._request("GET", "/apiv2/server_status")
            return response
