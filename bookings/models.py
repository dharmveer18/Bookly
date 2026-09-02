from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils.dateformat import format as date_format


class Client(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Service(models.Model):
    name = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    services = models.ManyToManyField(Service, related_name="staff", blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StaffAvailability(models.Model):
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="availability")
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.staff} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class TimeOff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="time_off")
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.staff} off on {self.date}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No-show"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="appointments")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="appointments")
    start_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    @property
    def end_time(self):
        total_minutes = sum(s.service.duration_minutes for s in self.services.all())
        return self.start_time + timedelta(minutes=total_minutes)

    def __str__(self):
        when = date_format(self.start_time, "M j, Y, g:i A")
        return f"{self.client} with {self.staff} at {when}"


class AppointmentService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="services")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    order = models.PositiveIntegerField(default=0)
    price_at_booking = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if self.price_at_booking is None:
            self.price_at_booking = self.service.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service} for {self.appointment}"
