# apps/authentication/models.py:

from django.db import models
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class RoleManager:
    """Manager para crear roles y permisos del sistema"""
    
    @staticmethod
    def create_default_groups():
        """Crea los grupos por defecto del sistema"""
        
        # Crear grupos
        admin_group, created = Group.objects.get_or_create(name='Administrador')
        teacher_group, created = Group.objects.get_or_create(name='Docente')
        student_group, created = Group.objects.get_or_create(name='Estudiante')
        
        # Permisos para Administrador (todos)
        if created or admin_group.permissions.count() == 0:
            admin_permissions = Permission.objects.all()
            admin_group.permissions.set(admin_permissions)
        
        return admin_group, teacher_group, student_group

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    """Crear grupos automáticamente después de las migraciones"""
    if sender.name == 'apps.authentication':
        RoleManager.create_default_groups()