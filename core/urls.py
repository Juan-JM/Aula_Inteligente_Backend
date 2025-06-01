# core/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/', include('apps.authentication.urls')),
    path('api/students/', include('apps.students.urls')),
    path('api/teachers/', include('apps.teachers.urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/subjects/', include('apps.subjects.urls')),
    path('api/grades/', include('apps.grades.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/participation/', include('apps.participation.urls')),
    path('api/tutors/', include('apps.tutors.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]