#authentication/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

# Crear el router
router = DefaultRouter()
router.register(r'groups', views.GroupViewSet)
router.register(r'permissions', views.PermissionViewSet)
router.register(r'users-admin', views.UserManagementViewSet, basename='user-management')
router.register(r'profile', views.ProfileManagementViewSet, basename='profile-management')
router.register(r'users', views.UserGroupViewSet)

urlpatterns = [
    # Endpoints básicos de autenticación
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Endpoints de gestión (incluye ViewSets)
    path('', include(router.urls)),
]