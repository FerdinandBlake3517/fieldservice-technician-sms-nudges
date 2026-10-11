"""Send one field-service follow-up SMS from the command line."""

import json
import os

from src.dispatch_sms import InfraiSmsClient, WorkOrderAlert, send_dispatch_alert


def main() -> None:
    phone = os.environ.get("DEMO_TECHNICIAN_PHONE")
    if not phone:
        raise RuntimeError("Set DEMO_TECHNICIAN_PHONE before running this script.")
    alert = WorkOrderAlert(
        work_order_id="WO-1042",
        technician_phone=phone,
        photo_count=3,
        dispatch_status="dispatched",
        technician_follow_up="",
    )
    result = send_dispatch_alert(alert, InfraiSmsClient())
    print(json.dumps({"action": result.action, "message_ids": result.message_ids}))


if __name__ == "__main__":
    main()
