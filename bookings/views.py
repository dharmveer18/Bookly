from django.conf import settings
from django.contrib import admin
from django.shortcuts import render


def setup_view(request):
    context = {
        **admin.site.each_context(request),
        "title": "Setup",
        "email_configured": bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD),
        "whatsapp_configured": bool(
            settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID
        ),
    }
    return render(request, "admin/setup.html", context)
