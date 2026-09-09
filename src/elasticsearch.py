import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

ELASTICSEARCH_URL = os.getenv(
    "ELASTICSEARCH_URL",
    "http://localhost:9200",
)

ELASTICSEARCH_INDEX = os.getenv(
    "ELASTICSEARCH_INDEX",
    "logs",
)

es = Elasticsearch(ELASTICSEARCH_URL)

MAX_LIMIT = 100

RESPONSE_FIELDS = {
    "@timestamp": "timestamp",
    "service": "service",
    "level": "level",
    "message": "message",
    "endpoint": "endpoint",
    "status_code": "status",
    "latency_ms": "latency",
    "deployment": "deployment",
}

QUERY_FIELDS = [
    "message",
    "service",
    "endpoint",
    "deployment",
]


def search_logs(
    query: str,
    service: str | None = None,
    environment: str | None = None,
    level: str | None = None,
    status_code: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 20,
    sort: str = "timestamp",
):
    filters = []

    for field, value in (
        ("service", service),
        ("environment", environment),
        ("level", level),
    ):
        if value:
            filters.append({"term": {field: value}})

    if status_code is not None:
        filters.append({"term": {"status_code": status_code}})

    if start_time or end_time:
        range_filter = {"range": {"@timestamp": {}}}
        if start_time:
            range_filter["range"]["@timestamp"]["gte"] = start_time
        if end_time:
            range_filter["range"]["@timestamp"]["lte"] = end_time
        filters.append(range_filter)

    if query.strip():
        query_clause = {
            "multi_match": {
                "query": query,
                "fields": QUERY_FIELDS,
            }
        }
    else:
        query_clause = {"match_all": {}}

    search_query = {
        "bool": {
            "must": [query_clause],
            "filter": filters,
        }
    }

    if sort == "relevance":
        sort_options = [
            {"_score": {"order": "desc"}},
            {"@timestamp": {"order": "desc"}},
        ]
    else:
        sort_options = [{"@timestamp": {"order": "desc"}}]

    response = es.search(
        index=ELASTICSEARCH_INDEX,
        query=search_query,
        size=min(limit, MAX_LIMIT),
        sort=sort_options,
        _source=list(RESPONSE_FIELDS),
    )

    return [
        {
            new_name: hit["_source"].get(old_name)
            for old_name, new_name in RESPONSE_FIELDS.items()
        }
        for hit in response["hits"]["hits"]
    ]