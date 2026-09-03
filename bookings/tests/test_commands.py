from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from bookings.models import Appointment, Client, Staff


class SendAppointmentRemindersTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="staffuser", password="x")
        self.staff = Staff.objects.create(user=user)
        self.client_obj = Client.objects.create(
            first_name="Meena",
            last_name="Gill",
            phone="0400111222",
            email="meena@example.com",
        )

    def _make_appointment(self, **overrides):
        defaults = {
            "client": self.client_obj,
            "staff": self.staff,
            "start_time": timezone.now() + timedelta(hours=5),
            "status": "confirmed",
        }
        defaults.update(overrides)
        return Appointment.objects.create(**defaults)

    def test_sends_reminder_within_window(self):
        appointment = self._make_appointment()
        call_command("send_appointment_reminders")
        appointment.refresh_from_db()
        self.assertIsNotNone(appointment.reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_skips_already_reminded(self):
        self._make_appointment(reminder_sent_at=timezone.now())
        call_command("send_appointment_reminders")
        self.assertEqual(len(mail.outbox), 0)

    def test_skips_cancelled(self):
        self._make_appointment(status="cancelled")
        call_command("send_appointment_reminders")
        self.assertEqual(len(mail.outbox), 0)

    def test_skips_outside_window(self):
        self._make_appointment(start_time=timezone.now() + timedelta(days=5))
        call_command("send_appointment_reminders")
        self.assertEqual(len(mail.outbox), 0)

    def test_skips_past_appointments(self):
        self._make_appointment(start_time=timezone.now() - timedelta(hours=1))
        call_command("send_appointment_reminders")
        self.assertEqual(len(mail.outbox), 0)

    def test_running_twice_does_not_double_send(self):
        self._make_appointment()
        call_command("send_appointment_reminders")
        call_command("send_appointment_reminders")
        self.assertEqual(len(mail.outbox), 1)


class EnsureSuperuserTests(TestCase):
    def test_creates_when_none_exists_and_env_vars_set(self):
        with mock.patch.dict(
            "os.environ",
            {
                "DJANGO_SUPERUSER_USERNAME": "admin",
                "DJANGO_SUPERUSER_PASSWORD": "supersecret123",
                "DJANGO_SUPERUSER_EMAIL": "admin@example.com",
            },
        ):
            call_command("ensure_superuser")
        self.assertTrue(User.objects.filter(username="admin", is_superuser=True).exists())

    def test_skips_when_superuser_already_exists(self):
        User.objects.create_superuser(username="existing", email="e@example.com", password="x")
        with mock.patch.dict(
            "os.environ",
            {
                "DJANGO_SUPERUSER_USERNAME": "admin",
                "DJANGO_SUPERUSER_PASSWORD": "supersecret123",
            },
        ):
            call_command("ensure_superuser")
        self.assertFalse(User.objects.filter(username="admin").exists())
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_skips_when_env_vars_missing(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            call_command("ensure_superuser")
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
