"""app.integrations — External service gateway modules.

All outbound HTTP calls to third-party/SAP APIs must go through a gateway
in this package, never via bare `requests` calls in services or blueprints.

This mirrors the `app/ai/gateway.py` pattern: every call is:
  - Authenticated (token injected by the gateway)
  - Retried with exponential backoff
  - Circuit-broken to prevent cascade failures
  - Logged to the relevant audit table

Current gateways:
  alm_gateway.ALMGateway — SAP Cloud ALM REST API (FDD-F07 Faz B)
"""
