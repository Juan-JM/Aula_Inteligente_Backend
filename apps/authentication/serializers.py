from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.contenttypes.models import ContentType

class UserSerializer(serializers.ModelSerializer):
    groups = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'groups', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Credenciales inválidas')
            if not user.is_active:
                raise serializers.ValidationError('Usuario inactivo')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Debe proporcionar username y password')

# SERIALIZER CORREGIDO PARA REGISTRO
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    groups = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="Lista de IDs de grupos a asignar"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 
                 'password_confirm', 'groups', 'is_staff', 'is_active', 'is_superuser']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        
        # Validar que los grupos existen
        groups_ids = attrs.get('groups', [])
        if groups_ids:
            existing_groups = Group.objects.filter(id__in=groups_ids)
            if len(existing_groups) != len(groups_ids):
                invalid_ids = set(groups_ids) - set(existing_groups.values_list('id', flat=True))
                raise serializers.ValidationError(f"Los grupos con IDs {list(invalid_ids)} no existen")
        
        return attrs
    
    def create(self, validated_data):
        # Remover campos que no van al modelo User
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        groups_ids = validated_data.pop('groups', [])
        
        # Crear usuario
        user = User.objects.create_user(password=password, **validated_data)
        
        # Asignar grupos
        if groups_ids:
            groups = Group.objects.filter(id__in=groups_ids)
            user.groups.set(groups)
        
        return user

class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']

class PermissionSerializer(serializers.ModelSerializer):
    content_type = ContentTypeSerializer(read_only=True)
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']

class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'permission_count']
    
    def get_permission_count(self, obj):
        return obj.permissions.count()

class UserGroupSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    user_permissions = PermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'is_staff', 'is_active', 'groups', 'user_permissions']

# SERIALIZER MEJORADO PARA ACTUALIZACIÓN
class UserUpdateSerializer(serializers.ModelSerializer):
    groups = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="Lista de IDs de grupos a asignar"
    )
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 
                 'is_active', 'is_superuser', 'groups', 'password', 'password_confirm']
    
    def validate(self, attrs):
        # Validar contraseñas si se proporcionan
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError("Las contraseñas no coinciden")
        
        # Validar que los grupos existen
        groups_ids = attrs.get('groups', [])
        if groups_ids:
            existing_groups = Group.objects.filter(id__in=groups_ids)
            if len(existing_groups) != len(groups_ids):
                invalid_ids = set(groups_ids) - set(existing_groups.values_list('id', flat=True))
                raise serializers.ValidationError(f"Los grupos con IDs {list(invalid_ids)} no existen")
        
        return attrs
    
    def update(self, instance, validated_data):
        groups_ids = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)
        
        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar contraseña si se proporciona
        if password:
            instance.set_password(password)
        
        instance.save()
        
        # Actualizar grupos si se proporcionaron
        if groups_ids is not None:
            groups = Group.objects.filter(id__in=groups_ids)
            instance.groups.set(groups)
        
        return instance

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Las nuevas contraseñas no coinciden")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta")
        return value

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
    
    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está en uso")
        return value

class AdminPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs