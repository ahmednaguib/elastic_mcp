import asyncio

from fastmcp import Client

import src.elasticsearch as es_mod
import src.server as server_mod
from src.server import mcp


class FakeES:
    def __init__(self, hits=None):
        self.search_calls = []
        self.hits = hits or []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return {"hits": {"hits": self.hits}}


def _run(coro):
    return asyncio.run(coro)


def list_tools():
    async def _list():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            return {t.name: t.input_schema for t in tools}

    return _run(_list())


def invoke_tool(arguments, raise_on_error=True):
    async def _call():
        async with Client(mcp) as client:
            return await client.call_tool(
                "search_application_logs",
                arguments,
                raise_on_error=raise_on_error,
            )

    return _run(_call())


class TestRegistration:
    def test_search_application_logs_registered(self):
        assert "search_application_logs" in list_tools()

    def test_schema_exposes_all_parameters(self):
        schema = list_tools()["search_application_logs"]
        props = schema.get("properties", {})
        for param in [
            "query",
            "start_time",
            "end_time",
            "service",
            "environment",
            "level",
            "status_code",
            "limit",
            "sort",
        ]:
            assert param in props

    def test_query_is_required(self):
        schema = list_tools()["search_application_logs"]
        assert "query" in schema.get("required", [])

    def test_optional_parameters_are_not_required(self):
        schema = list_tools()["search_application_logs"]
        required = set(schema.get("required", []))
        for param in ["start_time", "end_time", "service", "level", "sort"]:
            assert param not in required


class TestArgPassthrough:
    def test_all_arguments_forwarded(self, monkeypatch):
        captured = {}

        def stub(**kwargs):
            captured.update(kwargs)
            return [{"message": "ok"}]

        monkeypatch.setattr(server_mod, "search_logs", stub)

        res = invoke_tool(
            {
                "query": "payment",
                "start_time": "2026-09-09T08:00:00Z",
                "end_time": "2026-09-09T09:00:00Z",
                "service": "checkout",
                "environment": "production",
                "level": "ERROR",
                "status_code": 504,
                "limit": 5,
                "sort": "relevance",
            }
        )

        assert captured == {
            "query": "payment",
            "start_time": "2026-09-09T08:00:00Z",
            "end_time": "2026-09-09T09:00:00Z",
            "service": "checkout",
            "environment": "production",
            "level": "ERROR",
            "status_code": 504,
            "limit": 5,
            "sort": "relevance",
        }
        assert res.is_error is False

    def test_defaults_used_when_omitted(self, monkeypatch):
        captured = {}

        def stub(**kwargs):
            captured.update(kwargs)
            return []

        monkeypatch.setattr(server_mod, "search_logs", stub)

        invoke_tool({"query": "payment"})

        assert captured["limit"] == 20
        assert captured["sort"] == "timestamp"
        assert captured["service"] is None
        assert captured["level"] is None


class TestFullStack:
    def test_tool_returns_projected_docs(self, monkeypatch):
        fake_es = FakeES(
            hits=[
                {
                    "_source": {
                        "@timestamp": "2026-09-09T08:30:00Z",
                        "service": "checkout",
                        "level": "ERROR",
                        "message": "Payment request timed out",
                        "endpoint": "/api/checkout/payment",
                        "status_code": 504,
                        "latency_ms": 4827.15,
                        "deployment": "checkout-v1.82",
                    }
                }
            ]
        )
        monkeypatch.setattr(es_mod, "es", fake_es)

        res = invoke_tool({"query": "payment", "limit": 1})

        assert res.is_error is False
        assert res.structured_content == {
            "result": [
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
        }

    def test_tool_error_propagates(self, monkeypatch):
        def boom(**kwargs):
            raise RuntimeError("elasticsearch down")

        monkeypatch.setattr(server_mod, "search_logs", boom)

        res = invoke_tool({"query": "payment"}, raise_on_error=False)

        assert res.is_error is True