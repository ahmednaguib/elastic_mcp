import pytest

import src.elasticsearch as es_mod
from src.elasticsearch import RESPONSE_FIELDS, search_logs


class FakeES:
    def __init__(self, hits=None):
        self.search_calls = []
        self.hits = hits or []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return {"hits": {"hits": self.hits}}


@pytest.fixture
def fake_es(monkeypatch):
    es = FakeES()
    monkeypatch.setattr(es_mod, "es", es)
    return es


def search_kwargs(fake_es):
    return fake_es.search_calls[-1]


def search_query(fake_es):
    return search_kwargs(fake_es)["query"]


FULL_HIT = {
    "@timestamp": "2026-09-09T08:30:00Z",
    "service": "checkout",
    "environment": "production",
    "level": "ERROR",
    "message": "Payment request timed out",
    "endpoint": "/api/checkout/payment",
    "status_code": 504,
    "latency_ms": 4827.15,
    "trace_id": "abc123",
    "deployment": "checkout-v1.82",
    "event_type": "request",
}


class TestQuery:
    def test_empty_query_uses_match_all(self, fake_es):
        search_logs("")
        must = search_query(fake_es)["bool"]["must"]
        assert must == [{"match_all": {}}]

    def test_non_empty_query_uses_multi_match(self, fake_es):
        search_logs("payment")
        assert search_query(fake_es)["bool"]["must"] == [
            {
                "multi_match": {
                    "query": "payment",
                    "fields": ["message", "service", "endpoint", "deployment"],
                }
            }
        ]

    def test_no_filters_without_arguments(self, fake_es):
        search_logs("payment")
        assert search_query(fake_es)["bool"]["filter"] == []

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            ({"service": "checkout"}, [{"term": {"service": "checkout"}}]),
            (
                {"service": "checkout", "level": "ERROR"},
                [{"term": {"service": "checkout"}}, {"term": {"level": "ERROR"}}],
            ),
            (
                {"environment": "production"},
                [{"term": {"environment": "production"}}],
            ),
            ({"status_code": 500}, [{"term": {"status_code": 500}}]),
        ],
    )
    def test_structured_filters(self, fake_es, kwargs, expected):
        search_logs("payment", **kwargs)
        assert search_query(fake_es)["bool"]["filter"] == expected

    def test_time_range_filter_bounds(self, fake_es):
        search_logs(
            "payment",
            start_time="2026-09-09T08:00:00Z",
            end_time="2026-09-09T09:00:00Z",
        )
        assert search_query(fake_es)["bool"]["filter"] == [
            {
                "range": {
                    "@timestamp": {
                        "gte": "2026-09-09T08:00:00Z",
                        "lte": "2026-09-09T09:00:00Z",
                    }
                }
            }
        ]

    def test_start_time_only(self, fake_es):
        search_logs("payment", start_time="2026-09-09T08:00:00Z")
        assert search_query(fake_es)["bool"]["filter"] == [
            {"range": {"@timestamp": {"gte": "2026-09-09T08:00:00Z"}}}
        ]

    def test_end_time_only(self, fake_es):
        search_logs("payment", end_time="2026-09-09T09:00:00Z")
        assert search_query(fake_es)["bool"]["filter"] == [
            {"range": {"@timestamp": {"lte": "2026-09-09T09:00:00Z"}}}
        ]

    def test_filters_combined_with_time_range(self, fake_es):
        search_logs(
            "payment",
            service="checkout",
            level="ERROR",
            start_time="2026-09-09T08:00:00Z",
            end_time="2026-09-09T09:00:00Z",
        )
        assert search_query(fake_es)["bool"]["filter"] == [
            {"term": {"service": "checkout"}},
            {"term": {"level": "ERROR"}},
            {
                "range": {
                    "@timestamp": {
                        "gte": "2026-09-09T08:00:00Z",
                        "lte": "2026-09-09T09:00:00Z",
                    }
                }
            },
        ]


class TestSorting:
    def test_default_sort_by_timestamp_desc(self, fake_es):
        search_logs("payment")
        assert search_kwargs(fake_es)["sort"] == [
            {"@timestamp": {"order": "desc"}}
        ]

    def test_relevance_sort(self, fake_es):
        search_logs("payment", sort="relevance")
        assert search_kwargs(fake_es)["sort"] == [
            {"_score": {"order": "desc"}},
            {"@timestamp": {"order": "desc"}},
        ]


class TestLimiting:
    def test_limit_passed_through(self, fake_es):
        search_logs("payment", limit=5)
        assert search_kwargs(fake_es)["size"] == 5

    def test_limit_capped_at_100(self, fake_es):
        search_logs("payment", limit=500)
        assert search_kwargs(fake_es)["size"] == 100

    def test_default_limit(self, fake_es):
        search_logs("payment")
        assert search_kwargs(fake_es)["size"] == 20


class TestSourceRestriction:
    def test_fetches_only_response_fields(self, fake_es):
        search_logs("payment")
        assert search_kwargs(fake_es)["_source"] == list(RESPONSE_FIELDS)


class TestProjection:
    def test_returns_concise_fields(self, fake_es):
        fake_es.hits = [{"_source": FULL_HIT}]
        result = search_logs("payment")
        assert result == [
            {
                "timestamp": "2026-09-09T08:30:00Z",
                "service": "checkout",
                "level": "ERROR",
                "message": "Payment request timed out",
                "endpoint": "/api/checkout/payment",
                "status": 504,
                "latency": 4827.15,
                "deployment": "checkout-v1.82",
            }
        ]

    def test_omits_non_response_fields(self, fake_es):
        fake_es.hits = [{"_source": FULL_HIT}]
        result = search_logs("payment")
        assert "trace_id" not in result[0]
        assert "event_type" not in result[0]

    def test_missing_fields_become_none(self, fake_es):
        fake_es.hits = [{"_source": {"message": "Request completed"}}]
        result = search_logs("payment")
        assert result[0]["timestamp"] is None
        assert result[0]["message"] == "Request completed"

    def test_no_hits_returns_empty_list(self, fake_es):
        assert search_logs("payment") == []