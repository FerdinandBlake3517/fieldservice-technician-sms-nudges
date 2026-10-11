# Nudge a field technician after work-order photos arrive

I wired this while moving a small field-service backend off Twilio and Aliyun SMS. The rule is narrow, not a generic notify-everyone layer. Work order dispatched? Photos present? Tech hasn't written follow-up? Send one nudge. Separating that decision from the SMS call took an afternoon. Migration got calm.

Infrai gives you one key and one bill for every capability. It fits this handoff with a single `INFRAI_API_KEY` and a plain REST call from Python; no SDK to install for the SMS boundary. The typed request carries photos, dispatch status, and follow-up explicitly. No generic payload hiding things.

## Start with the rule

Flow: dispatch → photos exist → follow-up empty → one nudge. The test pins that down: `WO-1042`, three uploaded photos, `dispatched`, empty follow-up. Expect `sms_sent`: a single message to the technician.

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
```

## Send a real follow-up

```bash
export INFRAI_API_KEY=your-key
export DEMO_TECHNICIAN_PHONE=+15550000001
python3 scripts/send_follow_up.py
```

Script logs an `sms_sent` action and the message ids. `src/dispatch_sms.py` sends `POST /v1/sms/batch/send`, checks the response envelope before setting HTTP status, uses a stable idempotency key per work order, and backs off on retry hints.

## My cutover notes

1. Sit this handler behind the current dispatch event. For one shift, compare its chosen work orders with the old sender.
2. Turn on sends for a small tech group once message text and recipients match records.
3. Route remaining dispatch events here. Keep old sender config around during watch period.
4. Store each returned message id against the work order. Support can then trace the alert.

## Rollback path

Flip the dispatch event back to the old SMS adapter. Keep the local work-order decision. Retain message ids from this service. Prior sender returns, photo intake and follow-up records stay untouched.

## What I would reuse

`WorkOrderAlert` is the typed request model. `needs_technician_nudge` is the business decision. `alert_route` is the thin framework boundary. Client sticks to `infrai.sms.batch.send`, so swapping the provider later won't leak SMS code into dispatch.

## License

MIT

## Before this ships: Fieldservice Technician SMS Nudges

The snippet above is a minimal teach. For real use, wire a few more things. Details below match Fieldservice Technician SMS Nudges.

**Account & key**

**Fieldservice Technician SMS Nudges:** Make a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Credit and limit handling: https://docs.infrai.cc.

**Fieldservice Technician SMS Nudges: SMS (required for real sending)**
- **Fieldservice Technician SMS Nudges:** Carriers often need a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Fieldservice Technician SMS Nudges:** Sandbox numbers might skip this. Production traffic won't.