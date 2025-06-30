import logging
import random
from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory import Faker, post_generation

from tasks.models import Category, Comment, Tag, Task, TaskPriority, TaskStatus

logger = logging.getLogger("comment_factory")

User = get_user_model()


def get_random_manager():
    return random.choice(User.objects.filter(groups__name="manager"))


def get_random_user():
    return random.choice(User.objects.filter(groups__name="user"))


def get_random_task():
    return random.choice(Task.objects.all())


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Task

    title = Faker("sentence")
    description = Faker("sentence")
    status = factory.LazyFunction(
        lambda: random.choice([status.value for status in TaskStatus])
    )
    deadline = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=random.randint(-3, 3))
    )
    priority = factory.LazyFunction(
        lambda: random.choice([p.value for p in TaskPriority])
    )
    owner = factory.LazyFunction(get_random_manager)
    notified = Faker("boolean")

    @post_generation
    def executor(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.executor.add(user)
        else:
            count = random.randint(1, 3)
            qs = User.objects.filter(groups__name="user")
            if qs.exists():
                users = qs.order_by("?")[:count]
                self.executor.add(*users)  # same set here

    @post_generation
    def category(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            # self.category = extracted
            self.category, _ = Category.objects.get_or_create(name=extracted)
        else:
            if not Category.objects.exists():
                Category.objects.bulk_create(
                    [
                        Category(name="Feature"),
                        Category(name="Improvement"),
                        Category(name="Documentation"),
                        Category(name="Research"),
                        Category(name="Testing"),
                    ]
                )

            category_list = list(Category.objects.all())
            self.category = random.choice(category_list)

        self.save(update_fields=["category"])

    @post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tags in extracted:
                self.tags.add(tags)

        else:
            # создам заранее несколько дефолтных:
            if not Tag.objects.exists():
                Tag.objects.bulk_create(
                    [
                        Tag(name="architecture"),
                        Tag(name="backend"),
                        Tag(name="frontend"),
                        Tag(name="bugs"),
                        Tag(name="database"),
                    ]
                )
            count = random.randint(1, 3)
            tags = Tag.objects.order_by("?")[:count]
            self.tags.add(*tags)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    logger.info("Start to create CommentFactory class")
    text = Faker("sentence")
    created_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=random.randint(-3, 3))
    )
    task = factory.LazyFunction(lambda: get_random_task())  # нужно сразу тк это fk

    @factory.lazy_attribute
    def author(self):
        return self.task.owner  # нужно сразу тк это fk

    logger.info("End to create CommentFactory class")

    @post_generation
    def validate_consistency(self, create, extracted, **kwargs):
        # после создания объекта проверяю что данные согласованы:
        assert (
            self.author == self.task.owner
        ), f"author ({self.author}) должен быть владельцем task ({self.task.owner})"


# @post_generation — специальный хук, вызывается после создания Task.
# User.objects.order_by('?') - сортировка записей в случайном порядке
# [:2] — срез результатов: берутся только первые 2 записи
# нужно отражать бизнес-правила и в фабриках, чтобы тестовые данные были валидными.

# LazyFunction — это способ сказать фабрике:
# Вызови эту функцию каждый раз при создании объекта, и используй
# её результат как значение поля.
# Если написать просто task = get_random_task()
# то get_random_task() вызовется один раз при определении класса,
# и все объекты фабрики будут иметь одинаковое значение.

# @post_generation вызывается после создания объекта, а в случае Comment
# объект не мог быть создан без полей task and author тк оба fk:
# @post_generation  #
# def setup_comment(self, create, extracted, **kwargs):
#     logger.info(f'Call setup_comment function')
#     if not create:
#         return
#
#     task = get_random_task()
#     logger.info(f'Random Task has owner {task.owner}')
#     if not task:
#         task = TaskFactory()
#         logger.info(f'Random Task has owner {task.owner}')
#
#     self.task = task
#     self.author = self.task.owner
#     self.save(update_fields=['task', 'author'])
