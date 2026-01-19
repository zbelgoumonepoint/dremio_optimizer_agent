# Sonepar Dremio - System Architecture

## Overview

The Sonepar Dremio is an AI-powered system for detecting and fixing query performance issues in Dremio. It combines data collection, pattern detection, AI reasoning, and performance measurement into an integrated platform.

**Current Status**: Phase 1 Complete ✅ | Phase 2+ In Planning

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      External Integrations                       │
│  (BI Tools, Monitoring, Dashboards, External APIs)             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    REST API Layer (Phase 5)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ FastAPI • Auth • Rate Limiting • OpenAPI Docs           │  │
│  │ /health /analysis /recommendations /measurements        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  Application Services Layer                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ • Recommendation Service (Phase 3)                       │  │
│  │ • Analysis Service (Phase 2)                             │  │
│  │ • Measurement Service (Phase 4)                          │  │
│  │ • LangGraph AI Agent (Phase 3)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   Analysis Engine (Phase 2)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Detectors:                                               │  │
│  │  • Partition Pruning       • Reflection Usage            │  │
│  │  • JOIN Fan-out            • SELECT * Usage              │  │
│  │  • Small Files             • Performance Regression      │  │
│  │                                                           │  │
│  │ Baseline Calculator → Anomaly Detection                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                Data Collection Pipeline                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ DremioCollector (Orchestration)                          │  │
│  │  ├── Query Loader       ├── Metrics Loader              │  │
│  │  ├── Profile Loader     ├── Storage Loader              │  │
│  │  ├── Metadata Loader    └── Workload Loader             │  │
│  │  └── Reflection Loader                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              DremioClient (Dual-Mode)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Cloud Mode (REST API) | On-Prem Mode (REST API)        │  │
│  │ Auto-detection via config                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              Dremio Instance                                     │
│  (Cloud or On-Premises)                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### ✅ Phase 1: Foundation & Data Collection (COMPLETE)

**Status**: 100% Complete

**Components**:

1. **DremioClient** (`src/clients/dremio_client.py`)
   - Dual-mode support (Cloud + On-prem)
   - Token-based authentication
   - Query history access
   - System table queries
   - SSL certificate handling
   - ~300 lines, fully tested

2. **Data Loaders** (`src/data/loaders/`)
   - `QueryLoader` - SQL text and query metadata
   - `ProfileLoader` - Query execution profiles (EXPLAIN plans)
   - `MetadataLoader` - Table/dataset metadata
   - `ReflectionMetadataLoader` - Reflection info
   - `MetricsLoader` - Performance metrics
   - `StorageLoader` - Object storage metadata
   - `WorkloadLoader` - User/workload context
   - 7 specialized loaders, error handling included

3. **Database Layer** (`src/database/`)
   - 8 SQLAlchemy models (Query, Profile, Baseline, Recommendation, etc.)
   - 4 repository classes with CRUD operations
   - PostgreSQL schema with proper relationships
   - Connection management

4. **Collection Orchestration** (`src/data/collectors/`)
   - `DremioCollector` - Coordinates all loaders
   - Duplicate prevention
   - Error handling and logging
   - Collection statistics

5. **Configuration** (`src/config/settings.py`)
   - Pydantic Settings
   - Environment variable support
   - Mode auto-detection
   - Comprehensive validation

**Key Achievements**:
- ✅ Live connection to Dremio Cloud
- ✅ Query history collection working
- ✅ Full database schema defined
- ✅ 7 data loaders implemented
- ✅ Comprehensive documentation

---

### ⏳ Phase 2: Analysis Engine (NEXT)

**Duration**: 1-2 weeks
**Dependencies**: Phase 1 ✅

**Components to Build**:

1. **Detection Framework** (`src/analysis/detectors/`)
   - Base detector abstract class
   - Detection result dataclass
   - Issue severity/type enums
   - Reusable detector patterns

2. **Six Core Detectors**:
   - **PartitionPruningDetector** - Identify missing partition filters
   - **ReflectionDetector** - Detect missing/unused reflections
   - **JoinFanoutDetector** - Identify join inefficiencies
   - **SelectStarDetector** - Find SELECT * anti-patterns
   - **SmallFileDetector** - Detect small file problems
   - **RegressionDetector** - Identify query slowdowns

3. **Baseline Calculator** (`src/analysis/metrics/`)
   - Historical performance baselines
   - Anomaly detection
   - Trend analysis
   - Regression detection

4. **Analysis Service** (`src/analysis/services/`)
   - Orchestrates detectors
   - Aggregates results
   - Persistence to database
   - Batch analysis support

**Deliverables**:
- 6+ working detectors with tests
- Baseline calculation system
- Analysis orchestration service
- >80% test coverage

---

### 🤖 Phase 3: AI Agent Implementation

**Duration**: 1-2 weeks
**Dependencies**: Phase 2 ✅

**Components to Build**:

1. **LangGraph Agent** (`src/agents/optimizer_agent.py`)
   - State management for multi-step reasoning
   - Error recovery and retries
   - Memory of past analyses
   - Tool orchestration

2. **Agent Tools** (`src/agents/tools/`)
   - `QueryPatternAnalyzer` - Analyze SQL patterns
   - `ReflectionChecker` - Check reflection opportunities
   - `ImpactEstimator` - Estimate optimization impact
   - `SQLRewriter` - Generate SQL rewrites

3. **System Prompts** (`src/agents/prompts/`)
   - Domain-specific expertise in Dremio
   - Few-shot examples
   - Reasoning templates
   - Trade-off analysis

4. **Recommendation Service** (`src/services/recommendation_service.py`)
   - Calls LLM with detected issues
   - Generates structured recommendations
   - Estimates impact
   - Persists recommendations
   - Tracks reasoning

**AI/LLM Strategy**:
- **Primary Model**: GPT-4o (reasoning, SQL generation)
- **Backup**: Claude 3.5 Sonnet (Anthropic API)
- **Prompt Strategy**: Chain of Thought with domain knowledge
- **Context Window**: Optimized for token efficiency

**Deliverables**:
- LangGraph agent with state management
- 4 specialized tools
- System prompts with examples
- Structured recommendations with SQL
- Impact estimation

---

### 📊 Phase 4: Performance Measurement

**Duration**: 1 week
**Dependencies**: Phase 3 ✅

**Components to Build**:

1. **Measurement Service** (`src/services/measurement_service.py`)
   - Before/after query performance comparison
   - Impact calculation
   - Cost savings tracking
   - ROI calculation

2. **Metrics Tracking**:
   - Query latency (before vs. after)
   - CPU/Memory reduction
   - Reflection hit rate improvement
   - Cost per query
   - Total savings

3. **Result Persistence**:
   - Store measurement results
   - Track recommendation impact
   - Build historical trends
   - Enable feedback loop

**Deliverables**:
- Measurement service
- Impact calculation engine
- Cost tracking
- Historical analysis

---

### 🌐 Phase 5: REST API

**Duration**: 1 week
**Dependencies**: Phases 1-4 ✅

**Endpoints**:

```
GET    /health                    # Health check
GET    /api/v1/analysis/{query_id}         # Get analysis for query
POST   /api/v1/analysis           # Trigger new analysis
GET    /api/v1/recommendations    # Get recommendations
POST   /api/v1/recommendations/apply # Apply recommendation
GET    /api/v1/measurements/{rec_id} # Get measurement results
GET    /api/v1/metrics/summary    # Overall metrics
POST   /api/v1/collection/trigger # Trigger data collection
```

**Features**:
- FastAPI framework
- OpenAPI/Swagger docs
- Authentication (API keys or OAuth)
- Rate limiting
- Caching
- Error handling
- Batch operations
- Async endpoints

**Deliverables**:
- 20+ REST endpoints
- OpenAPI documentation
- Auth middleware
- Python SDK client

---

### 👁️ Phase 6: Observability

**Duration**: 1 week
**Dependencies**: Phases 1-5 ✅

**Components**:

1. **Logging**
   - Structured JSON logging
   - Log levels (DEBUG, INFO, WARNING, ERROR)
   - Request/response logging

2. **Tracing** (OpenTelemetry)
   - Distributed tracing
   - Tempo backend integration
   - Span creation for key operations

3. **Metrics** (Prometheus)
   - Agent performance metrics
   - Error rates
   - Collection duration
   - Analysis latency

4. **Monitoring Dashboard**
   - Grafana dashboard
   - Real-time metrics
   - Error tracking
   - Performance trends

**Deliverables**:
- Structured logging
- OpenTelemetry integration
- Prometheus metrics
- Grafana dashboards

---

### ✅ Phase 7: Testing & Documentation

**Duration**: 1-2 weeks
**Dependencies**: Phases 1-6 ✅

**Components**:

1. **Testing**
   - Unit tests (>80% coverage)
   - Integration tests
   - E2E tests
   - Performance benchmarks
   - Load testing

2. **Documentation**
   - Architecture guide
   - API documentation
   - Deployment guide
   - User guide
   - Contributing guide
   - Troubleshooting guide

3. **CI/CD**
   - GitHub Actions
   - Automated testing
   - Code quality checks
   - Build artifacts

**Deliverables**:
- >80% test coverage
- Comprehensive documentation
- CI/CD pipeline
- Deployment ready

---

## Data Flow

### Collection Data Flow

```
Dremio Instance
     ↓
DremioClient (auto-detects mode)
     ↓
[7 Parallel Loaders] (with error handling)
  • QueryLoader → SQL text
  • ProfileLoader → Execution profiles
  • MetadataLoader → Table metadata
  • ReflectionMetadataLoader → Reflection info
  • MetricsLoader → Performance metrics
  • StorageLoader → Storage metadata
  • WorkloadLoader → User context
     ↓
DremioCollector (orchestration)
     ↓
Database Layer (repositories)
     ↓
PostgreSQL (8 tables with relationships)
```

### Analysis Data Flow

```
Stored Queries & Profiles
     ↓
Analysis Service
     ↓
[6 Parallel Detectors]
  • PartitionPruningDetector
  • ReflectionDetector
  • JoinFanoutDetector
  • SelectStarDetector
  • SmallFileDetector
  • RegressionDetector
     ↓
Detected Issues
     ↓
Issue Aggregation & Prioritization
     ↓
Database Persistence
```

### Recommendation Data Flow

```
Detected Issues
     ↓
LangGraph AI Agent
     ↓
[4 Agent Tools]
  • QueryPatternAnalyzer
  • ReflectionChecker
  • ImpactEstimator
  • SQLRewriter
     ↓
LLM Reasoning (GPT-4o)
     ↓
Structured Recommendations
  {
    "issue_id": "...",
    "recommendation": "...",
    "sql_rewrite": "...",
    "estimated_impact_pct": 25,
    "reasoning": "..."
  }
     ↓
Recommendations Table
```

### Measurement Data Flow

```
Applied Recommendation
     ↓
Run Optimized Query
     ↓
Collect New Metrics
     ↓
Measurement Service
     ↓
Compare Before/After
     ↓
Calculate Impact
  {
    "latency_reduction_pct": 28,
    "cost_savings": 150,
    "cpu_reduction_pct": 32
  }
     ↓
Measurement Persistence
```

---

## Database Schema

### Core Tables

```
queries
├── id (UUID, PK)
├── sql_text (TEXT)
├── user (VARCHAR)
├── execution_duration_ms (INT)
├── rows_scanned (INT)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

query_profiles
├── id (UUID, PK)
├── query_id (UUID, FK)
├── plan_json (JSONB)
├── operator_tree (JSONB)
├── row_counts (JSONB)
└── collected_at (TIMESTAMP)

issues
├── id (UUID, PK)
├── query_id (UUID, FK)
├── issue_type (VARCHAR) - Enum
├── severity (VARCHAR) - low/medium/high/critical
├── title (VARCHAR)
├── description (TEXT)
├── evidence (JSONB)
└── detected_at (TIMESTAMP)

recommendations
├── id (UUID, PK)
├── issue_id (UUID, FK)
├── title (VARCHAR)
├── description (TEXT)
├── sql_rewrite (TEXT)
├── estimated_impact_pct (FLOAT)
├── reasoning (TEXT)
├── created_at (TIMESTAMP)
└── applied_at (TIMESTAMP, NULL)

measurements
├── id (UUID, PK)
├── recommendation_id (UUID, FK)
├── before_latency_ms (INT)
├── after_latency_ms (INT)
├── actual_improvement_pct (FLOAT)
├── cost_savings (DECIMAL)
└── measured_at (TIMESTAMP)

baselines
├── id (UUID, PK)
├── query_id (UUID, FK)
├── metric_name (VARCHAR)
├── value (FLOAT)
├── period (VARCHAR) - daily/weekly/monthly
└── calculated_at (TIMESTAMP)
```

---

## Technology Stack

### Backend
- **Python 3.12** - Primary language
- **FastAPI** - REST API framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Pydantic** - Data validation

### AI/ML
- **LangGraph** - Agent framework
- **OpenAI API** - GPT-4o for reasoning
- **Anthropic API** - Claude 3.5 as backup
- **LangChain** - LLM abstractions

### Observability
- **OpenTelemetry** - Tracing
- **Prometheus** - Metrics
- **Loki** - Logging
- **Grafana** - Dashboards
- **Tempo** - Trace backend

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local development
- **Kubernetes** - Production deployment
- **GitHub Actions** - CI/CD

### Development
- **UV** - Python package manager
- **pytest** - Testing
- **Black** - Code formatting
- **Pylint** - Linting
- **mypy** - Type checking

---

## Configuration Management

### Environment Variables

```bash
# Dremio
DREMIO_URL=https://api.dremio.cloud
DREMIO_TOKEN=***
DREMIO_PROJECT_ID=***
DREMIO_VERIFY_SSL=true

# Database
DATABASE_URL=postgresql://user:pass@localhost/dremio_optimizer

# LLM
OPENAI_API_KEY=***
ANTHROPIC_API_KEY=***
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.1

# Observability
TEMPO_ENDPOINT=http://localhost:4317
LOKI_ENDPOINT=http://localhost:3100

# Collection
COLLECTION_INTERVAL_MINUTES=30
COLLECTION_LOOKBACK_HOURS=24
```

---

## Deployment Architecture

### Local Development
```
Docker Compose
├── Dremio Simulator (mock)
├── PostgreSQL
├── Loki (logging)
├── Tempo (tracing)
├── Prometheus (metrics)
└── Grafana (dashboards)

+ Python app (dev mode)
```

### Production (Kubernetes)
```
Kubernetes Cluster
├── Deployment: Optimizer Agent
├── Service: REST API
├── ConfigMap: Configuration
├── Secret: Credentials
├── PersistentVolume: Database
└── Ingress: External access
```

---

## Key Design Decisions

1. **Modular Architecture** - Each phase can be developed independently
2. **Dual-Mode Dremio Client** - Support both Cloud and On-prem
3. **LangGraph Agent** - Multi-step AI reasoning over tools
4. **Evidence-Based Recommendations** - AI recommendations backed by query metrics
5. **Database Persistence** - Track all analyses and recommendations
6. **PostgreSQL** - JSONB support for flexible metadata storage
7. **OpenTelemetry** - Industry-standard observability
8. **REST API First** - All functionality exposed via API

---

## Integration Points

### Upstream (Data Sources)
- Dremio Cloud API
- Dremio On-Prem REST API
- System tables
- Query profiles
- Catalog metadata

### Downstream (Consumers)
- BI Tools (Tableau, Looker)
- Monitoring Systems (Datadog, NewRelic)
- Slack/Email Notifications
- Custom Dashboards
- Automation Workflows

---

## Future Enhancements

1. **Multi-tenant Support** - Separate orgs/teams
2. **SQL Generation Verification** - Test generated rewrites
3. **Auto-apply Recommendations** - Automated optimization
4. **Cost Forecasting** - Predict future costs
5. **Query Rewrite Versioning** - Track SQL changes
6. **Team Collaboration** - Comments/feedback on recommendations
7. **Advanced Analytics** - Anomaly detection, forecasting
8. **Plugin System** - Custom detectors and tools
