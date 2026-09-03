# Email & WhatsApp setup

Both are optional. With nothing configured, confirmations and reminders
still "send" - they just print to the console/logs instead of actually
going out. Configure real credentials in `.env` (local) or your host's
environment variable panel (production, e.g. Render) to make them real.

## Email

1. Use any SMTP provider - e.g. Gmail (free, with an
   [app password](https://myaccount.google.com/apppasswords)), or a
   free-tier transactional service like Brevo or Mailgun.
2. Set these env vars:
   - `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST`
   - `EMAIL_PORT`
   - `EMAIL_HOST_USER`
   - `EMAIL_HOST_PASSWORD`
   - `EMAIL_USE_TLS`
   - `DEFAULT_FROM_EMAIL`
3. Restart the server (local) or redeploy (production).

## WhatsApp (Meta Business Cloud API)

1. Create a Meta Business account and a WhatsApp Business app at
   [developers.facebook.com/apps](https://developers.facebook.com/apps).
2. Register a WhatsApp phone number for it and note the **Phone Number
   ID** and a **permanent access token** (a System User token, not a
   24-hour test token).
3. Create and submit two message templates in the "Utility" category
   for Meta's approval, each with 4 body variables in order - client
   name, date, time, staff - named `appointment_confirmation` and
   `appointment_reminder` (or choose your own names and set them via
   the env vars below).
4. Set these env vars:
   - `WHATSAPP_ACCESS_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_TEMPLATE_NAME_CONFIRMATION` (only if you used a different name)
   - `WHATSAPP_TEMPLATE_NAME_REMINDER` (only if you used a different name)
5. Restart the server (local) or redeploy (production).

See `bookings/whatsapp.py` for the implementation and
`bookings/notifications.py` for how confirmation/reminder messages are
built.

## Checking status

`/setup/` in the admin shows whether each is currently configured, without
exposing these steps - that page is written for a non-technical salon
owner. This file is the reference for whoever's actually setting the
credentials up (you).
