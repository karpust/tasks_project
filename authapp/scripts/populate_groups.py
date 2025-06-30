from django.contrib.auth.models import Group


def run():
    roles = ["admin", "manager", "user"]
    for role in roles:
        group, created = Group.objects.get_or_create(name=role)
        print(f'Группа "{role}" {"создана" if created else "уже существует"}')


# python manage.py runscript populate_groups
