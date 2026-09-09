import os

from fastmcp import FastMCP

from src.elasticsearch import search_logs

mcp = FastMCP(
    name="eng-intelligence"
)


@mcp.tool
def search_application_logs(
    query: str,
    start_time: str | None = None,
    end_time: str | None = None,
    service: str | None = None,
    environment: str | None = None,
    level: str | None = None,
    status_code: int | None = None,
    limit: int = 20,
    sort: str = "timestamp",
) -> list[dict]:
    """
    Search production application logs.

    Use this when investigating errors, failures,
    deployments, latency problems, or other issues
    in the application.

    Args:
        query: Free-text search across message, service, endpoint and deployment.
        start_time: Only return logs at or after this ISO-8601 timestamp (e.g. "2026-09-09T08:00:00Z").
        end_time: Only return logs at or before this ISO-8601 timestamp (e.g. "2026-09-09T09:00:00Z").
        service: Filter by service name (e.g. "checkout", "payments").
        environment: Filter by deployment environment (e.g. "production").
        level: Filter by log level (e.g. "INFO", "ERROR").
        status_code: Filter by HTTP status code (e.g. 500, 504).
        limit: Maximum number of results to return (default 20, max 100).
        sort: "timestamp" for newest first (default) or "relevance" for best match.
    """

    return search_logs(
        query=query,
        service=service,
        environment=environment,
        level=level,
        status_code=status_code,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        sort=sort,
    )


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "sse"))