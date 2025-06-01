#apps/authentication/permissions.py:

from rest_framework.permissions import BasePermission

class IsAdministradorOrReadOnly(BasePermission):
    """
    Permiso personalizado que solo permite a administradores modificar.
    Otros usuarios solo pueden leer.
    """
    def has_permission(self, request, view):
        # Permisos de lectura para usuarios autenticados
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user.is_authenticated
        
        # Permisos de escritura solo para administradores
        return (request.user.is_authenticated and 
                request.user.groups.filter(name='Administrador').exists())

class IsAdministrador(BasePermission):
    """
    Solo administradores pueden acceder
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.groups.filter(name='Administrador').exists())

class IsDocenteOrAdministrador(BasePermission):
    """
    Solo docentes y administradores pueden acceder
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.groups.filter(name__in=['Docente', 'Administrador']).exists())

class IsOwnerOrAdministrador(BasePermission):
    """
    Solo el propietario del objeto o administrador pueden acceder
    """
    def has_object_permission(self, request, view, obj):
        # Administradores tienen acceso total
        if request.user.groups.filter(name='Administrador').exists():
            return True
        
        # Verificar si el usuario es propietario del objeto
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
        
        return False