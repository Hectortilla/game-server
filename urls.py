from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path

from apps.main.views import robots, health_check, MainViewSet

admin.site.site_header = settings.SITE_ADMIN_TITLE

urlpatterns = [
    path('robots.txt', robots),
    re_path(r'^rabbit/$', health_check, name='health_check'),

    path('hq/', admin.site.urls),
    re_path(r'^$', MainViewSet.as_view({'get': 'retrieve'}), name="main"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
