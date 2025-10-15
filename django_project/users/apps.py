from django.apps import AppConfig

class UsersConfig(AppConfig):
    name = 'django_project.users'

    def ready(self):
        import django_project.users.signals