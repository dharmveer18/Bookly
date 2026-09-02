"""
WhatsApp Business Cloud API integration.

To actually send messages (rather than printing to the console):

1. Create a Meta Business account and a WhatsApp Business app at
   https://developers.facebook.com/apps
2. Register a WhatsApp phone number for it and note the Phone Number ID
   and a permanent access token (System User token, not a 24h test token).
3. Create and submit two message templates in the "Utility" category, each
   with 4 body variables in this order: client first name, date, time,
   staff name - get them approved by Meta:
   - WHATSAPP_TEMPLATE_NAME_CONFIRMATION (default "appointment_confirmation")
   - WHATSAPP_TEMPLATE_NAME_REMINDER (default "appointment_reminder")
4. Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env.
"""

import requests
from django.conf import settings


def to_e164(phone):
    """Normalize a local number (e.g. "0400 111 222") to E.164 (+61...)."""
    digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if digits.startswith("+"):
        return digits
    if digits.startswith("0"):
        return settings.DEFAULT_COUNTRY_CODE + digits[1:]
    return settings.DEFAULT_COUNTRY_CODE + digits


def send_whatsapp_message(client_first_name, phone, short_date, time_str, staff_name, template_name, label):
    to = to_e164(phone)

    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print(
            f"[WhatsApp not configured - would send {label} to {to}]\n"
            f"Hi {client_first_name}, your appointment is on {short_date} "
            f"at {time_str} with {staff_name}."
        )
        return

    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": client_first_name},
                        {"type": "text", "text": short_date},
                        {"type": "text", "text": time_str},
                        {"type": "text", "text": staff_name},
                    ],
                }
            ],
        },
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
