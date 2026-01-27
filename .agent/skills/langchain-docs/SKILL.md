---
name: langchain-docs
description: >
  Use this skill for requests related to LangChain, LangGraph, or Deep Agents 
  to fetch relevant documentation and provide accurate, up-to-date guidance.
metadata:
  version: 1.0.0
  author: SkullRender AI
  tags: [langchain, langgraph, deep-agents, mcp, documentation]
  mcp_server: https://docs.langchain.com/mcp
---

# SKILL: LangChain Documentation Expert

> [!IMPORTANT]
> **Purpose**: Access LangChain's official documentation in real-time via MCP.
> Always fetch fresh docs to avoid outdated information.
>
> **Documentation**: [docs.langchain.com](https://docs.langchain.com/)

## When to Use

Load this skill when:
- User asks about LangChain, LangGraph, or Deep Agents concepts
- Implementing multi-agent systems or state graphs
- Debugging LangChain/LangGraph code
- Learning about middleware, backends, or skills patterns
- Comparing Phylactery architecture with LangChain standards

## Critical Patterns

### 1. Documentation Workflow

**Step-by-step process:**

1. **Fetch the Documentation Index**
   ```
   MCP Tool: fetch_url
   URL: https://docs.langchain.com/llms.txt
   ```
   This provides a structured list of all available documentation with descriptions.

2. **Select Relevant Documentation**
   Based on the user's question, identify 2-4 most relevant documentation URLs from the index.
   
   **Prioritize:**
   - Specific how-to guides for implementation questions
   - Core concept pages for understanding questions
   - Tutorials for end-to-end examples
   - Reference docs for API details

3. **Fetch Selected Documentation**
   ```
   MCP Tool: fetch_url
   URL: <selected_doc_url>
   ```
   Fetch each selected documentation page.

4. **Provide Accurate Guidance**
   After reading the documentation:
   - Answer the user's question with citations
   - Include code examples from the docs
   - Link to relevant pages for deeper reading
   - Highlight differences with Phylactery's approach (if applicable)

### 2. MCP Server Connection

**Server Details:**
- **URL**: `https://docs.langchain.com/mcp`
- **Type**: HTTP MCP Server (Mintlify-hosted)
- **Tools Available**: `fetch_url`, `search_docs`

**Connection Test:**
```python
# Verify MCP connection
mcp_client = get_mcp_client("langchain-docs")
result = await mcp_client.call_tool(
    "fetch_url",
    {"url": "https://docs.langchain.com/llms.txt"}
)
```

### 3. Progressive Disclosure

**This skill should only load when:**
- User query contains keywords: "langchain", "langgraph", "deep agents", "middleware", "backends"
- User explicitly requests LangChain documentation
- Comparing architectures or patterns

**Do NOT load for:**
- General Python questions
- Angular/Frontend questions
- Questions about other frameworks

## Code Examples

### Example: Fetching Deep Agents Middleware Docs

```python
# 1. Get index
index = await fetch_url("https://docs.langchain.com/llms.txt")

# 2. Search for "middleware"
relevant_docs = [
    "https://docs.langchain.com/oss/deepagents/middleware",
    "https://docs.langchain.com/oss/deepagents/harness"
]

# 3. Fetch each doc
for doc_url in relevant_docs:
    content = await fetch_url(doc_url)
    # Parse and extract relevant sections
```

### Example: Comparing with Phylactery

When user asks: "How does LangChain handle filesystem tools?"

**Response Pattern:**
```markdown
According to [LangChain Deep Agents Docs](https://docs.langchain.com/oss/deepagents/harness):

**LangChain Approach:**
- 6 filesystem tools: ls, read_file, write_file, edit_file, glob, grep
- Pluggable backends: StateBackend, StoreBackend, FilesystemBackend, CompositeBackend
- Automatic tool result eviction (>20k tokens)

**Phylactery Current State:**
- Uses MCP filesystem server (external)
- No native filesystem middleware yet
- Planned for Phase 2 (see ROADMAP.md)

**Recommendation:** Implement FilesystemMiddleware following LangChain's pattern.
```

## Anti-Patterns

### Don't: Use Outdated Information
❌ **Never** answer LangChain questions from training data alone.
✅ **Always** fetch fresh documentation via MCP.

**Why:** LangChain evolves rapidly. Deep Agents was released in late 2024.

### Don't: Fetch Entire Documentation
❌ **Never** fetch all docs at once (hundreds of pages).
✅ **Always** use the index to select 2-4 most relevant pages.

**Why:** Context window limits and performance.

### Don't: Ignore Phylactery Context
❌ **Never** recommend LangChain patterns without considering Phylactery's architecture.
✅ **Always** explain how to adapt LangChain concepts to Phylactery.

**Why:** We're building on LangChain ideas, not copying blindly.

## Quick Reference

### Common Queries

| User Question | Relevant Docs |
|---------------|---------------|
| "How do LangChain agents work?" | `/oss/deepagents/harness`, `/oss/python/concepts/products` |
| "What are LangGraph state graphs?" | `/oss/langgraph/concepts/state-graph` |
| "How to implement middleware?" | `/oss/deepagents/middleware` |
| "What are backends?" | `/oss/deepagents/backends` |
| "How to create skills?" | `/oss/deepagents/skills` |

### MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `fetch_url` | Get documentation page | `fetch_url("https://docs.langchain.com/llms.txt")` |
| `search_docs` | Search across all docs | `search_docs("filesystem middleware")` |

### Key Concepts to Know

- **Deep Agents**: LangChain's agent harness with built-in tools
- **Middleware**: Composable capabilities (TodoList, Filesystem, SubAgent)
- **Backends**: Storage abstraction (State, Store, Filesystem, Composite)
- **Skills**: Reusable agent capabilities (Agent Skills standard)
- **Progressive Disclosure**: Load context only when needed

---

**Last Updated:** 2026-01-26  
**Maintained By:** SkullRender AI (Phylactery Team)
