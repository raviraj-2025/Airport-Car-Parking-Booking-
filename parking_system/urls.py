from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import HttpResponse

# Simple health check view
def health_check(request):
    return HttpResponse('OK')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('parking_app.urls')),
    path('health/', health_check, name='health_check'),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]
