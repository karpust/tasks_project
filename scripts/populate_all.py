# scripts/populate_all.py

from django.core.management import call_command


def run():
    print("Создаю группы...")
    call_command("runscript", "populate_groups")

    print("Создаю пользователей...")
    call_command("runscript", "populate_users")

    print("Создаю категории...")
    call_command("runscript", "populate_tasks")

    print("Создаю задачи...")
    call_command("runscript", "populate_comments")

    print("Данные успешно заполнены!")
