# Dremio Optimizer Agent - Setup Guide

## Prerequisites

1. **Python 3.11+**
2. **PostgreSQL** (for storing optimization data)
3. **Dremio** with admin access
4. **Dremio Personal Access Token** (recommended) or username/password

## Step 1: Generate Dremio Personal Access Token

### Via Dremio UI:
1. Log in to Dremio as an admin user
2. Click on your user profile (top-right corner)
3. Select **Account Settings**
4. Navigate to **Personal Access Tokens**
5. Click **New Token**
6. Give it a name (e.g., "Optimizer Agent")
7. Set expiration (or choose "No Expiration" for testing)
8. Click **Create**
9. **Copy the token immediately** - you won't be able to see it again!

The token will look something like:
```
dremio_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Step 2: Install Dependencies

```bash
cd dremio_optimizer_agent

# Using Poetry (recommended)
poetry install

# OR using pip
pip install -e .
```

## Step 3: Configure Environment

### Create .env file:
```bash
cp .env.example .env
```

### Edit .env with your settings:

#### Option A: Using Personal Access Token (Recommended)
```env
# Dremio Configuration
DREMIO_URL=https://your-dremio-instance.com:9047
DREMIO_TOKEN=dremio_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Leave these empty if using token
DREMIO_USERNAME=
DREMIO_PASSWORD=

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dremio_optimizer

# LLM Configuration (for Phase 3 - AI Agent)
OPENAI_API_KEY=sk-your-key-here
```

#### Option B: Using Username/Password
```env
# Dremio Configuration
DREMIO_URL=https://your-dremio-instance.com:9047
DREMIO_USERNAME=admin
DREMIO_PASSWORD=your_password

# Leave token empty if using username/password
DREMIO_TOKEN=

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dremio_optimizer

# LLM Configuration (for Phase 3 - AI Agent)
OPENAI_API_KEY=sk-your-key-here
```

## Step 4: Setup PostgreSQL Database

### Create Database:
```bash
# Using psql
createdb dremio_optimizer

# OR using SQL
psql -U postgres -c "CREATE DATABASE dremio_optimizer;"
```

### Initialize Tables:
```bash
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

## Step 5: Test Connection

### Test Dremio Connection:
```python
# test_connection.py
from src.clients.dremio_client import DremioClient

# Will automatically use token from .env
client = DremioClient()

# Test connection
system_info = client.get_system_info()
print(f"Connected to Dremio version: {system_info.get('version')}")

# Fetch recent queries
queries = client.get_query_history(limit=5)
print(f"Found {len(queries)} recent queries")
```

Run it:
```bash
python test_connection.py
```

### Test Data Collection:
```bash
python scripts/test_collection.py
```

Expected output:
```
Testing Dremio connection and data collection...
============================================================

1. Initializing Dremio client...
2. Testing Dremio connection...
   ✓ Connected to Dremio version: 24.0.0

3. Initializing data collector...

4. Starting data collection...
------------------------------------------------------------
Collecting queries from last 24 hours...
Found 1234 queries
Inserted 1234 new queries
Collecting query profiles...
Collected 100 profiles
Collecting reflection metadata...
Collected 45 reflections
Collecting dataset metadata...
Collected 89 datasets

============================================================
Collection Summary:
============================================================
  Queries: 1234
  Profiles: 100
  Reflections: 45
  Datasets: 89

✓ Data collection completed successfully!
```

## Step 6: Usage Examples

### Example 1: Initialize Client with Token in Code

```python
from src.clients.dremio_client import DremioClient

# Option 1: Use token from environment (.env)
client = DremioClient()

# Option 2: Pass token directly
client = DremioClient(
    base_url="https://your-dremio-instance.com:9047",
    token="dremio_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)

# Get query history
queries = client.get_query_history(limit=100)
for query in queries[:5]:
    print(f"Query: {query.get('sql')[:50]}... Duration: {query.get('duration')}ms")
```

### Example 2: Collect Data Programmatically

```python
from src.data.collectors.dremio_collector import DremioCollector
from src.clients.dremio_client import DremioClient

# Initialize with token
client = DremioClient()
collector = DremioCollector(client)

# Collect all data from last 24 hours
stats = collector.collect_all(lookback_hours=24)
print(f"Collected {stats['queries']} queries and {stats['profiles']} profiles")

# Collect specific query
result = collector.collect_query(job_id="2bf9d3c8-1234-5678-90ab-cdef12345678")
print(f"Query collected: {result['query']}, Profile collected: {result['profile']}")
```

### Example 3: Query the Database

```python
from src.database.connection import get_db_session
from src.database.repositories.query_repository import QueryRepository
from src.database.repositories.profile_repository import ProfileRepository

# Get slow queries
with get_db_session() as session:
    query_repo = QueryRepository(session)

    # Get queries slower than 10 seconds
    slow_queries = query_repo.get_slow_queries(threshold_ms=10000, limit=10)

    for query in slow_queries:
        print(f"Job ID: {query.job_id}")
        print(f"Duration: {query.duration_ms}ms")
        print(f"SQL: {query.sql_text[:100]}...")
        print("-" * 60)
```

## Troubleshooting

### Issue 1: Authentication Failed
```
Error: 401 Unauthorized
```

**Solution:**
- Verify your token is correct and not expired
- Check that the token was copied completely (no spaces)
- Ensure the Dremio URL is correct (include port 9047)

### Issue 2: Connection Refused
```
Error: Connection refused to localhost:9047
```

**Solution:**
- Verify Dremio is running
- Check the DREMIO_URL in .env matches your Dremio instance
- For cloud Dremio, use the full URL (e.g., `https://xxx.dremio.cloud`)

### Issue 3: Database Connection Error
```
Error: could not connect to server
```

**Solution:**
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL in .env is correct
- Ensure the database exists: `psql -l | grep dremio_optimizer`

### Issue 4: No Queries Returned
```
Collection Summary:
  Queries: 0
```

**Solution:**
- Verify your Dremio instance has query history
- Check that your token has permissions to access job history
- Try a longer lookback period: `collector.collect_all(lookback_hours=168)`  # 7 days

## Next Steps

Once setup is complete:

1. **Verify Data Collection** - Ensure queries and profiles are being collected
2. **Check Database** - Query PostgreSQL to see collected data:
   ```sql
   SELECT COUNT(*) FROM queries;
   SELECT COUNT(*) FROM query_profiles;
   ```
3. **Ready for Phase 2** - Proceed to implement the Analysis Engine (detectors)

## Security Best Practices

1. **Use Personal Access Tokens** instead of username/password
2. **Set token expiration** - Rotate tokens regularly
3. **Secure .env file** - Never commit .env to version control
4. **Limit token scope** - Use minimal required permissions
5. **Use environment-specific tokens** - Different tokens for dev/staging/prod

## Support

If you encounter issues:
1. Check the logs for detailed error messages
2. Verify all prerequisites are installed
3. Test Dremio API access using curl:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://your-dremio-instance.com:9047/api/v3/catalog
   ```

---

**Setup Complete!** ✅

You're now ready to collect data from Dremio and proceed to Phase 2: Analysis Engine.
