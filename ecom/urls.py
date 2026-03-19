
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings



urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
    path('customer/', include('customer.urls')),
    path("account/", include("accounts.urls")),
    path("aadmin/", include("aadmin.urls")),
    path("payment/", include("payment.urls")),
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)