"""Notifications URLs, at the site root (the service worker must be)."""

from django.urls import path

from notifications import views

app_name = "notifications"

urlpatterns = [
    path("notifications/", views.page, name="page"),
    path("notifications/subscribe/", views.subscribe, name="subscribe"),
    path("notifications/forget/", views.forget, name="forget"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
]
