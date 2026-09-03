from django import forms
from django.contrib import admin
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
# admin is mounted at "/" (see Bookly/urls.py) alongside other routes
# (/healthz/, /auth/...) - admin's default catch-all view would otherwise
# intercept those before they reach their real views.
admin.site.final_catch_all_view = False


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


class AppointmentServiceInline(admin.StackedInline):
    model = AppointmentService
    extra = 1
    fields = ["service"]
    # skips the boxed heading/table chrome of the built-in stacked/tabular
    # templates - just repeats the plain "Service" dropdown, styled the
    # same as Client/Staff, with a plain "+ Add another Service" link.
    template = "admin/edit_inline/service_plain.html"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "staff", "start_time", "end_time", "status")
    list_filter = ("status", "staff")
    search_fields = ("client__first_name", "client__last_name")
    # "staff" is hidden from the form for now, not removed - only one person
    # uses this, so picking a staff member on every booking is pointless
    # friction. save_model() auto-assigns the sole Staff record instead.
    exclude = ["reminder_sent_at", "staff"]
    inlines = [AppointmentServiceInline]
    formfield_overrides = {
        models.DateTimeField: {
            "form_class": forms.DateTimeField,
            "widget": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        },
    }

    def save_model(self, request, obj, form, change):
        if not obj.staff_id:
            obj.staff = Staff.objects.first()
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        # "order" and "price_at_booking" aren't shown on the inline form -
        # assign order from row position, price auto-fills on save().
        if formset.model is not AppointmentService:
            return super().save_formset(request, form, formset, change)
        instances = formset.save(commit=False)
        for index, instance in enumerate(instances):
            instance.appointment = form.instance
            instance.order = index
            instance.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

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
        # runs after the inline services are saved, so the confirmation can
        # include them (a post_save signal on Appointment would fire too
        # early, before the inline formset has been processed)
        send_confirmation(obj)
        return super().response_add(request, obj, post_url_continue)

    def response_post_save_add(self, request, obj):
        # land on the dashboard (instead of Django's default changelist) so
        # the new appointment shows up in "Upcoming bookings" right away.
        return HttpResponseRedirect(reverse("admin:index"))
