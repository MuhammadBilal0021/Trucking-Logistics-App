from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'Trucking Logistics API',
        'endpoints': {
            'calculate_trip': '/api/calculate-trip/',
        }
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
