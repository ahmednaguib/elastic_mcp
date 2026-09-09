import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

SERVICES = {
    "api-gateway": ["/api/*"],
    "users": ["/api/users", "/api/users/{id}"],
    "orders": ["/api/orders", "/api/orders/{id}"],
    "payments": ["/api/payments", "/api/payments/authorize"],
    "checkout": ["/api/checkout", "/api/checkout/payment"],
    "notifications": ["/api/notifications"],
}

START = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
END = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
EVENTS = 100_000

def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")

def normal_event(dt):
    service = random.choice(list(SERVICES))
    endpoint = random.choice(SERVICES[service])
    latency = max(5, random.gauss(180 if service == "checkout" else 120, 45))
    status = 200 if random.random() < 0.985 else random.choice([400, 404, 500])
    level = "INFO" if status < 500 else "ERROR"
    return {
        "@timestamp": iso(dt),
        "service": service,
        "environment": "production",
        "level": level,
        "message": "Request completed" if status < 500 else "Request failed",
        "endpoint": endpoint,
        "status_code": status,
        "latency_ms": round(latency, 2),
        "trace_id": uuid.uuid4().hex,
        "deployment": "checkout-v1.81" if service == "checkout" else f"{service}-v2.14",
        "event_type": "request",
    }

def incident_event(dt):
    service = "checkout"
    endpoint = "/api/checkout/payment"
    is_timeout = random.random() < 0.55
    latency = max(1000, random.gauss(4800, 700))
    status = 504 if is_timeout else 500
    return {
        "@timestamp": iso(dt),
        "service": service,
        "environment": "production",
        "level": "ERROR",
        "message": "Payment request timed out" if is_timeout else "Payment provider error",
        "endpoint": endpoint,
        "status_code": status,
        "latency_ms": round(latency, 2),
        "trace_id": uuid.uuid4().hex,
        "deployment": "checkout-v1.82",
        "event_type": "request",
    }

def deployment_event(dt):
    return {
        "@timestamp": iso(dt),
        "service": "checkout",
        "environment": "production",
        "level": "INFO",
        "message": "Deployment completed: checkout-v1.82",
        "endpoint": "/internal/deploy",
        "status_code": 200,
        "latency_ms": 32,
        "trace_id": uuid.uuid4().hex,
        "deployment": "checkout-v1.82",
        "event_type": "deployment",
    }

def main():
    out = Path(__file__).resolve().parent.parent / "data"
    out.mkdir(exist_ok=True)
    path = out / "events.ndjson"

    incident_start = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)
    deployment_time = incident_start - timedelta(minutes=10)

    with path.open("w") as f:
        # Normal traffic.
        for _ in range(EVENTS):
            dt = START + (END - START) * random.random()

            # Inject deployment event and a strong checkout incident.
            if deployment_time <= dt < incident_start:
                event = normal_event(dt)
            elif incident_start <= dt <= incident_start + timedelta(hours=1):
                event = incident_event(dt) if random.random() < 0.65 else normal_event(dt)
            else:
                event = normal_event(dt)

            f.write(json.dumps({"index": {"_index": "logs"}}) + "\n")
            f.write(json.dumps(event) + "\n")

        event = deployment_event(deployment_time)
        f.write(json.dumps({"index": {"_index": "logs"}}) + "\n")
        f.write(json.dumps(event) + "\n")

    print(f"Generated {EVENTS + 1:,} events: {path}")

if __name__ == "__main__":
    main()
