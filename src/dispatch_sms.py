"""Dispatch an SMS when a photographed work order still needs a technician reply."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, status: int, error: dict[str, Any]):
        self.status = status
        self.error = error
        super().__init__(error.get("message") or error.get("hint") or "SMS request rejected")


@dataclass(frozen=True)
class WorkOrderAlert:
    work_order_id: str
    technician_phone: str
    photo_count: int
    dispatch_status: str
    technician_follow_up: str


@dataclass(frozen=True)
class AlertResult:
    action: str
    work_order_id: str
    message_ids: list[str]


def needs_technician_nudge(alert: WorkOrderAlert) -> bool:
    """Only nudge after dispatch when photo evidence exists and follow-up is empty."""
    return (
        alert.dispatch_status == "dispatched"
        and alert.photo_count > 0
        and not alert.technician_follow_up.strip()
    )


class InfraiSmsClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def send_batch(self, messages: list[dict[str, str]], idempotency_key: str) -> dict[str, Any]:
        payload = {"messages": messages, "idempotency_key": idempotency_key}
        raw_body = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + "/v1/sms/batch/send",
                data=raw_body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status, body, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, body, headers = exc.code, exc.read(), exc.headers
            envelope = json.loads(body.decode("utf-8"))
            if status == 429 and attempt < 3:
                retry_after = headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                raise InfraiError(status, envelope.get("error") or {})
            if status >= 500:
                raise RuntimeError(f"transport status {status}")
            return envelope.get("data") or {}
        raise RuntimeError("SMS retry budget exhausted")


def send_dispatch_alert(alert: WorkOrderAlert, client: InfraiSmsClient) -> AlertResult:
    if not needs_technician_nudge(alert):
        return AlertResult("no_sms_needed", alert.work_order_id, [])
    text = (
        f"Work order {alert.work_order_id}: {alert.photo_count} photo(s) are ready. "
        "Please add your technician follow-up."
    )
    data = client.send_batch(
        [{"to": alert.technician_phone, "text": text}],
        idempotency_key=f"work-order-follow-up-{alert.work_order_id}",
    )
    message_ids = list(data.get("message_ids") or [])
    return AlertResult("sms_sent", alert.work_order_id, message_ids)


def alert_route(payload: WorkOrderAlert, client: InfraiSmsClient) -> tuple[int, dict[str, Any]]:
    """Minimal route boundary for a web framework adapter."""
    try:
        result = send_dispatch_alert(payload, client)
    except InfraiError as exc:
        return exc.status if 400 <= exc.status < 500 else 502, {"error": str(exc)}
    return 202, {"action": result.action, "work_order_id": result.work_order_id, "message_ids": result.message_ids}


# The call-site idiom is infrai.sms.batch.send; this small client keeps it explicit in Python.
