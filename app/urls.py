from django.contrib import admin
from django.urls import path

from home.views import home_view, upload_view, revert_view

from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin', admin.site.urls),
    path('', home_view, name='home'),
    path('upload', upload_view, name='upload'),
    path('revert', revert_view, name='revert'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)