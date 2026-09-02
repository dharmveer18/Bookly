from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Appointment
from bookings.notifications import send_reminder

REMINDER_WINDOW = timedelta(hours=24)


class Command(BaseCommand):
    help = "Sends an email and/or WhatsApp reminder for appointments starting within the next 24h."

    def handle(self, *args, **options):
        now = timezone.now()
        due = (
            Appointment.objects.filter(
                start_time__gte=now,
                start_time__lte=now + REMINDER_WINDOW,
                reminder_sent_at__isnull=True,
            )
            .exclude(status="cancelled")
            .select_related("client", "staff__user")
        )

        sent = 0
        for appointment in due:
            send_reminder(appointment)
            appointment.reminder_sent_at = now
            appointment.save(update_fields=["reminder_sent_at"])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} reminder(s)."))
