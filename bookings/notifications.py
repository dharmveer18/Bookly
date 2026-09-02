from django.conf import settings
from django.core.mail import send_mail
from django.utils.dateformat import format as date_format

from .whatsapp import send_whatsapp_message


def _context(appointment):
    services = ", ".join(line.service.name for line in appointment.services.all())
    return {
        "short_date": date_format(appointment.start_time, "M j"),
        "full_date": date_format(appointment.start_time, "l, F j, Y"),
        "time_str": date_format(appointment.start_time, "g:i A"),
        "staff_name": str(appointment.staff),
        "services": services or "n/a",
    }


def _send(appointment, subject_prefix, intro, whatsapp_template, whatsapp_label):
    ctx = _context(appointment)
    client = appointment.client

    if client.email:
        subject = f"{subject_prefix}: {ctx['short_date']} at {ctx['time_str']}"
        message = (
            f"Hi {client.first_name},\n\n"
            f"{intro}\n\n"
            f"Date: {ctx['full_date']}\n"
            f"Time: {ctx['time_str']}\n"
            f"With: {ctx['staff_name']}\n"
            f"Services: {ctx['services']}\n\n"
            f"See you then!\nBookly"
        )
        send_mail(subject, message, None, [client.email])

    send_whatsapp_message(
        client.first_name,
        client.phone,
        ctx["short_date"],
        ctx["time_str"],
        ctx["staff_name"],
        whatsapp_template,
        whatsapp_label,
    )


def send_confirmation(appointment):
    _send(
        appointment,
        subject_prefix="Booking confirmed",
        intro="Your appointment is confirmed:",
        whatsapp_template=settings.WHATSAPP_TEMPLATE_NAME_CONFIRMATION,
        whatsapp_label="confirmation",
    )


def send_reminder(appointment):
    _send(
        appointment,
        subject_prefix="Reminder",
        intro="This is a reminder for your upcoming appointment:",
        whatsapp_template=settings.WHATSAPP_TEMPLATE_NAME_REMINDER,
        whatsapp_label="reminder",
    )
