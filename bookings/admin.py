from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.auth.models import Group
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
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
            "completed_appointments": client.appointments.filter(status="completed").order_by(
                "-start_time"
            ),
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


class AppointmentAdminForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(active=True),
        required=False,
        help_text="Price and duration are taken from the selected service.",
    )

    class Meta:
        model = Appointment
        fields = ["client", "staff", "service", "start_time", "status", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            line = self.instance.services.first()
            if line:
                self.fields["service"].initial = line.service_id
        # "service" is a plain form field, not a real model FK on Appointment,
        # so it doesn't automatically get the change/add/view icons Client
        # and Staff have - wrap it the same way Django wraps a real FK.
        rel = AppointmentService._meta.get_field("service").remote_field
        self.fields["service"].widget = RelatedFieldWidgetWrapper(
            self.fields["service"].widget,
            rel,
            admin.site,
            can_add_related=True,
            can_change_related=True,
            can_view_related=True,
        )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "staff", "start_time", "end_time", "status")
    list_filter = ("status", "staff")
    search_fields = ("client__first_name", "client__last_name")
    form = AppointmentAdminForm
    formfield_overrides = {
        models.DateTimeField: {
            "form_class": forms.DateTimeField,
            "widget": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        },
    }

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        service = form.cleaned_data.get("service")
        line = obj.services.first()
        if service:
            if line is None:
                AppointmentService.objects.create(appointment=obj, service=service, order=0)
            elif line.service_id != service.id:
                line.service = service
                line.price_at_booking = None
                line.save()
        elif line is not None:
            line.delete()

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
        # runs after save_model() has attached the service, so the
        # confirmation can include it (a post_save signal on Appointment
        # would fire too early, before that happens)
        send_confirmation(obj)
        return super().response_add(request, obj, post_url_continue)

    def response_post_save_add(self, request, obj):
        # land on the dashboard (instead of Django's default changelist) so
        # the new appointment shows up in "Upcoming bookings" right away.
        return HttpResponseRedirect(reverse("admin:index"))
