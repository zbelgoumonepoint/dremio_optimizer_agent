# Documentation Index

This directory contains all documentation related to the conception, development, and setup of the Dremio Optimizer Agent project.

## Project Overview

- **[Main README](../README.md)** - Project overview and quick start guide

## Setup & Configuration

- **[Setup Guide](SETUP_GUIDE.md)** - Complete installation and configuration instructions
- **[Dremio Cloud Setup](DREMIO_CLOUD_SETUP.md)** - Dremio Cloud-specific configuration guide

## Technical Documentation

- **[Dremio Cloud API Integration](DREMIO_CLOUD_API_COMPLETE.md)** - Complete guide to Cloud API implementation
  - Dual-mode client architecture (Cloud + On-prem)
  - SQL API for query history
  - System table schemas
  - API endpoint mapping

- **[SSL Configuration](SSL_FIX_COMPLETE.md)** - SSL certificate handling and troubleshooting
  - macOS SSL issues
  - Configurable SSL verification
  - Security considerations

## Project Progress

- **[Phase 1 Complete](PHASE1_COMPLETE.md)** - Original Phase 1 completion summary
- **[Phase 1 Updated](PHASE1_UPDATED.md)** - Final Phase 1 status with Cloud API integration
  - 60 files, 4,300+ lines of code
  - Dual-mode Dremio client
  - 8 database tables
  - 7 data loaders
  - 4 repositories

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DREMIO REST API                         │
│                  (Cloud or On-Prem)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ DremioClient (auto-detects mode)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATA COLLECTION LAYER                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐     │
│  │QueryLoader  │  │ProfileLoader │  │MetadataLoader │ ... │
│  └─────────────┘  └──────────────┘  └───────────────┘     │
│                 DremioCollector                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Repositories (CRUD)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                      │
│  queries | query_profiles | baselines | recommendations    │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **DremioClient** - Dual-mode API client
   - Detects Cloud vs On-prem automatically
   - Routes to appropriate endpoints
   - Handles authentication (Bearer token or _dremio prefix)

2. **Data Loaders** (7 specialized loaders)
   - QueryLoader - Query history
   - ProfileLoader - Execution profiles
   - MetadataLoader - Dataset metadata
   - ReflectionMetadataLoader - Reflection info
   - MetricsLoader - Performance metrics
   - StorageLoader - Storage metadata
   - WorkloadLoader - User/workload context

3. **Database Layer**
   - 8 SQLAlchemy models
   - 4 specialized repositories
   - Connection pooling and session management

4. **Configuration System**
   - Pydantic Settings with environment variables
   - Support for Cloud-specific settings

## Development Phases

### Phase 1: Foundation & Data Collection ✅ COMPLETE
- Project structure (60 files)
- Dremio client (Cloud + On-prem)
- Database schema (8 tables)
- Data loaders (7 loaders)
- Repositories (4 repos)
- Documentation (10+ files)

### Phase 2: Analysis Engine (Next)
- 6+ detector implementations
- Baseline system
- Performance analysis service

### Phase 3: AI Agent
- LangGraph-based optimizer
- SQL rewriting tools
- Impact estimation

### Phase 4: Performance Measurement
- Before/after tracking
- Measurement workflows
- Impact validation

### Phase 5: REST API
- FastAPI endpoints
- API documentation
- Client SDKs

### Phase 6: Observability
- OpenTelemetry integration
- Loki logging
- Monitoring dashboards

### Phase 7: Testing & Documentation
- Comprehensive test suite
- User guides
- Deployment documentation

## Quick Links

- **GitHub Repository**: https://github.com/zbelgoumonepoint/dremio_optimizer_agent
- **Dremio Cloud**: https://api.dremio.cloud
- **Dremio Documentation**: https://docs.dremio.com/cloud/

## Support

For issues or questions:
1. Check the relevant documentation file above
2. Review the main README
3. Check GitHub issues

---

**Last Updated**: Phase 1 Complete - January 2026
