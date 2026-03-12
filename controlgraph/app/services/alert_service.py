
import hmac
import hashlib
import json
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from app.models import Webhook, WebhookDelivery


def trigger_webhooks(db: Session, tenant_id: str, event_type: str, payload: dict):
    hooks = db.query(Webhook).filter(
        Webhook.tenant_id == tenant_id,
        Webhook.is_active.is_(True)
    ).all()

    for hook in hooks:
        if event_type not in (hook.event_types or []):
            continue
        body = {
            "event_type": event_type,
            "occurred_at": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "data": payload,
        }
        signature = hmac.new(hook.secret_hash.encode(), json.dumps(body).encode(), hashlib.sha256).hexdigest()
        success = False
        status_code = None
        response_text = None
        try:
            response = requests.post(
                hook.target_url,
                json=body,
                timeout=5,
                headers={"X-ControlGraph-Signature": signature},
            )
            status_code = response.status_code
            response_text = response.text[:500]
            success = 200 <= response.status_code < 300
        except Exception as exc:
            response_text = str(exc)

        delivery = WebhookDelivery(
            tenant_id=tenant_id,
            webhook_id=hook.id,
            event_type=event_type,
            payload=body,
            status_code=status_code,
            success=success,
            response_text=response_text,
        )
        db.add(delivery)
    db.commit()
