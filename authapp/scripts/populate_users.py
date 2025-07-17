import logging
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from authapp.factories import UserFactory

logger = logging.getLogger("data_fixtures")

User = get_user_model()


def create_admin():
    # если суперпользователь создается вручную (через createsuperuser или sherll+орм),
    # обязательно нужно добавить его в группу "admin",
    # иначе у него не будет необходимых прав доступа.

    username = os.environ.get("DJANGO_ADMIN_USERNAME")
    email = os.environ.get("DJANGO_ADMIN_EMAIL")
    password = os.environ.get("DJANGO_ADMIN_PASSWORD")

    if not all([username, email, password]):
        logger.warning(
            "Environment variables for administrator are not set. "
            "Create an administrator manually"
        )
        return

    if not User.objects.filter(username=username).exists():
        admin = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        admin_group, _ = Group.objects.get_or_create(name="admin")
        admin.groups.add(admin_group)

        logger.info(f"Администратор '{username}' создан и добавлен в группу 'admin'")
    else:
        logger.info(f"Администратор '{username}' уже существует")


def run(n=50):

    create_admin()

    logger.info("Creation of users...")
    count = 0
    for i in range(n):
        try:
            if i % 5 == 0:
                user = UserFactory(groups="manager")
            else:
                user = UserFactory()
            if not user or not user.pk:
                raise ValueError("Failed to create user")
            count += 1
        except Exception:
            logger.exception("Failed to create user")

    logger.info(f"{count} users from {n} created successfully")


# python manage.py runscript populate_users
