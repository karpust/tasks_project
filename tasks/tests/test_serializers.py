from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now
from rest_framework.test import APIRequestFactory

from tasks.models import Category, Comment, Tag, Task
from tasks.serializers import (
    CategorySerializer,
    CommentSerializer,
    TagSerializer,
    TaskSerializer,
)

User = get_user_model()


class TaskSerializerTests(TestCase):
    def setUp(self):
        """Предварительно создаю объекты юзера, тэга, категории; использую их для
        создания объекта задачи; но тк как task.owner передается автоматически из зароса
        симулирую запрос, в который передаю юзера."""
        self.some_user = User.objects.create(username="some_user")
        self.executor = User.objects.create(username="executor")
        self.owner = User.objects.create(username="owner")
        self.deadline = now() + timedelta(days=1)
        self.task_valid_data = {
            "title": "New Task",
            "description": "This is a test task",
            "status": "to_do",
            "deadline": self.deadline,
            "priority": "high",
            "executor": [self.executor.pk],
            "category": "Work",
            "tags": ["Urgent", "Home"],
        }
        factory = (
            APIRequestFactory()
        )  # использую фабрику для передачи юзера в контексте запроса
        # self.request = self.factory.post("/tasks/", self.valid_data, format="json")
        self.request = factory.post(
            "/fake-request/"
        )  # APIRequestFactory не использует маршрутизацию
        self.request.user = self.owner

    def test_correct_serialization(self):
        """Проверяю, что сериализатор корректно сериализует объект."""
        # создаю объект модели:
        serializer = TaskSerializer(
            data=self.task_valid_data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        task = serializer.save()
        # проверяю что owner добавился:
        self.assertEqual(task.owner, self.owner)

        expected_data = {
            "id": 1,
            "title": "New Task",
            "description": "This is a test task",
            "status": "to_do",
            "status_display": "to_do",
            "deadline": self.deadline.isoformat().replace("+00:00", "Z"),
            "priority": "high",
            "priority_display": "high",
            "executor": [self.executor.pk],
            "category": "Work",
            "tags": ["Urgent", "Home"],
            # no owner bcz it's hidden field
        }
        serializer = TaskSerializer(instance=task)

        self.assertEqual(serializer.data["id"], expected_data["id"])
        self.assertEqual(serializer.data["title"], expected_data["title"])
        self.assertEqual(serializer.data["description"], expected_data["description"])
        self.assertEqual(serializer.data["status"], expected_data["status"])  # to_do
        self.assertEqual(task.status, 1)
        self.assertEqual(serializer.data["deadline"], expected_data["deadline"])
        self.assertEqual(serializer.data["priority"], expected_data["priority"])
        self.assertEqual(serializer.data["executor"], expected_data["executor"])
        self.assertEqual(serializer.data["category"], expected_data["category"])
        self.assertEqual(serializer.data["tags"], expected_data["tags"])
        self.assertNotIn("owner", serializer.data)

    def test_update_task_with_new_tags_and_category(self):
        # create task:
        serializer = TaskSerializer(
            data=self.task_valid_data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        task = serializer.save()

        # update some data in task:
        updated_data = {
            "tags": ["UpdatedUrgent", "Home"],
            "category": "UpdatedWork",
        }
        serializer = TaskSerializer(instance=task, data=updated_data, partial=True)
        self.assertTrue(serializer.is_valid())
        task = serializer.save()

        # check data:
        self.assertEqual(task.category.name, "UpdatedWork")
        self.assertEqual(
            set(tag.name for tag in task.tags.all()), {"Updatedurgent", "Home"}
        )
        self.assertEqual(task.title, self.task_valid_data["title"])
        self.assertEqual(task.description, self.task_valid_data["description"])

    def test_to_representation_for_tags_and_category_names(self):
        serializer = TaskSerializer(
            data=self.task_valid_data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()

        self.assertEqual(serializer.data["tags"], ["Urgent", "Home"])
        self.assertEqual(serializer.data["category"], "Work")

    def test_deserialization_valid_data(self):
        """Проверяю корректность десериализации валидных данных."""
        serializer = TaskSerializer(
            data=self.task_valid_data, context={"request": self.request}
        )

        self.assertTrue(serializer.is_valid())

        self.assertEqual(
            serializer.validated_data["title"], self.task_valid_data["title"]
        )
        self.assertEqual(
            serializer.validated_data["description"],
            self.task_valid_data["description"],
        )
        self.assertEqual(serializer.initial_data["status"], "to_do")
        self.assertEqual(
            serializer.validated_data["status"], 1
        )  # self.task_valid_data["status"]
        self.assertEqual(
            serializer.validated_data["deadline"],
            self.task_valid_data["deadline"],
        )
        self.assertEqual(serializer.validated_data["priority"], 3)
        self.assertEqual(serializer.validated_data["executor"], [self.executor])
        self.assertEqual(serializer.validated_data["category"], "Work")
        self.assertEqual(serializer.validated_data["tags"], ["Urgent", "Home"])

    def test_get_owner_from_request(self):
        """Проверяю, что owner добавляется из запроса."""
        serializer = TaskSerializer(
            data=self.task_valid_data, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        self.assertNotEqual(task.owner, None)
        self.assertNotEqual(task.owner, self.some_user)
        self.assertEqual(task.owner, self.owner)

    def test_deserialization_invalid_data(self):
        """Проверяю, что сериализатор не валидирует некорректные данные."""

        invalid_data = {
            "title": "N",
            "description": "This is a test task",
            "status": 4,
            "deadline": 1,
            "priority": 4,
            "executor": [self.executor],
            "category": "",
            "tags": [""],
        }

        serializer = TaskSerializer(
            data=invalid_data, context={"request": self.request}
        )

        serializer.is_valid()
        self.assertIn("status", serializer.errors)
        self.assertIn("deadline", serializer.errors)
        self.assertIn("priority", serializer.errors)
        self.assertIn("executor", serializer.errors)
        self.assertIn("category", serializer.errors)
        self.assertFalse(serializer.is_valid(), serializer.errors)

    def test_missing_required_field(self):
        invalid_data = {}

        serializer = TaskSerializer(
            data=invalid_data, context={"request": self.request}
        )
        serializer.is_valid()

        # required fields:
        self.assertIn("title", serializer.errors)
        self.assertIn("executor", serializer.errors)
        # not required fields:
        self.assertNotIn("category", serializer.errors)
        self.assertNotIn("tags", serializer.errors)


class CommentSerializerTest(TestCase):
    def setUp(self):
        # create fake user:
        self.user = User.objects.create(username="commenter")
        # create task object:
        task_data = {
            "title": "New Task",
            "deadline": "2024-04-06T10:00:00Z",
            # "executor": [self.user.pk],  # m2m в бд может быть пустым,
            # но если сериализовать-будет ошибка
            "owner": self.user,  # для бд, не для сериализации
        }

        self.factory = APIRequestFactory()
        self.request = self.factory.get("/fake-request/")
        self.request.user = self.user
        self.task = Task.objects.create(**task_data)
        self.comment_valid_data = {"text": "New Comment"}

    def test_correct_serialization(self):
        """Проверяю корректность сериализации объекта."""
        comment = Comment.objects.create(
            task=self.task, text="New Comment", author=self.user
        )
        expected_data = {
            "id": 1,
            "task": self.task.pk,
            "text": "New Comment",
        }

        serializer = CommentSerializer(instance=comment)

        self.assertEqual(serializer.data["id"], expected_data["id"])
        self.assertEqual(serializer.data["task"], expected_data["task"])
        self.assertEqual(serializer.data["text"], expected_data["text"])
        self.assertIn("created_at", serializer.data)
        self.assertIsInstance(serializer.data["created_at"], str)
        self.assertNotIn("author", serializer.data)  # HiddenField

    def test_deserialization_valid_data(self):
        """Проверяю корректность десериализации валидных данных."""
        serializer = CommentSerializer(
            data={"text": "New Comment", "task": self.task},
            context={"request": self.request},
        )
        # проверяю начальные данные:
        self.assertIn("task", serializer.initial_data)  # !
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("task", serializer.validated_data)  # ! => read-only field
        # проверяю что сериализатор добавил автора(HiddenField):
        self.assertIn("author", serializer.validated_data)
        # но задача добавляется вьюшкой:
        self.assertNotIn("task", serializer.validated_data)
        # task is read-only field
        # created_at после сохраниения объекта в бд:
        self.assertNotIn(
            "created_at", serializer.validated_data
        )  # объект еще не сохранен

        serializer.save(task=self.task)  # имитирую добавление задачи вьюшкой

        self.assertNotIn("author", serializer.data)  # вывод данных
        self.assertEqual(serializer.data["id"], 1)
        self.assertEqual(serializer.data["task"], self.task.id)
        self.assertEqual(serializer.data["text"], "New Comment")
        self.assertIsInstance(serializer.data["created_at"], str)

    def test_get_author_from_request(self):
        """Проверяю, что author добавляется из запроса."""
        serializer = CommentSerializer(
            data=self.comment_valid_data, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        self.assertIn("author", serializer.validated_data)
        comment = serializer.save(task=self.task)
        self.assertNotIn("author", serializer.data)

        self.assertNotEqual(comment.author, None)
        self.assertEqual(comment.author, self.user)

    def test_deserialization_invalid_data(self):
        serializer = CommentSerializer(
            data={"text": ""}, context={"request": self.request}
        )
        serializer.is_valid()
        self.assertIn("text", serializer.errors)

    def test_missing_required_field(self):
        serializer = CommentSerializer(data={}, context={"request": self.request})
        serializer.is_valid()

        self.assertIn("text", serializer.errors)
        self.assertFalse(serializer.is_valid())


class CategorySerializerTest(TestCase):
    def setUp(self):
        self.category_data = {"name": "Test Category"}

    def test_correct_serialization(self):
        """Проверяю корректность сериализацию объекта."""
        category = Category.objects.create(**self.category_data)
        expected_data = {"id": category.pk, "name": category.name}

        serializer = CategorySerializer(instance=category)

        self.assertEqual(serializer.data, expected_data)

    def test_deserialization_valid_data(self):
        """Проверяю корректность десериализации валидных данных."""
        serializer = CategorySerializer(data=self.category_data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["name"], self.category_data["name"])

    def test_deserialization_invalid_data(self):
        """Проверяю корректность десериализации невалидных данных."""
        invalid_data = {"name": ""}  # can not be empty

        serializer = CategorySerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_missing_required_field(self):
        serializer = CategorySerializer(data={})
        serializer.is_valid()

        self.assertIn("name", serializer.errors)
        self.assertFalse(serializer.is_valid())


class TagSerializerTest(TestCase):
    def setUp(self):
        self.tag_data = {"name": "Test Tag"}

    def test_correct_serialization(self):
        """Проверяю корректность сериализации объекта."""
        tag = Tag.objects.create(**self.tag_data)
        expected_data = {"id": tag.pk, "name": tag.name}

        serializer = TagSerializer(instance=tag)

        self.assertEqual(serializer.data, expected_data)

    def test_deserialization_valid_data(self):
        """Проверяю корректность десериализации валидных данных."""
        serializer = TagSerializer(data=self.tag_data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["name"], self.tag_data["name"])

    def test_deserialization_invalid_data(self):
        """Проверяю корректность десериализации невалидных данных."""
        invalid_data = {"name": ""}  # name should not be empty

        serializer = TagSerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_missing_required_field(self):
        serializer = TagSerializer(data={})
        serializer.is_valid()

        self.assertIn("name", serializer.errors)
        self.assertFalse(serializer.is_valid())
