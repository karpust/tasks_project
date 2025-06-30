from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

User = get_user_model()


class Category(models.Model):
    name = models.CharField(
        max_length=255, unique=True, verbose_name="Название категории"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название тэга")

    class Meta:
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"

    def __str__(self):
        return self.name


class TaskStatus(models.IntegerChoices):
    TO_DO = 1, "to_do"
    IN_PROGRESS = 2, "in_progress"
    DONE = 3, "done"


class TaskPriority(models.IntegerChoices):
    LOW = 1, "low"
    MEDIUM = 2, "medium"
    HIGH = 3, "high"


def default_deadline():
    return timezone.now() + timedelta(days=1)


class Task(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название задачи")
    description = models.TextField(
        blank=True, null=True, verbose_name="Описание задачи"
    )
    status = models.IntegerField(
        choices=TaskStatus.choices,
        default=TaskStatus.TO_DO,
        verbose_name="Статус выполнения",
    )
    deadline = models.DateTimeField(
        default=default_deadline, verbose_name="Срок выполнения"
    )
    priority = models.IntegerField(
        choices=TaskPriority.choices,
        default=TaskPriority.LOW,
        verbose_name="Приоритет задачи",
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_owner",
        verbose_name="Создатель задачи",
    )
    executor = models.ManyToManyField(
        User, related_name="task_executors", verbose_name="Исполнитель задачи"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    tags = models.ManyToManyField(Tag, blank=True)
    notified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

    def clean(self):
        """Проверяем, чтобы был хотя бы один исполнитель."""
        # отсутствие связей в M2M не блокирует создание объекта модели,
        # это нужно проверять вручную;
        super().clean()
        if not self.executor.exists():
            raise ValidationError(
                {
                    "executor": "This field cannot be null. "
                    "Need to choose at least one executor."
                }
            )

    def __str__(self):
        return self.title


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comment_author",
        verbose_name="Автор комментария",
    )
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"
