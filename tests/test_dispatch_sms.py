from src.dispatch_sms import WorkOrderAlert, needs_technician_nudge, send_dispatch_alert


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str]] = []

    def send_batch(self, messages: list[dict[str, str]], idempotency_key: str) -> dict[str, list[str]]:
        self.calls.append((messages, idempotency_key))
        return {"message_ids": ["sms-1042"]}


def test_dispatched_photo_work_order_without_follow_up_sends_one_nudge() -> None:
    alert = WorkOrderAlert("WO-1042", "+15550000001", 3, "dispatched", "")
    client = RecordingClient()

    result = send_dispatch_alert(alert, client)  # type: ignore[arg-type]

    assert needs_technician_nudge(alert) is True
    assert result.action == "sms_sent"
    assert result.message_ids == ["sms-1042"]
    assert client.calls == [
        ([{"to": "+15550000001", "text": "Work order WO-1042: 3 photo(s) are ready. Please add your technician follow-up."}], "work-order-follow-up-WO-1042")
    ]


def test_completed_follow_up_does_not_send_another_sms() -> None:
    alert = WorkOrderAlert("WO-1043", "+15550000001", 1, "dispatched", "replaced valve")
    client = RecordingClient()

    result = send_dispatch_alert(alert, client)  # type: ignore[arg-type]

    assert result.action == "no_sms_needed"
    assert client.calls == []
