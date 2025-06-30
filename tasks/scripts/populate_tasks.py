from tasks.factories import TaskFactory


def run():
    n = 50
    print(f"Создаю {n} задач...")
    for _ in range(n):
        TaskFactory()
    print(f"{n} задач успешно созданы!")


# python manage.py runscript populate_tasks
