from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.db import models
from django.shortcuts import get_object_or_404, render
from django.urls import path
from django.utils import timezone
from social_django.models import Association, Nonce, UserSocialAuth

from .models import (
    Appointment,
    AppointmentService,
    Client,
    Service,
    Staff,
    StaffAvailability,
    TimeOff,
)
from .notifications import send_confirmation

admin.site.unregister(UserSocialAuth)
admin.site.unregister(Nonce)
admin.site.unregister(Association)
admin.site.unregister(Group)

admin.site.site_header = "Bookly"
admin.site.site_title = "Bookly Admin"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "email", "created_at")
    search_fields = ("first_name", "last_name", "phone", "email")

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/edit/",
                self.admin_site.admin_view(self.edit_view),
                name="bookings_client_edit",
            ),
        ]
        return custom_urls + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        client = get_object_or_404(Client, pk=object_id)
        now = timezone.now()
        context = {
            **self.admin_site.each_context(request),
            "title": str(client),
            "client": client,
            "opts": self.model._meta,
            "upcoming_appointments": client.appointments.filter(start_time__gte=now)
            .exclude(status="cancelled")
            .order_by("start_time"),
            "completed_appointments": client.appointments.filter(status="completed").order_by("-start_time"),
        }
        return render(request, "admin/client_details.html", context)

    def edit_view(self, request, object_id):
        return super().change_view(request, object_id)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price", "active")
    list_filter = ("active",)


class StaffAvailabilityInline(admin.TabularInline):
    model = StaffAvailability
    extra = 1


class TimeOffInline(admin.TabularInline):
    model = TimeOff
    extra = 1


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ("services",)
    inlines = [StaffAvailabilityInline, TimeOffInline]


class AppointmentServiceInline(admin.TabularInline):
    model = AppointmentService
    extra = 1


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "staff", "start_time", "end_time", "status")
    list_filter = ("status", "staff")
    search_fields = ("client__first_name", "client__last_name")
    inlines = [AppointmentServiceInline]
    formfield_overrides = {
        models.DateTimeField: {
            "form_class": forms.DateTimeField,
            "widget": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        },
    }

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/edit/",
                self.admin_site.admin_view(self.edit_view),
                name="bookings_appointment_edit",
            ),
        ]
        return custom_urls + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        appointment = get_object_or_404(Appointment, pk=object_id)
        now = timezone.now()
        context = {
            **self.admin_site.each_context(request),
            "title": str(appointment.client),
            "appointment": appointment,
            "opts": self.model._meta,
            "upcoming_appointments": appointment.client.appointments.filter(start_time__gte=now)
            .exclude(status="cancelled")
            .exclude(pk=appointment.pk)
            .order_by("start_time"),
            "completed_appointments": appointment.client.appointments.filter(status="completed")
            .exclude(pk=appointment.pk)
            .order_by("-start_time"),
        }
        return render(request, "admin/appointment_details.html", context)

    def edit_view(self, request, object_id):
        return super().change_view(request, object_id)

    def response_add(self, request, obj, post_url_continue=None):
        # runs after inline services are saved, so the confirmation can
        # include them (a post_save signal on Appointment would fire too
        # early, before the inline formset has been processed)
        send_confirmation(obj)
        return super().response_add(request, obj, post_url_continue)
