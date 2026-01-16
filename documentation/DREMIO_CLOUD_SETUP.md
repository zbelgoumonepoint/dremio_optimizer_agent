# Dremio Cloud Setup Guide

## Your Dremio Cloud Configuration

Based on your account information:

- **Organization ID**: `6e57e93c-07da-4758-9684-3d58fa71dabc`
- **Project ID**: `a9096569-7b74-4ca3-b540-29dfb04d2637`
- **Region**: AWS US West (Oregon)
- **API Endpoint**: `https://api.dremio.cloud`
- **JDBC Connection**: `jdbc:arrow-flight-sql://data.dremio.cloud:443?useEncryption=true&CATALOG=a9096569-7b74-4ca3-b540-29dfb04d2637`

## Quick Setup Steps

### 1. Generate Personal Access Token

1. Go to **Dremio Cloud Console**: https://app.dremio.cloud
2. Log in with your admin account
3. Click your **profile icon** (top-right)
4. Select **Account Settings**
5. Navigate to **Personal Access Tokens**
6. Click **New Token**
7. Name: "Dremio Optimizer Agent"
8. Expiration: Choose based on your security policy (30-90 days recommended)
9. Click **Create**
10. **IMPORTANT**: Copy the token immediately - format will be like `dremio_pat_xxxxxxxxxxxxx`

### 2. Configure .env File

I've already created a `.env` file for you with your Project ID. You just need to add your token:

```bash
cd dremio_optimizer_agent
```

Edit `.env` and replace `YOUR_PERSONAL_ACCESS_TOKEN_HERE` with your actual token:

```env
# Dremio Cloud Configuration
DREMIO_URL=https://api.dremio.cloud
DREMIO_TOKEN=dremio_pat_your_actual_token_here
DREMIO_PROJECT_ID=a9096569-7b74-4ca3-b540-29dfb04d2637
```

### 3. Setup PostgreSQL Database

```bash
# Create database
createdb dremio_optimizer

# Initialize tables
python scripts/setup_db.py
```

Expected output:
```
Initializing database tables...
✓ Database tables created successfully!

Tables created:
  - queries
  - query_profiles
  - baselines
  - recommendations
  - measurements
  - reflection_metadata
  - dataset_metadata
```

### 4. Test Connection

```bash
python test_connection.py
```

Expected output:
```
Testing Dremio Connection
============================================================

Configuration:
  Dremio URL: https://api.dremio.cloud
  Authentication: Token (dremio_pat_xxxxx...)

1. Initializing Dremio client...
2. Testing connection to Dremio...
   ✓ Connected successfully!
   ✓ Dremio version: XX.X.X

3. Testing query history access...
   ✓ Successfully fetched N recent queries

✓ All tests passed! Your Dremio connection is working.
```

### 5. Collect Data

```bash
python scripts/test_collection.py
```

This will:
- Connect to your Dremio Cloud instance
- Fetch recent query history
- Collect query profiles
- Store data in PostgreSQL

## Dremio Cloud API Differences

The client automatically detects Dremio Cloud and adjusts:

| Feature | On-Prem | Dremio Cloud |
|---------|---------|--------------|
| **Base URL** | `http://localhost:9047` | `https://api.dremio.cloud` |
| **Auth Method** | Username/Password or Token | **Token only** |
| **Auth Header** | `Authorization: _dremioTOKEN` | `Authorization: Bearer TOKEN` |
| **Project Context** | Not required | Project ID required for some APIs |

## Usage Examples

### Example 1: Initialize Client for Dremio Cloud

```python
from src.clients.dremio_client import DremioClient

# Automatically uses settings from .env
client = DremioClient()

# Or pass explicitly
client = DremioClient(
    base_url="https://api.dremio.cloud",
    token="dremio_pat_xxxxxxxxxxxxx",
    project_id="a9096569-7b74-4ca3-b540-29dfb04d2637"
)

# Fetch query history
queries = client.get_query_history(limit=100)
print(f"Found {len(queries)} queries")
```

### Example 2: Collect Data from Dremio Cloud

```python
from src.data.collectors.dremio_collector import DremioCollector

collector = DremioCollector()

# Collect last 24 hours
stats = collector.collect_all(lookback_hours=24)
print(f"Collected: {stats}")
```

### Example 3: Query Collected Data

```python
from src.database.connection import get_db_session
from src.database.repositories.query_repository import QueryRepository

with get_db_session() as session:
    query_repo = QueryRepository(session)

    # Get slow queries
    slow_queries = query_repo.get_slow_queries(threshold_ms=10000, limit=10)

    for query in slow_queries:
        print(f"Duration: {query.duration_ms}ms")
        print(f"SQL: {query.sql_text[:100]}...")
        print("-" * 60)
```

## Troubleshooting

### Error: 401 Unauthorized

**Cause**: Invalid or expired token

**Solution**:
1. Verify token is correct in `.env`
2. Check token hasn't expired
3. Generate new token if needed

### Error: 403 Forbidden

**Cause**: Token lacks required permissions

**Solution**:
1. Ensure token was created by admin user
2. Check project permissions in Dremio Cloud Console
3. Verify Project ID is correct

### Error: Connection timeout

**Cause**: Network/firewall issue

**Solution**:
1. Check internet connectivity
2. Verify you can access https://api.dremio.cloud in browser
3. Check firewall/proxy settings

### No queries returned

**Cause**: Empty query history or insufficient permissions

**Solution**:
1. Run some queries in Dremio Cloud first
2. Verify token has permission to view job history
3. Try longer lookback: `collector.collect_all(lookback_hours=168)` # 7 days

## Important Notes for Dremio Cloud

1. **Token Authentication Only**: Dremio Cloud doesn't support username/password via API
2. **Project Context**: Some APIs require Project ID for multi-project accounts
3. **Rate Limits**: Dremio Cloud may have API rate limits (currently generous)
4. **Data Residency**: Your data stays in AWS US-West-2 (Oregon)

## API Endpoints Reference

### Dremio Cloud REST API

All endpoints use: `https://api.dremio.cloud`

- **Job History**: `GET /api/v3/job`
- **Job Profile**: `GET /api/v3/job/{jobId}`
- **Catalog**: `GET /api/v3/catalog`
- **Reflections**: `GET /api/v3/reflection`
- **System Info**: `GET /apiv2/server_status`

### Headers Required

```http
Authorization: Bearer dremio_pat_xxxxxxxxxxxxx
Content-Type: application/json
```

## Testing with curl

Test your token directly:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.dremio.cloud/api/v3/job?limit=1
```

Should return JSON with recent query.

## Security Best Practices

1. ✅ **Rotate tokens** every 30-90 days
2. ✅ **Use separate tokens** for dev/staging/prod
3. ✅ **Never commit** `.env` to git (already in .gitignore)
4. ✅ **Monitor token usage** in Dremio Cloud Console
5. ✅ **Revoke compromised tokens** immediately

## Next Steps

Once your connection is working:

1. ✅ **Verify data collection** - Run `python scripts/test_collection.py`
2. ✅ **Check database** - Query PostgreSQL to see collected data
3. ✅ **Proceed to Phase 2** - Implement Analysis Engine (detectors)

## Support

Dremio Cloud Support:
- Documentation: https://docs.dremio.com/cloud/
- Support Portal: https://support.dremio.com
- Community Forum: https://community.dremio.com

---

**Your configuration is ready!** Just add your Personal Access Token to the `.env` file and test the connection.
