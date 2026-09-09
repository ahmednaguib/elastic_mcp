# elastic-mcp synthetic data

Generate realistic application events with a deliberately injected checkout incident.

## Generate
python scripts/generate_data.py

## Index
./scripts/import_data.sh

Incident:
- 07:50 UTC: checkout-v1.82 deployment
- 08:00 UTC: checkout latency/error spike begins
- 08:00-09:00 UTC: payment timeouts and 5xx responses increase
