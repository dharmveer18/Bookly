from django import template
from django.utils import timezone

from bookings.models import Appointment

register = template.Library()


@register.inclusion_tag("admin/upcoming_bookings.html")
def upcoming_bookings():
    appointments = (
        Appointment.objects.filter(start_time__gte=timezone.now())
        .filter(status__in=["confirmed", "pending"])
        .select_related("client", "staff__user")
        .prefetch_related("services__service")
        .order_by("start_time")[:8]
    )
    return {"appointments": appointments}
