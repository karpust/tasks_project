from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from tasks.models import Category, Comment, Tag, Task

User = get_user_model()


class BaseTaskModelTests(TestCase):
    """Родительский класс для наследования от него методов setUpTestData, setUp."""

    @classmethod
    def setUpTestData(cls):
        """Выполняется один раз перед запуском всех тестов, созданные объекты не
        сбрасываются автоматически, использую для ускорения тестов."""

        cls.user = User.objects.create_user(
            username="some_user",
            password="some_user_password123",
        )
        cls.task = Task(
            id=1,
            title="some_task",
            description="some_description",
            status=3,
            deadline=timezone.now(),
            priority=3,
            owner=cls.user,
        )
        cls.task.executor.add(cls.user)  # no need save after

        # проверка валидности:
        try:
            cls.task.full_clean()
            cls.task.save()  # если валидация успешна, сохраняею объект
        except ValidationError as e:
            print(e.message_dict)  # печатаю ошибки если есть

        cls.comment = Comment.objects.create(
            task=cls.task, author=cls.user, text="Test comment"
        )

    def setUp(self):
        """Обновляю объекты перед каждым тестом, на случай изменения тестом."""
        self.task = Task.objects.get(id=self.task.id)
        self.user = User.objects.get(id=self.user.id)
        self.comment = Comment.objects.get(id=self.comment.id)


class TaskModelTests(BaseTaskModelTests):

    def test_task_correct_creation(self):
        self.assertEqual(self.task.title, "some_task")
        self.assertEqual(self.task.description, "some_description")
        self.assertEqual(self.task.status, 3)
        self.assertIsNotNone(self.task.deadline)
        self.assertEqual(self.task.priority, 3)
        self.assertEqual(self.task.owner, self.user)
        self.assertEqual(list(self.task.executor.all()), [self.user])

    def test_required_fields(self):
        """Обязательные поля не могут быть пустыми."""

        # создаю объект с пустыми обязательными полями:
        invalid_task = Task(id=2)

        with self.assertRaises(ValidationError) as context:
            invalid_task.full_clean()
        validation_errors = context.exception.message_dict

        # проверяю, что каждое обязательное поле дает ошибку:
        self.assertIn("title", validation_errors)
        self.assertIn("owner", validation_errors)
        self.assertIn("executor", validation_errors)

        # проверяю конкретные сообщения об ошибке для каждого поля:
        self.assertIn("This field cannot be blank.", validation_errors["title"])
        self.assertIn("This field cannot be null.", validation_errors["owner"])
        self.assertIn(
            "This field cannot be null. Need to choose at least one executor.",
            validation_errors["executor"],
        )

    def test_correct_defalt_values(self):
        """Проверка значений по умолчанию."""
        # create task without data to default fields:
        task = Task.objects.create(
            title="some_task",
            description="some_description",
            deadline=timezone.now(),
            owner=self.user,
        )

        # check default data was set correct:
        self.assertEqual(task.status, 1)
        self.assertEqual(task.priority, 1)

    def test_correct_priority_choices(self):
        """Проверка choices поля priority."""

        valid_priorities = [1, 2, 3]
        invalid_priorities = [0, 4]

        # test valid priorities:
        for val in valid_priorities:
            with self.subTest(valid_priority=val):
                self.task.priority = val
                self.task.full_clean()  # если ошибка, тест провалится

        # test invalid priorities:
        for val in invalid_priorities:
            with self.subTest(invalid_priority=val):
                self.task.priority = val
                with self.assertRaises(ValidationError) as context:
                    self.task.full_clean()
                self.assertIn("priority", context.exception.message_dict)

                # проверяю, что сообщение об ошибке связано с choices
                # print(context.exception.messages)
                error_message = str(context.exception.message_dict["priority"])
                self.assertIn("valid choice", error_message)

    def test_correct_status_choices(self):
        """Проверка choices поля status."""

        valid_status = [1, 2, 3]
        invalid_status = [0, 4]

        # test valid priorities:
        for val in valid_status:
            with self.subTest(valid_status=val):
                self.task.status = val
                self.task.full_clean()  # если ошибка, тест провалится

        # test invalid priorities:
        for val in invalid_status:
            with self.subTest(invalid_status=val):
                self.task.status = val
                with self.assertRaises(ValidationError) as context:
                    self.task.full_clean()
                self.assertIn("status", context.exception.message_dict)

                # проверяю, что сообщение об ошибке связано с choices
                error_message = str(context.exception.message_dict["status"])
                self.assertIn("valid choice", error_message)

    def test_task_str(self):
        self.assertEqual(str(self.task), "some_task")


class CommentModelTests(BaseTaskModelTests):

    def test_comment_creation(self):
        """Проверяет, что комментарий корректно создается."""
        self.assertEqual(self.comment.text, "Test comment")
        self.assertEqual(self.comment.author, self.user)
        self.assertEqual(self.comment.task, self.task)
        self.assertIsNotNone(self.comment.created_at)

    def test_comment_str(self):
        """Проверяет строковое представление комментария."""
        self.assertEqual(str(self.comment), f"Comment by {self.user} on {self.task}")


class CategoryModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Technology")

    def test_category_creation(self):
        """Test that a category is created correctly."""
        self.assertEqual(self.category.name, "Technology")

    def test_category_str(self):
        """Test the __str__ method of Category."""
        self.assertEqual(str(self.category), "Technology")

    def test_category_name_unique(self):
        """Test that category names are unique."""
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Technology")


class TagModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tag = Tag.objects.create(name="Django")

    def test_tag_creation(self):
        """Test that a tag is created correctly."""
        self.assertEqual(self.tag.name, "Django")

    def test_tag_str(self):
        """Test the __str__ method of Tag."""
        self.assertEqual(str(self.tag), "Django")

    def test_tag_name_unique(self):
        """Test that tag names are unique."""
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Django")
