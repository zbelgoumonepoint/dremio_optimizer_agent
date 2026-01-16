# Dremio Query Optimization Agent - Data Collection Guide

## A. Query-level Data (MANDATORY)

### 1️⃣ SQL Text

**Source**
- Dremio query history
- Job profiles / system tables
- REST API

**Used for**
- Pattern detection (SELECT *, joins, filters)
- Rewrite suggestions
- Change diffing
- Agent insights
- Top slow queries
- Repeated anti-patterns
- High-risk SQL patterns

### 2️⃣ Query Plans & Profiles (💎 Goldmine)

**Source**
- Dremio Query Profile
- EXPLAIN plans
- Job details API

**Contains**
- Operator tree
- Row counts
- Scan size
- Join methods
- Reflection usage

**Agent Insights**
- Partition pruning applied?
- Join fan-out
- Exchange / shuffle hotspots
- Reflection mismatches

> ⚠️ **This is your single most important signal.**

---

## B. Metadata & Catalog Data

### 3️⃣ Table & Dataset Metadata

**Source**
- Dremio Catalog API
- Iceberg / Hive metastore
- Information schema

**Includes**
- File format
- Partition columns
- Sort order
- Row counts
- Update frequency

**Agent Insights**
- Partition misuse
- Poor table design
- Missing reflections
- Schema evolution risks

### 4️⃣ Reflection Metadata (Dremio-specific)

**Source**
- Dremio reflection APIs

**Includes**
- Reflection type
- Refresh frequency
- Usage stats

**Agent Insights**
- Unused reflections (wasted cost)
- Missing reflections
- Reflections that don't match query shapes

---

## C. Execution & Resource Data

### 5️⃣ Execution Metrics

**Source**
- Dremio job profiles
- Cluster metrics (YARN / Kubernetes)

**Includes**
- CPU
- Memory
- Disk spill
- Runtime per phase

**Agent Insights**
- Memory pressure
- Skewed joins
- Concurrency issues
- Bad query patterns during peak hours

### 6️⃣ Storage-Layer Metadata

**Source**
- Object storage metrics (S3 / ADLS)
- Iceberg metadata tables

**Includes**
- File counts
- File sizes
- Partition layout
- Snapshot history

**Agent Insights**
- Small file problems
- Metadata bloat
- Missing compaction
- Inefficient partitioning

---

## D. User & Usage Context (Often Overlooked)

### 7️⃣ User & Workload Metadata

**Source**
- Dremio users / roles
- BI tool query tags
- Session metadata

**Agent Insights**
- Who runs expensive queries
- Which dashboards cause load
- Which teams need education vs automation

### 8️⃣ Historical Baselines

**Source**
- Stored query history
- Past performance snapshots

**Agent Insights**
- Regression detection
- Anomaly detection
- "This query used to be fast"

---

## Agent Capabilities Enabled

### A. Automated Issue Detection

| Issue | Data Needed |
|-------|-------------|
| No partition pruning | Plan + metadata |
| Reflection unused | Plan + reflection catalog |
| Join fan-out | Plan row counts |
| SELECT * | SQL text |
| Small file problem | Storage metadata |
| VDS overuse | Catalog lineage |
| Expensive dashboards | User + query frequency |

### B. Root Cause Analysis (Huge Value)

**Example Scenario:** "Why did yesterday's dashboards slow down?"

Agent can correlate:
- Query runtime ↑
- File count ↑
- New partition added
- Reflection refresh failed

> 💡 **This is where LLM reasoning shines.**

---

## E. Agent Evaluation Metrics

### A. Accuracy & Detection Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Precision** | % of detected issues that are actually valid issues | > 85% |
| **Recall** | % of actual issues detected by the agent | > 80% |
| **F1 Score** | Harmonic mean of precision & recall | > 0.82 |
| **False Positive Rate** | Issues incorrectly flagged as problems | < 15% |
| **False Negative Rate** | Real issues missed by the agent | < 20% |
| **Issue Detection Rate** | % of queries analyzed with issues identified | Baseline dependent |

### B. Performance Optimization Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Query Latency Improvement** | Average % reduction in query execution time after recommendations | Target: 20-40% |
| **CPU Utilization Reduction** | % decrease in CPU consumption for optimized queries | Target: 15-30% |
| **Memory Reduction** | % decrease in memory spill / peak memory usage | Target: 20-35% |
| **Disk I/O Improvement** | % reduction in unnecessary scans / data transferred | Target: 25-40% |
| **Reflection Utilization** | % improvement in reflection hit rate | Target: 10-25% increase |

### C. Cost Impact Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Total Cost Savings** | Cumulative $/month saved through optimizations | Target: 15-30% reduction |
| **Cost per Query** | Average $ reduction per optimized query | Track trend |
| **Storage Cost Reduction** | Savings from compaction, partition optimization | Target: 10-20% |
| **Compute Cost Reduction** | Savings from resource efficiency | Target: 20-35% |
| **ROI** | Cost savings vs. agent infrastructure cost | Target: > 5x |

### D. Coverage & Consistency Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Query Coverage** | % of total queries analyzed by agent | > 80% |
| **Issue Type Coverage** | # of different issue types detected vs. known types | > 70% |
| **Data Completeness** | % of required data successfully collected | > 95% |
| **Recommendation Consistency** | Same issue gets same recommendation type | > 90% |
| **Actionability Score** | % of recommendations that can be automatically applied | > 60% |

### E. Business & Adoption Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Issue Detection Velocity** | Avg. time to detect an issue after it occurs | Target: < 5 min |
| **Mean Time to Insight** | Time from issue detection to actionable recommendation | Target: < 2 min |
| **Recommendation Adoption Rate** | % of agent recommendations implemented by users | Target: > 60% |
| **Issue Resolution Time** | Avg. time from detection to resolution | Track trend |
| **Dashboards/Queries Improved** | # of slow dashboards/queries that were optimized | Track trend |

### F. Reliability & Stability Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Agent Uptime** | % of time agent is operational & collecting data | > 99% |
| **Data Collection Latency** | Time lag between event and data availability | < 30 seconds |
| **API Error Rate** | % of Dremio API calls that fail | < 2% |
| **Recommendation Stability** | Same query gets consistent recommendations over time | > 95% |
| **Root Cause Agreement** | Agent root cause matches human analysis | > 75% |

### G. Long-term Learning Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Issue Pattern Evolution** | New issue types discovered over time | Track # of new patterns |
| **Recommendation Effectiveness Trend** | % improvement in avg. query performance over 30/60/90 days | Upward trend |
| **Agent Accuracy Improvement** | Precision/Recall trend as agent learns | Should improve 5-10%/month |
| **Duplicate Issue Reduction** | % decrease in same issue reoccurring | Target: 30-50% reduction |
| **Prevention vs. Detection Ratio** | % of issues prevented vs. detected & fixed | Target: 40% prevention |

---

## Recommended Evaluation Workflow

1. **Baseline Phase (Week 1-2)**: Establish baseline metrics for all categories
2. **Detection Phase (Week 2-8)**: Validate precision/recall against manual audits
3. **Optimization Phase (Month 2-3)**: Measure actual performance improvements
4. **Business Phase (Month 3+)**: Track cost savings and ROI
5. **Continuous Monitoring**: Maintain dashboards for all metrics above
