from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Appointment, Client, Service, Staff


class AppointmentAdminTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password123"
        )
        self.client.login(username="admin", password="password123")
        # required fixture data (Appointment.staff is a required FK, now
        # auto-assigned behind the scenes) - not testing staff behavior itself
        Staff.objects.create(user=self.user)
        self.client_obj = Client.objects.create(
            first_name="Meena",
            last_name="Gill",
            phone="0400111222",
            email="meena@example.com",
        )
        self.haircut = Service.objects.create(
            name="Haircut", duration_minutes=30, price=Decimal("25.00")
        )
        self.facial = Service.objects.create(
            name="Facial", duration_minutes=45, price=Decimal("60.00")
        )

    def _appointment_data(self, **overrides):
        start = timezone.now() + timedelta(days=1)
        data = {
            "client": self.client_obj.pk,
            "start_time": start.strftime("%Y-%m-%dT%H:%M"),
            "status": "confirmed",
            "notes": "",
            "services-TOTAL_FORMS": "1",
            "services-INITIAL_FORMS": "0",
            "services-MIN_NUM_FORMS": "0",
            "services-MAX_NUM_FORMS": "1000",
            "services-0-service": self.haircut.pk,
        }
        data.update(overrides)
        return data

    def test_add_appointment_with_one_service_autofills_price(self):
        resp = self.client.post(reverse("admin:bookings_appointment_add"), self._appointment_data())
        self.assertEqual(resp.status_code, 302)
        appointment = Appointment.objects.get()
        lines = list(appointment.services.all())
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].service, self.haircut)
        self.assertEqual(lines[0].price_at_booking, self.haircut.price)

    def test_add_appointment_with_multiple_services_sets_order_and_price(self):
        data = self._appointment_data(
            **{
                "services-TOTAL_FORMS": "2",
                "services-0-service": self.haircut.pk,
                "services-1-service": self.facial.pk,
            }
        )
        resp = self.client.post(reverse("admin:bookings_appointment_add"), data)
        self.assertEqual(resp.status_code, 302)
        appointment = Appointment.objects.get()
        lines = list(appointment.services.order_by("order"))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].service, self.haircut)
        self.assertEqual(lines[0].order, 0)
        self.assertEqual(lines[1].service, self.facial)
        self.assertEqual(lines[1].order, 1)
        self.assertEqual(lines[1].price_at_booking, self.facial.price)

    def test_editing_appointment_service_refreshes_price(self):
        self.client.post(reverse("admin:bookings_appointment_add"), self._appointment_data())
        appointment = Appointment.objects.get()
        line = appointment.services.get()

        edit_data = self._appointment_data(
            **{
                "services-INITIAL_FORMS": "1",
                "services-0-id": line.pk,
                "services-0-service": self.facial.pk,
            }
        )
        resp = self.client.post(
            reverse("admin:bookings_appointment_edit", args=[appointment.pk]), edit_data
        )
        self.assertEqual(resp.status_code, 302)
        line.refresh_from_db()
        self.assertEqual(line.service, self.facial)
        self.assertEqual(line.price_at_booking, self.facial.price)

    def test_add_appointment_redirects_to_dashboard(self):
        resp = self.client.post(reverse("admin:bookings_appointment_add"), self._appointment_data())
        self.assertRedirects(resp, reverse("admin:index"))

    def test_add_appointment_sends_confirmation_with_services(self):
        self.client.post(reverse("admin:bookings_appointment_add"), self._appointment_data())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Haircut", mail.outbox[0].body)

    def test_edit_url_loads_for_existing_appointment(self):
        self.client.post(reverse("admin:bookings_appointment_add"), self._appointment_data())
        appointment = Appointment.objects.get()
        resp = self.client.get(reverse("admin:bookings_appointment_edit", args=[appointment.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_reminder_sent_at_not_on_form(self):
        resp = self.client.get(reverse("admin:bookings_appointment_add"))
        self.assertNotContains(resp, "Reminder sent at")

    def test_client_details_shows_upcoming_and_completed(self):
        self.client.post(reverse("admin:bookings_appointment_add"), self._appointment_data())
        appointment = Appointment.objects.get()
        appointment.status = "completed"
        appointment.start_time = timezone.now() - timedelta(days=1)
        appointment.save()

        resp = self.client.get(reverse("admin:bookings_client_change", args=[self.client_obj.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Completed appointments")
