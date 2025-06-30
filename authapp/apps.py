from django.apps import AppConfig

# def get_user_role(self):
#     profile = getattr(self, 'profile', None)  # check if user have profile
#     if profile and hasattr(profile, 'role'):  # check if profile have role
#         return profile.role


class AuthappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authapp"

    def ready(self):
        # from django.contrib.auth.models import User
        # from django.contrib.auth.models import AnonymousUser
        # User.add_to_class("role", property(get_user_role))
        # AnonymousUser.role = property(get_user_role)
        pass
