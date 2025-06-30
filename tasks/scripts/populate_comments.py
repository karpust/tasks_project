from tasks.factories import CommentFactory


def run():
    n = 50
    print(f"Создаю {n} комментариев...")
    for _ in range(n):
        CommentFactory()
    print(f"{n} комментариев успешно созданы!")


# python manage.py runscript populate_comments
