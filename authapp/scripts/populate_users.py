from django.contrib.auth import get_user_model

from authapp.factories import UserFactory

User = get_user_model()

n = 50


def run():
    # admin = User.objects.create_superuser(
    #     username='admin',
    #     email='admin@example.com',
    #     password='admin12345',
    # )
    # admin_group = Group.objects.get(name='admin')
    # admin.groups.add(admin_group)

    for i in range(n):
        if i % 5 == 0:
            UserFactory(groups="manager")
        else:
            UserFactory()
    print(f"{n} пользователей успешно созданы в базе")


# python manage.py runscript populate_users
