from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import update_session_auth_hash
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from django.contrib.auth.models import User
from .serializers import (
    LoginSerializer, RegisterSerializer, UserSerializer, TokenSerializer,
    GroupSerializer, PermissionSerializer, UserGroupSerializer,
    UserUpdateSerializer, PasswordChangeSerializer, ProfileUpdateSerializer,
    AdminPasswordResetSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Iniciar sesión y obtener tokens JWT"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_view(request):
    """Registrar nuevo usuario (solo administradores)"""
    # Verificar que el usuario que hace la petición es administrador
    if not request.user.groups.filter(name='Administrador').exists() and not request.user.is_staff:
        return Response(
            {'error': 'Solo administradores pueden crear usuarios'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            UserSerializer(user).data, 
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Cerrar sesión invalidando el refresh token"""
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Sesión cerrada exitosamente'})
    except Exception as e:
        return Response({'error': 'Token inválido'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Obtener perfil del usuario actual"""
    return Response(UserSerializer(request.user).data)

class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver grupos y sus permisos"""
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Obtener usuarios de un grupo específico"""
        group = self.get_object()
        users = group.user_set.all()
        serializer = UserGroupSerializer(users, many=True)
        return Response(serializer.data)

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver todos los permisos"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Permission.objects.all()
        # Filtrar por app si se especifica
        app_label = self.request.query_params.get('app', None)
        if app_label:
            queryset = queryset.filter(content_type__app_label=app_label)
        return queryset


class UserGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver usuarios y sus grupos/permisos (solo lectura)"""
    queryset = User.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """Personalizar queryset para filtrar por nombre de grupo"""
        print(f"🔍 get_queryset llamado con params: {self.request.query_params}")
        queryset = User.objects.all()
        
        # Filtrar por nombre de grupo si se proporciona
        group_name = self.request.query_params.get('groups', None)
        if group_name:
            print(f"🎯 Filtrando por grupo: {group_name}")
            queryset = queryset.filter(groups__name__iexact=group_name)
        
        return queryset.distinct()
    
    @action(detail=False, methods=['get'], url_path='by-group')
    def by_group(self, request):
        """Endpoint específico para obtener usuarios por grupo"""
        print(f"🚀 by_group llamado con params: {request.query_params}")
        
        group_name = request.query_params.get('group', None)
        is_active = request.query_params.get('is_active', 'true').lower() == 'true'
        
        print(f"🎯 Buscando grupo: {group_name}, activos: {is_active}")
        
        if not group_name:
            return Response({'error': 'Parámetro group es requerido'}, status=400)
        
        users = User.objects.filter(
            groups__name__iexact=group_name,
            is_active=is_active
        ).distinct()
        
        print(f"📊 Usuarios encontrados: {users.count()}")
        
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener grupos y permisos del usuario actual"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios por administradores
    - No incluye CREATE (usar /register/)
    - Solo READ, UPDATE, DELETE
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_staff', 'groups']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined', 'last_login']
    ordering = ['-date_joined']
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return AdminPasswordResetSerializer
        return UserGroupSerializer
    
    def get_permissions(self):
        """Solo administradores pueden modificar y eliminar usuarios"""
        if self.action in ['update', 'partial_update', 'destroy', 'change_password', 'toggle_active']:
            permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Deshabilitar CREATE - usar /register/ en su lugar"""
        return Response(
            {'error': 'Use /api/auth/register/ para crear usuarios'}, 
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Cambiar contraseña de un usuario específico (solo administradores)"""
        user = self.get_object()
        serializer = AdminPasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']
            user.set_password(new_password)
            user.save()
            
            return Response({
                'message': f'Contraseña actualizada para {user.username}'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar usuario"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        status_text = "activado" if user.is_active else "desactivado"
        return Response({
            'message': f'Usuario {user.username} {status_text}',
            'is_active': user.is_active
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Estadísticas de usuarios"""
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        staff_users = User.objects.filter(is_staff=True).count()
        
        groups_stats = []
        for group in Group.objects.all():
            groups_stats.append({
                'group': group.name,
                'count': group.user_set.count()
            })
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'staff_users': staff_users,
            'users_by_group': groups_stats
        })

class ProfileManagementViewSet(viewsets.GenericViewSet):
    """ViewSet para que usuarios gestionen su propio perfil"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener perfil detallado del usuario actual"""
        serializer = UserGroupSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Actualizar perfil del usuario actual"""
        partial = request.method == 'PATCH'
        serializer = ProfileUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=partial
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Perfil actualizado exitosamente',
                'user': UserSerializer(request.user).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Cambiar contraseña del usuario actual"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            user.set_password(new_password)
            user.save()
            
            # Mantener la sesión activa después del cambio de contraseña
            update_session_auth_hash(request, user)
            
            return Response({
                'message': 'Contraseña actualizada exitosamente'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_permissions(self, request):
        """Obtener permisos del usuario actual"""
        user = request.user
        groups = [group.name for group in user.groups.all()]
        all_permissions = user.get_all_permissions()
        
        return Response({
            'username': user.username,
            'groups': groups,
            'permissions': list(all_permissions),
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff
        })