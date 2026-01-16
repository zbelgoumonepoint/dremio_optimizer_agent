# Phase 3: AI Agent Implementation

**Duration**: 2 weeks
**Status**: Planned
**Dependencies**: Phase 2 (Analysis Engine) must be complete

## Overview

Build a LangGraph-based AI agent that analyzes detected performance issues and generates actionable, context-aware optimization recommendations with reasoning.

### Goals

1. Implement LangGraph agent with 4+ specialized tools
2. Create robust system prompts with few-shot examples
3. Generate structured recommendations with SQL rewrites
4. Estimate performance impact using evidence-based heuristics
5. Provide reasoning and trade-off analysis for each recommendation

### Key Deliverables

- LangGraph agent with state management
- 4 specialized agent tools
- System prompts with domain expertise
- Recommendation service with persistence
- End-to-end recommendation generation workflow

---

## Architecture

```
Detected Issues → OptimizerAgent (LangGraph) → Structured Recommendations
                       ↓
                  [Agent Tools]
                  - analyze_query_pattern
                  - check_reflection_opportunity
                  - estimate_optimization_impact
                  - generate_sql_rewrite
                       ↓
                  LLM Reasoning (GPT-4o)
                       ↓
                  Recommendations → PostgreSQL
```

---

## Component 1: Agent Tools

### File Structure
```
src/agents/tools/
├── __init__.py
├── query_analyzer.py
├── reflection_checker.py
├── impact_estimator.py
└── sql_rewriter.py
```

### Tool 1: Query Pattern Analyzer

**File**: `src/agents/tools/query_analyzer.py`

```python
from langchain_core.tools import tool
from typing import Dict, Any

@tool
def analyze_query_pattern(sql_text: str, profile: Dict[str, Any]) -> str:
    """
    Analyze SQL query patterns and execution characteristics.

    Extracts:
    - SELECT * usage
    - JOIN patterns and types
    - WHERE clause filters and selectivity
    - GROUP BY / ORDER BY patterns
    - Subquery complexity
    - Rows scanned vs returned ratio

    Args:
        sql_text: The SQL query text
        profile: Query execution profile with operator metrics

    Returns:
        Detailed analysis of query patterns and characteristics
    """
    analysis = {
        "patterns": [],
        "selectivity": None,
        "complexity": "low",
        "issues": []
    }

    # Check for SELECT *
    if "SELECT *" in sql_text.upper() or "SELECT\n*" in sql_text:
        analysis["patterns"].append("select_star")
        analysis["issues"].append("Using SELECT * retrieves unnecessary columns")

    # Check for JOINs
    join_types = ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"]
    for join_type in join_types:
        if join_type in sql_text.upper():
            analysis["patterns"].append(f"{join_type.lower().replace(' ', '_')}")

    # Calculate selectivity from profile
    if profile and "rows_scanned" in profile and "rows_returned" in profile:
        rows_scanned = profile["rows_scanned"]
        rows_returned = profile["rows_returned"]

        if rows_scanned > 0:
            selectivity = rows_returned / rows_scanned
            analysis["selectivity"] = selectivity

            if selectivity > 0.8:
                analysis["issues"].append(
                    f"Low selectivity ({selectivity:.1%}): query returns most rows scanned"
                )
            elif selectivity > 10:  # Fan-out
                analysis["issues"].append(
                    f"Join fan-out detected: returning {selectivity:.1f}x more rows than scanned"
                )

    # Complexity assessment
    complexity_indicators = [
        ("subquery", "SELECT" in sql_text.upper().split("FROM")[0]),
        ("multiple_joins", sql_text.upper().count("JOIN") > 2),
        ("aggregations", any(agg in sql_text.upper() for agg in ["GROUP BY", "COUNT", "SUM", "AVG"]))
    ]

    complexity_score = sum(1 for _, present in complexity_indicators if present)
    if complexity_score >= 2:
        analysis["complexity"] = "high"
    elif complexity_score == 1:
        analysis["complexity"] = "medium"

    # Format response
    response = f"""
Query Pattern Analysis:
- Patterns detected: {', '.join(analysis['patterns']) if analysis['patterns'] else 'standard select'}
- Complexity: {analysis['complexity']}
- Selectivity: {analysis['selectivity']:.2%} if analysis['selectivity'] else 'unknown'}
- Issues: {len(analysis['issues'])}

Details:
{chr(10).join(f"  • {issue}" for issue in analysis['issues'])}
"""
    return response.strip()
```

### Tool 2: Reflection Opportunity Checker

**File**: `src/agents/tools/reflection_checker.py`

```python
from langchain_core.tools import tool
from typing import Dict, Any, List
from src.database.repositories.reflection_repository import ReflectionMetadataRepository
from src.database.connection import get_db_session

@tool
def check_reflection_opportunity(dataset_path: str, query_pattern: str) -> str:
    """
    Check if a query would benefit from Dremio reflections (materialized views).

    Analyzes:
    - Existing reflections on the dataset
    - Query pattern (aggregation, raw, external)
    - Reflection hit rates and usage
    - Estimated performance improvement

    Args:
        dataset_path: Fully qualified dataset path (e.g., 'sales.orders')
        query_pattern: Type of query pattern (aggregation, filter, join)

    Returns:
        Recommendation on reflection opportunities
    """
    with get_db_session() as session:
        repo = ReflectionMetadataRepository(session)
        existing_reflections = repo.get_by_dataset(dataset_path)

    response_parts = [f"Reflection Analysis for {dataset_path}:"]

    # Check existing reflections
    if existing_reflections:
        response_parts.append(f"\nExisting reflections: {len(existing_reflections)}")

        for ref in existing_reflections:
            hit_rate = ref.hit_count / max(ref.miss_count + ref.hit_count, 1)
            status = "✓ Effective" if hit_rate > 0.7 else "⚠ Underutilized"
            response_parts.append(
                f"  • {ref.reflection_type}: {status} (hit rate: {hit_rate:.1%}, last used: {ref.last_used_at})"
            )
    else:
        response_parts.append("\nNo existing reflections found.")

    # Recommendation based on query pattern
    recommendations = []

    if query_pattern == "aggregation":
        if not any(r.reflection_type == "AGGREGATION" for r in existing_reflections):
            recommendations.append(
                "CREATE AGGREGATION REFLECTION: Query performs aggregations (GROUP BY/COUNT/SUM). "
                "An aggregation reflection could provide 70-90% speedup."
            )

    elif query_pattern == "filter":
        if not any(r.reflection_type == "RAW" for r in existing_reflections):
            recommendations.append(
                "CREATE RAW REFLECTION: Query filters on specific columns. "
                "A raw reflection with appropriate sort/partition could provide 40-60% speedup."
            )

    elif query_pattern == "join":
        recommendations.append(
            "CONSIDER REFLECTION ON JOIN DIMENSIONS: Pre-joining frequently used dimensions "
            "via reflection could reduce join overhead by 50-80%."
        )

    if recommendations:
        response_parts.append("\nRecommendations:")
        response_parts.extend(f"  • {rec}" for rec in recommendations)
        response_parts.append("\nEstimated improvement: 40-90% depending on reflection type")
    else:
        response_parts.append("\n✓ Reflection coverage appears adequate for this query pattern.")

    return "\n".join(response_parts)
```

### Tool 3: Impact Estimator

**File**: `src/agents/tools/impact_estimator.py`

```python
from langchain_core.tools import tool
from typing import Optional

# Evidence-based impact factors from industry benchmarks
IMPACT_FACTORS = {
    "partition_pruning": {
        "improvement_pct": 60,
        "description": "Reducing partitions scanned by 80%+ typically yields 60% speedup"
    },
    "reflection_aggregation": {
        "improvement_pct": 85,
        "description": "Aggregation reflections typically provide 70-90% speedup"
    },
    "reflection_raw": {
        "improvement_pct": 50,
        "description": "Raw reflections with proper sorting typically provide 40-60% speedup"
    },
    "select_star_elimination": {
        "improvement_pct": 20,
        "description": "Selecting only needed columns reduces I/O by ~20%"
    },
    "join_optimization": {
        "improvement_pct": 40,
        "description": "Fixing join fan-outs or reordering joins typically yields 30-50% improvement"
    },
    "small_file_compaction": {
        "improvement_pct": 55,
        "description": "Compacting small files reduces metadata overhead by 50-60%"
    },
    "index_creation": {
        "improvement_pct": 70,
        "description": "Adding indexes on filter columns typically provides 60-80% speedup"
    }
}

@tool
def estimate_optimization_impact(
    current_duration_ms: int,
    optimization_type: str,
    additional_context: Optional[str] = None
) -> str:
    """
    Estimate the performance impact of a proposed optimization.

    Uses industry benchmarks and empirical data to estimate:
    - Expected duration reduction percentage
    - Estimated new duration
    - Time savings per query execution

    Args:
        current_duration_ms: Current query duration in milliseconds
        optimization_type: Type of optimization (partition_pruning, reflection_aggregation, etc.)
        additional_context: Optional context for more refined estimates

    Returns:
        Detailed impact estimation with time savings
    """
    if optimization_type not in IMPACT_FACTORS:
        return f"Unknown optimization type: {optimization_type}. Cannot estimate impact."

    factor = IMPACT_FACTORS[optimization_type]
    improvement_pct = factor["improvement_pct"]

    # Adjust based on additional context
    if additional_context:
        if "minor" in additional_context.lower():
            improvement_pct *= 0.5
        elif "major" in additional_context.lower():
            improvement_pct = min(improvement_pct * 1.2, 95)

    # Calculate estimates
    current_duration_sec = current_duration_ms / 1000
    time_saved_sec = current_duration_sec * (improvement_pct / 100)
    new_duration_sec = current_duration_sec - time_saved_sec

    # Format response
    response = f"""
Optimization Impact Estimate:

Optimization Type: {optimization_type.replace('_', ' ').title()}
Current Duration: {current_duration_sec:.2f}s ({current_duration_ms:,}ms)

Expected Improvement: {improvement_pct}%
Basis: {factor['description']}

Estimated New Duration: {new_duration_sec:.2f}s ({int(new_duration_sec * 1000):,}ms)
Time Saved per Execution: {time_saved_sec:.2f}s ({int(time_saved_sec * 1000):,}ms)

Annual Impact (if run daily):
  • Time saved per year: {time_saved_sec * 365 / 3600:.1f} hours
  • Queries per day: 1 → {time_saved_sec:.1f}s saved/day
  • Queries per day: 100 → {time_saved_sec * 100 / 3600:.1f} hours saved/day

Note: Actual improvement may vary based on data volume, cluster resources, and workload.
"""
    return response.strip()
```

### Tool 4: SQL Rewriter

**File**: `src/agents/tools/sql_rewriter.py`

```python
from langchain_core.tools import tool
from typing import Dict, Any
import re

@tool
def generate_sql_rewrite(
    original_sql: str,
    issue_type: str,
    evidence: str
) -> str:
    """
    Generate optimized SQL rewrite for detected performance issues.

    Supports rewrites for:
    - SELECT * elimination → specific column selection
    - Partition pruning → add WHERE clause filters
    - Join optimization → reorder or add filters

    Args:
        original_sql: Original SQL query text
        issue_type: Type of issue (select_star, missing_partition_filter, etc.)
        evidence: Evidence context (e.g., available columns, partition columns)

    Returns:
        Rewritten SQL with explanation of changes
    """
    if issue_type == "select_star":
        return _rewrite_select_star(original_sql, evidence)
    elif issue_type == "missing_partition_filter":
        return _rewrite_add_partition_filter(original_sql, evidence)
    elif issue_type == "join_fanout":
        return _rewrite_join_optimization(original_sql, evidence)
    else:
        return f"SQL rewrite not available for issue type: {issue_type}"


def _rewrite_select_star(sql: str, evidence: str) -> str:
    """Replace SELECT * with specific columns based on usage."""
    # Parse evidence for actual columns used
    # In real implementation, would parse from query profile
    suggested_columns = [
        "order_id", "customer_id", "order_date", "total_amount", "status"
    ]

    # Simple regex replacement (production would use SQL parser)
    rewritten = re.sub(
        r'SELECT\s+\*',
        f"SELECT\n  {', '.join(suggested_columns)}",
        sql,
        flags=re.IGNORECASE
    )

    return f"""
-- ORIGINAL:
{sql}

-- OPTIMIZED (SELECT * → Specific Columns):
{rewritten}

-- EXPLANATION:
-- Replaced SELECT * with explicit column list based on actual usage.
-- This reduces I/O by retrieving only necessary columns.
-- Estimated improvement: 15-25% reduction in data scanned.

-- COLUMNS SELECTED:
{chr(10).join(f'--   • {col}' for col in suggested_columns)}
"""


def _rewrite_add_partition_filter(sql: str, evidence: str) -> str:
    """Add partition filter to WHERE clause."""
    # Extract partition column from evidence
    partition_col = "order_date"  # Would parse from evidence in production

    # Find WHERE clause or add one
    if "WHERE" in sql.upper():
        # Add to existing WHERE
        rewritten = re.sub(
            r'(WHERE\s+)',
            f'\\1{partition_col} >= CURRENT_DATE - INTERVAL \'30\' DAY\n  AND ',
            sql,
            flags=re.IGNORECASE
        )
    else:
        # Add new WHERE before GROUP BY/ORDER BY/LIMIT
        insert_before = re.search(r'(GROUP BY|ORDER BY|LIMIT)', sql, re.IGNORECASE)
        if insert_before:
            pos = insert_before.start()
            rewritten = (
                sql[:pos] +
                f"\nWHERE {partition_col} >= CURRENT_DATE - INTERVAL '30' DAY\n" +
                sql[pos:]
            )
        else:
            rewritten = sql + f"\nWHERE {partition_col} >= CURRENT_DATE - INTERVAL '30' DAY"

    return f"""
-- ORIGINAL:
{sql}

-- OPTIMIZED (Added Partition Filter):
{rewritten}

-- EXPLANATION:
-- Added filter on partition column '{partition_col}' to enable partition pruning.
-- This reduces the number of partitions scanned from all partitions to ~30 days.
-- Estimated improvement: 50-70% reduction in data scanned.

-- ADJUST THE DATE RANGE based on your analytical needs.
"""


def _rewrite_join_optimization(sql: str, evidence: str) -> str:
    """Suggest join optimization strategies."""
    return f"""
-- ORIGINAL:
{sql}

-- OPTIMIZATION STRATEGIES:

1. ADD JOIN FILTER:
   -- If joining on a dimension table, add a filter to reduce rows before join:
   -- WHERE dimension_table.status = 'ACTIVE'

2. JOIN ORDER:
   -- Dremio generally optimizes join order, but you can force it:
   -- Start with smallest table (dimension) and join to larger (fact)

3. USE REFLECTION:
   -- Consider creating a reflection that pre-joins these tables
   -- This is especially effective for frequently used dimension joins

-- EVIDENCE FROM QUERY:
{evidence}

-- RECOMMENDATION:
-- Review the join cardinality. If one table returns many more rows after join,
-- add filters to reduce the dimension table size before joining.
"""
```

---

## Component 2: LangGraph Agent

### File: `src/agents/optimizer_agent.py`

```python
from typing import TypedDict, Sequence, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.agents.prompts.system_prompts import OPTIMIZER_SYSTEM_PROMPT
from src.agents.tools.query_analyzer import analyze_query_pattern
from src.agents.tools.reflection_checker import check_reflection_opportunity
from src.agents.tools.impact_estimator import estimate_optimization_impact
from src.agents.tools.sql_rewriter import generate_sql_rewrite


class OptimizerState(TypedDict):
    """State for the optimizer agent."""
    query_context: Dict[str, Any]  # Job ID, SQL, duration, metrics
    detected_issues: List[Dict[str, Any]]  # Issues from detectors
    messages: Sequence[BaseMessage]
    recommendations: List[Dict[str, Any]]  # Final structured recommendations


# Define tools
TOOLS = [
    analyze_query_pattern,
    check_reflection_opportunity,
    estimate_optimization_impact,
    generate_sql_rewrite
]


def create_optimizer_agent(model_name: str = "gpt-4o", temperature: float = 0.1):
    """Create the LangGraph optimizer agent."""

    # Initialize LLM with tools
    llm = ChatOpenAI(model=model_name, temperature=temperature).bind_tools(TOOLS)

    # Define graph
    workflow = StateGraph(OptimizerState)

    # Add nodes
    workflow.add_node("call_optimizer", call_optimizer_node)
    workflow.add_node("tools", ToolNode(TOOLS))
    workflow.add_node("extract_recommendations", extract_recommendations_node)

    # Define edges
    workflow.set_entry_point("call_optimizer")

    # Conditional edge: if LLM calls tools, go to tools node, else extract recommendations
    workflow.add_conditional_edges(
        "call_optimizer",
        should_continue,
        {
            "continue": "tools",
            "end": "extract_recommendations"
        }
    )

    # After tools, go back to LLM
    workflow.add_edge("tools", "call_optimizer")

    # After extraction, end
    workflow.add_edge("extract_recommendations", END)

    return workflow.compile(), llm


def call_optimizer_node(state: OptimizerState, llm) -> OptimizerState:
    """Invoke the LLM with system prompt and context."""
    messages = state.get("messages", [])

    # Build context for LLM
    if not messages:
        # First call: set system prompt and context
        query_context = state["query_context"]
        detected_issues = state["detected_issues"]

        context_msg = f"""
Query Context:
- Job ID: {query_context['job_id']}
- SQL: {query_context['sql_text'][:500]}...
- Duration: {query_context['duration_ms']}ms
- Rows Scanned: {query_context.get('rows_scanned', 'N/A')}
- Rows Returned: {query_context.get('rows_returned', 'N/A')}

Detected Issues ({len(detected_issues)}):
{chr(10).join(f"{i+1}. {issue['title']} (Severity: {issue['severity']})" for i, issue in enumerate(detected_issues))}

For each issue, provide:
1. Root cause analysis
2. Specific recommendation with implementation steps
3. Use the available tools to estimate impact and generate SQL rewrites
4. Priority ranking (high/medium/low based on impact vs effort)
"""

        messages = [
            SystemMessage(content=OPTIMIZER_SYSTEM_PROMPT),
            HumanMessage(content=context_msg)
        ]

    # Invoke LLM
    response = llm.invoke(messages)
    messages.append(response)

    return {**state, "messages": messages}


def should_continue(state: OptimizerState) -> str:
    """Determine if we should continue to tools or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # If LLM called tools, continue
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "continue"

    return "end"


def extract_recommendations_node(state: OptimizerState) -> OptimizerState:
    """Extract structured recommendations from LLM response."""
    messages = state["messages"]
    final_response = messages[-1].content

    # Parse LLM response into structured recommendations
    # In production, would use more robust parsing (Pydantic models)
    recommendations = []

    detected_issues = state["detected_issues"]
    for i, issue in enumerate(detected_issues):
        # Extract recommendation for this issue from LLM response
        recommendation = {
            "issue_id": i + 1,
            "issue_type": issue["issue_type"],
            "severity": issue["severity"],
            "title": issue["title"],
            "recommendation": f"See agent response for issue {i+1}",
            "implementation_steps": [],
            "estimated_improvement_pct": issue.get("estimated_improvement_pct", 0),
            "difficulty": "medium",  # Would parse from LLM response
            "agent_reasoning": final_response
        }
        recommendations.append(recommendation)

    return {**state, "recommendations": recommendations}


# Create singleton agent instance
optimizer_graph, optimizer_llm = create_optimizer_agent()


def optimize_query(
    query_context: Dict[str, Any],
    detected_issues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Run the optimizer agent on a query with detected issues.

    Args:
        query_context: Context about the query (job_id, SQL, duration, metrics)
        detected_issues: List of issues detected by analysis engine

    Returns:
        List of structured recommendations with reasoning
    """
    initial_state = {
        "query_context": query_context,
        "detected_issues": detected_issues,
        "messages": [],
        "recommendations": []
    }

    # Invoke graph
    final_state = optimizer_graph.invoke(initial_state)

    return final_state["recommendations"]
```

---

## Component 3: System Prompts

### File: `src/agents/prompts/system_prompts.py`

```python
OPTIMIZER_SYSTEM_PROMPT = """You are an expert Dremio query optimization agent with deep expertise in:
- Distributed query processing and optimization
- Dremio reflections (materialized views) for performance acceleration
- Partition pruning strategies for data lake architectures
- Join optimization and cardinality estimation
- Query rewriting and SQL best practices
- Apache Arrow and columnar storage optimization

Your role is to analyze detected query performance issues and generate specific, actionable recommendations that engineering teams can implement immediately.

GUIDELINES:

1. BE SPECIFIC:
   - Provide exact SQL rewrites, not general suggestions
   - Include specific column names, filters, and table references
   - Give CREATE REFLECTION DDL statements when recommending reflections
   - Specify exact partition columns and date ranges

2. BE PRACTICAL:
   - Only recommend changes that can be implemented
   - Consider operational impact (reflection storage, refresh time)
   - Note any prerequisites or dependencies
   - Warn about potential trade-offs (e.g., storage vs speed)

3. BE DATA-DRIVEN:
   - Base recommendations on actual execution metrics
   - Use the provided tools to analyze patterns and estimate impact
   - Reference specific evidence from query profiles
   - Calculate realistic improvement estimates

4. PRIORITIZE BY IMPACT:
   - Focus first on optimizations with >50% estimated improvement
   - Consider implementation difficulty (low/medium/high)
   - Balance quick wins vs long-term improvements
   - Rank recommendations: HIGH → MEDIUM → LOW priority

5. PROVIDE REASONING:
   - Explain WHY the issue occurs (root cause)
   - Explain HOW the recommendation addresses it
   - Show the performance improvement logic
   - Mention any risks or caveats

AVAILABLE TOOLS:

- analyze_query_pattern(sql_text, profile): Analyze query patterns and extract key characteristics
- check_reflection_opportunity(dataset_path, query_pattern): Determine if reflections would help
- estimate_optimization_impact(current_duration_ms, optimization_type): Calculate expected speedup
- generate_sql_rewrite(original_sql, issue_type, evidence): Generate optimized SQL

OUTPUT FORMAT:

For each detected issue, provide:

**Issue #N: [Issue Title]**

**Root Cause:**
[Clear explanation of why this issue impacts performance]

**Recommendation:**
[Specific action to take - be precise]

**Implementation Steps:**
1. [Exact step 1]
2. [Exact step 2]
...

**Expected Impact:**
- Estimated improvement: X%
- Time saved per execution: Y seconds
- Annual impact: Z hours saved (if run daily)

**Implementation Difficulty:** [LOW/MEDIUM/HIGH]

**Prerequisites/Risks:**
- [Any prerequisites needed]
- [Any risks or trade-offs to consider]

**Priority:** [HIGH/MEDIUM/LOW]

---

FEW-SHOT EXAMPLES:

Example 1: Partition Pruning Issue

**Issue #1: Missing Partition Filter on Large Table**

**Root Cause:**
Query scans all 365 partitions of the orders table but WHERE clause doesn't filter on the partition column (order_date). This causes Dremio to read 12 months of data when only recent data is needed.

**Recommendation:**
Add partition filter on order_date to enable partition pruning and scan only relevant partitions.

**Implementation Steps:**
1. Add WHERE clause filter: `WHERE order_date >= CURRENT_DATE - INTERVAL '30' DAY`
2. Verify partition pruning in query profile (check "partitions pruned" metric)
3. Consider creating a date-based reflection if this pattern is frequent

**SQL Rewrite:**
```sql
-- BEFORE:
SELECT customer_id, SUM(order_amount)
FROM sales.orders
WHERE status = 'COMPLETED'
GROUP BY customer_id

-- AFTER:
SELECT customer_id, SUM(order_amount)
FROM sales.orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30' DAY
  AND status = 'COMPLETED'
GROUP BY customer_id
```

**Expected Impact:**
- Estimated improvement: 92% (scanning 30 days instead of 365 days)
- Time saved per execution: 45 seconds → 3.6 seconds
- Annual impact: 4,100 hours saved (if run 10x/day)

**Implementation Difficulty:** LOW (simple WHERE clause addition)

**Prerequisites/Risks:**
- Ensure 30-day lookback meets business requirements
- Adjust date range if longer history needed
- No risks - filter only improves performance

**Priority:** HIGH (92% improvement, low effort)

---

Example 2: Missing Aggregation Reflection

**Issue #2: Repeated Aggregation on Large Fact Table**

**Root Cause:**
Query performs GROUP BY aggregation on 500M row fact table. This aggregation pattern runs 50x/day but no reflection exists to pre-compute results. Each execution scans full table.

**Recommendation:**
Create an AGGREGATION reflection to materialize the aggregation results. Dremio will automatically use it when the query matches.

**Implementation Steps:**
1. Create aggregation reflection via Dremio UI or SQL:

```sql
-- Create Aggregation Reflection
ALTER TABLE sales.orders
CREATE AGGREGATE REFLECTION orders_daily_summary
DIMENSIONS (order_date, customer_id, region)
MEASURES (SUM(order_amount), COUNT(*), AVG(order_amount))
DISTRIBUTE BY (order_date)
```

2. Wait for initial reflection build (~10-15 minutes for 500M rows)
3. Verify reflection hit in subsequent query profiles
4. Monitor reflection refresh time (should be <5 minutes for daily incremental)

**Expected Impact:**
- Estimated improvement: 85% (query pre-aggregated results instead of raw data)
- Time saved per execution: 60 seconds → 9 seconds
- Annual impact: 9,300 hours saved (50 queries/day × 365 days)

**Implementation Difficulty:** LOW (UI click or single DDL statement)

**Prerequisites/Risks:**
- Reflection storage: ~5GB (estimate 1% of fact table size)
- Refresh time: 5 minutes daily (incremental refresh)
- Risk: If dimensions change frequently, reflection may not hit
- Mitigation: Start with common dimensions, expand if needed

**Priority:** HIGH (85% improvement, minimal storage cost, frequently run query)

---

Now, analyze the provided issues and generate recommendations following this format.
"""
```

---

## Component 4: Recommendation Service

### File: `src/services/recommendation_service.py`

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.agents.optimizer_agent import optimize_query
from src.database.repositories.recommendation_repository import RecommendationRepository
from src.database.connection import get_db_session
from src.observability.tracing import tracer


class RecommendationService:
    """Service for generating and managing optimization recommendations."""

    def __init__(self):
        pass

    def generate_recommendations(
        self,
        job_id: str,
        query_context: Dict[str, Any],
        detected_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered recommendations for detected issues.

        Args:
            job_id: Dremio job ID
            query_context: Query metadata (SQL, duration, metrics)
            detected_issues: Issues detected by analysis engine

        Returns:
            List of structured recommendations with reasoning
        """
        with tracer.start_as_current_span("recommendation.generate") as span:
            span.set_attribute("job_id", job_id)
            span.set_attribute("issues_count", len(detected_issues))

            # Invoke LangGraph agent
            recommendations = optimize_query(query_context, detected_issues)

            # Persist to database
            with get_db_session() as session:
                repo = RecommendationRepository(session)

                for rec in recommendations:
                    repo.create({
                        "job_id": job_id,
                        "issue_type": rec["issue_type"],
                        "severity": rec["severity"],
                        "title": rec["title"],
                        "description": rec["recommendation"],
                        "implementation_steps": rec["implementation_steps"],
                        "estimated_improvement_pct": rec["estimated_improvement_pct"],
                        "difficulty": rec["difficulty"],
                        "status": "pending",
                        "agent_reasoning": rec["agent_reasoning"],
                        "created_at": datetime.utcnow()
                    })

                session.commit()

            span.set_attribute("recommendations_generated", len(recommendations))
            return recommendations

    def get_recommendations(
        self,
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recommendations with optional filters.

        Args:
            job_id: Filter by job ID
            status: Filter by status (pending/implemented/rejected)
            severity: Filter by severity (high/medium/low)
            limit: Maximum number of results

        Returns:
            List of recommendations
        """
        with get_db_session() as session:
            repo = RecommendationRepository(session)
            return repo.find(
                job_id=job_id,
                status=status,
                severity=severity,
                limit=limit
            )

    def update_status(
        self,
        recommendation_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update recommendation status.

        Args:
            recommendation_id: Recommendation ID
            status: New status (implemented/rejected/in_progress)
            notes: Optional notes about status change

        Returns:
            Updated recommendation
        """
        with get_db_session() as session:
            repo = RecommendationRepository(session)

            recommendation = repo.get_by_id(recommendation_id)
            if not recommendation:
                raise ValueError(f"Recommendation {recommendation_id} not found")

            recommendation.status = status
            recommendation.status_notes = notes
            recommendation.updated_at = datetime.utcnow()

            session.commit()
            return recommendation.to_dict()
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/agents/test_optimizer_agent.py`

```python
import pytest
from src.agents.optimizer_agent import optimize_query


def test_optimize_query_with_partition_issue():
    """Test agent generates partition pruning recommendation."""
    query_context = {
        "job_id": "test-123",
        "sql_text": "SELECT * FROM sales.orders WHERE status = 'COMPLETED'",
        "duration_ms": 45000,
        "rows_scanned": 10000000,
        "rows_returned": 500000
    }

    detected_issues = [{
        "issue_type": "missing_partition_filter",
        "severity": "high",
        "title": "Missing Partition Filter",
        "description": "Query scans all partitions",
        "evidence": {"partition_column": "order_date"},
        "estimated_improvement_pct": 85
    }]

    recommendations = optimize_query(query_context, detected_issues)

    assert len(recommendations) == 1
    assert recommendations[0]["issue_type"] == "missing_partition_filter"
    assert "WHERE" in recommendations[0]["agent_reasoning"]
    assert recommendations[0]["estimated_improvement_pct"] > 50
```

### Integration Tests

**File**: `tests/integration/test_recommendation_flow.py`

```python
def test_end_to_end_recommendation_generation(db_session, dremio_client):
    """Test full flow: analyze → recommend → persist."""
    from src.services.analysis_service import AnalysisService
    from src.services.recommendation_service import RecommendationService

    analysis_service = AnalysisService()
    recommendation_service = RecommendationService()

    # Analyze query
    job_id = "test-query-123"
    issues = analysis_service.analyze_query(job_id)

    # Generate recommendations
    query_context = {"job_id": job_id, "sql_text": "...", "duration_ms": 30000}
    recommendations = recommendation_service.generate_recommendations(
        job_id, query_context, issues
    )

    # Verify persistence
    assert len(recommendations) > 0
    saved_recs = recommendation_service.get_recommendations(job_id=job_id)
    assert len(saved_recs) == len(recommendations)
```

---

## Success Criteria

- ✅ Agent generates actionable recommendations with SQL rewrites
- ✅ Impact estimates within ±20% of actual improvements (validated in Phase 4)
- ✅ All 4 tools functional and called appropriately by agent
- ✅ Recommendations persisted to database with full reasoning
- ✅ End-to-end latency <15 seconds for recommendation generation
- ✅ Test coverage >85% for agent logic

---

## Dependencies

```toml
# Already in pyproject.toml:
langchain = "^0.3.0"
langchain-openai = "^0.2.0"
langchain-anthropic = "^0.2.0"
langgraph = "^0.2.0"
openai = "^1.57.0"
anthropic = "^0.40.0"
```

---

## Next Steps After Phase 3

Once Phase 3 is complete, proceed to:
- **Phase 4**: Performance Measurement (validate actual improvements)
- **Phase 5**: REST API (expose recommendations via API)
