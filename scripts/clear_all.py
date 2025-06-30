def run():
    from django.contrib.auth.models import User

    from tasks.models import Category, Comment, Task

    print("Удаляю комментарии...")
    Comment.objects.all().delete()

    print("Удаляю задачи...")
    Task.objects.all().delete()

    print("Удаляю категории...")
    Category.objects.all().delete()

    print("Удаляю пользователей...")
    User.objects.all().delete()

    # print("Удаляю пользователей (кроме суперпользователя)...")
    # User.objects.exclude(is_superuser=True).delete()

    # print("Удаляю группы...")
    # Group.objects.all().delete()

    print("Данные успешно удалены.")
