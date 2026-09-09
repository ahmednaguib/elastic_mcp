# elastic_mcp
A local Model Context Protocol (MCP) server that exposes Elasticsearch application logs to MCP-compatible AI clients such as ChatGPT, Claude, and MCP Inspector.

The current MVP provides a search_application_logs tool backed by Elasticsearch.

## Table of Contents

- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [1. Create the Python environment](#1-create-the-python-environment)
- [2. Configure environment variables](#2-configure-environment-variables)
- [3. Start Elasticsearch](#3-start-elasticsearch)
- [4. Generate synthetic application data](#4-generate-synthetic-application-data)
- [5. Create the Elasticsearch index and import data](#5-create-the-elasticsearch-index-and-import-data)
- [6. Start the MCP server](#6-start-the-mcp-server)
- [7. Test the MCP server with MCP Inspector](#7-test-the-mcp-server-with-mcp-inspector)
- [8. Run the tests](#8-run-the-tests)

## Project structure

```
elastic-mcp/
├── src/
│   ├── server.py
│   └── elasticsearch.py
│
├── sample/
│   └── elastic-mcp-synthetic-data/
│       ├── data/
│       └── scripts/
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites
- Python 3.10+
- Docker / Docker Compose
- Node.js + npm (only needed for MCP Inspector)

Verify:
```
python3 --version
docker --version
docker compose version
node --version
npm --version
```

## 1. Create the Python environment

From the project root:
```
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt
```

## 2. Configure environment variables

Create .env:

```
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=logs
```

## 3. Start Elasticsearch

Start the local Elasticsearch container:
```
docker compose up -d
```
Check that Elasticsearch is running:
```
curl http://localhost:9200
```
You should receive an Elasticsearch cluster response.

## 4. Generate synthetic application data

The project includes a synthetic production-like dataset.

Generate the data:
```
python scripts/generate_data.py
```
This creates:
```
data/events.ndjson
```
The dataset contains services such as:

- api-gateway
- checkout
- payments
- orders
- users
- notifications

It also contains a deliberately injected checkout incident:

07:50 UTC
checkout-v1.82 deployed

08:00 UTC
checkout latency/error spike begins

08:00-09:00 UTC
payment timeouts and 5xx responses increase

## 5. Create the Elasticsearch index and import data

import the data:
```
./scripts/import_data.sh
````
Verify the document count:
```
curl "http://localhost:9200/logs/_count?pretty"
```
You should see approximately:
```
{
  "count": 100001
}
```
## 6. Start the MCP server

From the project root:
```
python -m src.server
```
The server starts with an SSE transport on http://localhost:8000/sse.

Override the transport (e.g. for stdio-based chat clients) with:
```
MCP_TRANSPORT=stdio python -m src.server
```
Keep this terminal running.

## 7. Test the MCP server with MCP Inspector

In a second terminal, from the project root:
```
npx @modelcontextprotocol/inspector
```
In the Inspector, connect using:
```
Transport type: SSE

URL: http://localhost:8000/sse
```
The server should expose:

eng-intelligence

```
Tools
└── search_application_logs
    ├── query
    ├── service
    ├── level
    └── limit
```
Try a query such as:
```
query: payment
service: checkout
limit: 10
```
You should receive matching Elasticsearch documents.

## 8. Run the tests

Run the test suite (no Elasticsearch connection required — the client is mocked):
```
python -m pytest
```
