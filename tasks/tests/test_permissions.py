from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from tasks.models import Task
from tasks.permissions import CommentPermission, TaskPermission

# from authapp.permissions import IsAdminUser, IsManagerUser


class BasePermissionTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = MagicMock(groups=MagicMock(name="admin"))
        cls.manager = MagicMock(groups=MagicMock(name="manager"))
        cls.user = MagicMock(groups=MagicMock(name="user"))
        cls.executor = MagicMock(groups=MagicMock(name="user"))
        cls.owner = MagicMock(groups=MagicMock(name="manager"))
        cls.all_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

    def setUp(self):
        self.task = MagicMock(owner=self.owner)

    # def create_user(self, username, role):
    # user = User(username=username)  # храню в памяти а не в бд,
    # user.profile = UserProfile(user=user, role=role)  # создаю профиль в памяти
    # user = MagicMock(username=username)
    # user.profile = MagicMock(user=user, role=role)
    # return user


class TaskPermissionTestCase(BasePermissionTestCase):
    """Тест для пермишнов, не тестирую api.

    мокаю объекты на случай если изменятся и начнут требовать обязательные поля
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.permission = TaskPermission()

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()

    @patch("tasks.permissions.is_admin", return_value=True)
    def test_task_all_by_admin(self, mock_is_admin):
        allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

        for method in allowed_methods:
            # динамически создает HTTP-запрос, используя заданный метод:
            request = getattr(self.factory, method.lower())("/")
            # -> self.factory.get("/")
            # -> self.factory.post("/") и т д
            request.user = self.admin
            self.assertTrue(
                self.permission.has_permission(request, None)
            )  # у админа доступ к api
            # view=None, не нужен, т к проверяю только пермишен:
            # по юзеру и методу запроса
            self.assertTrue(
                self.permission.has_object_permission(request, None, self.task)
            )

    def test_task_forbidden_by_unauthorized(self):
        """Аноним не может ничего, даже просматривать задачи."""
        all_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

        for method in all_methods:
            request = getattr(self.factory, method.lower())("/")
            request.user = AnonymousUser()

            self.assertFalse(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.task)
            )

    @patch("tasks.permissions.is_manager", return_value=True)
    def test_task_get_post_by_manager(self, mock_is_manager):
        allowed_methods = ["GET", "POST"]
        denied_methods = ["PUT", "PATCH", "DELETE"]
        request = self.factory.get("/")
        request.user = self.manager

        for method in allowed_methods:
            request.method = method
            if method == "POST":
                self.assertTrue(self.permission.has_permission(request, None))
            else:
                self.assertTrue(self.permission.has_permission(request, None))
                self.assertTrue(
                    self.permission.has_object_permission(request, None, self.task)
                )

        for method in denied_methods:
            request.method = method
            self.assertTrue(
                self.permission.has_permission(request, None)
            )  # менеджеру доступен api
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.task)
            )

    @patch("tasks.permissions.is_manager", return_value=True)
    def test_task_all_allowed_except_delete_by_owner(self, mock_is_manager):
        allowed_methods = ["GET", "PUT", "PATCH"]
        denied_methods = ["DELETE"]
        request = self.factory.get("/")
        request.user = self.owner

        for method in allowed_methods:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertTrue(
                self.permission.has_object_permission(request, None, self.task)
            )

        for method in denied_methods:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.task)
            )

    @patch("tasks.permissions.is_user", return_value=True)
    def test_task_read_by_authorized(self, mock_is_user):
        allowed_methods = ["GET"]
        denied_methods = ["POST", "PUT", "PATCH", "DELETE"]
        request = self.factory.get("/")
        request.user = self.user
        request.data = {
            "status": "in_progress",
            "desctiption": "Working on it",
        }

        for method in allowed_methods:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertTrue(
                self.permission.has_object_permission(request, None, self.task)
            )

        for method in denied_methods:
            request.method = method
            if method == "POST":
                self.assertFalse(self.permission.has_permission(request, None))
            else:
                self.assertTrue(self.permission.has_permission(request, None))
                self.assertFalse(
                    self.permission.has_object_permission(request, None, self.task)
                )

    @patch("tasks.permissions.is_user", return_value=True)
    def test_executor_can_update_status_and_comments(self, mock_is_user):
        # говорю что юзер является исполнителем:
        self.task.executor.contains.return_value = True
        # разрешен PATCH в полях 'status' и 'comments':
        request = self.factory.patch("/")
        request.data = {"status": "in_progress"}
        request.user = self.executor

        self.assertTrue(
            self.permission.has_permission(request, None)
        )  # юзеру доступен api
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.task)
        )  # можно изменять дозволенные поля

        # запрещен PATCH в других полях:
        request.data = {"title": "New Task", "description": "Some description"}
        request.user = self.executor

        self.assertTrue(
            self.permission.has_permission(request, None)
        )  # юзеру доступен api
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.task)
        )  # нельзя изменять запрещенные поля


class CommentPermissionTestCase(BasePermissionTestCase):
    """Проверить что: админ может все; коммент к задачам может: создавать owner,
    executor этой задачи, редактировать частично, полностью, удалять author,
    просматривать любой авторизованный.

    коммент к задачам не может:     создавать owner, executor другой задачи,
    авторизованный,     редактировать частично, полностью, удалять ни owner этой задачи,
    ни авторизованный, ни другой executor этой задачи,
    """

    # TODO проверь на неверный номер таски, на отсутствие таски с таким номером в бд

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.author = MagicMock(role="user")
        cls.permission = CommentPermission()

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.comment = MagicMock(author=self.author, task=self.task)

    @patch("tasks.permissions.Task.objects.get")
    def test_comment_post_by_each_user(self, mock_get):
        # мок executors:
        executors_m2m_mock = MagicMock()
        executors_m2m_mock.all.return_value = [self.executor]
        self.task.executor = executors_m2m_mock
        # мок view:
        mock_view = MagicMock()
        mock_view.kwargs = {"task_pk": 1}

        mock_get.return_value = self.task

        # anonymous:
        # 'WSGIRequest' object has no attribute 'data'
        # оставлю сырой WSGIRequest, тк в дату мне и не нужно:
        request = self.factory.post("/")
        request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(request, None))

        for user in (self.admin, self.user, self.manager):
            wsgi_request = self.factory.post("/")
            force_authenticate(wsgi_request, user=user)
            request = Request(wsgi_request)
            self.assertFalse(self.permission.has_permission(request, view=mock_view))

        for user in (self.owner, self.executor):
            # нужна request.data - оборачиваю сырой запрос в Request DRF:
            wsgi_request = self.factory.post("/")
            force_authenticate(wsgi_request, user=user)
            request = Request(wsgi_request)
            self.assertTrue(self.permission.has_permission(request, view=mock_view))

    def test_comment_post_invalid_task_id(self):
        mock_view = MagicMock()
        mock_view.kwargs = {"task_pk": ""}
        wsgi_request = self.factory.post("/")
        force_authenticate(wsgi_request, user=self.owner)
        request = Request(wsgi_request)
        self.assertFalse(self.permission.has_permission(request, mock_view))

    @patch("tasks.permissions.Task.objects.get")
    def test_comment_post_nonexistent_task_id(self, mock_get):
        mock_view = MagicMock()
        mock_view.kwargs = {"task_pk": "99"}
        mock_get.side_effect = Task.DoesNotExist
        wsgi_request = self.factory.post("/")
        force_authenticate(wsgi_request, user=self.owner)
        request = Request(wsgi_request)
        self.assertFalse(self.permission.has_permission(request, mock_view))

    def test_comment_all_by_author(self):
        """Коммент уже создан автором."""
        request = self.factory.get("/")
        request.user = self.author

        for method in ["GET", "PUT", "PATCH", "DELETE"]:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertTrue(
                self.permission.has_object_permission(request, None, self.comment)
            )

    @patch("tasks.permissions.is_admin", return_value=True)
    def test_comment_read_delete_by_admin(self, mock_is_admin):
        """Админ не может создавать и редактировать комменты."""
        request = self.factory.get("/")

        for method in ["GET", "PUT", "PATCH", "DELETE"]:
            request.method = method
            request.user = self.admin

            if method in ("GET", "DELETE"):
                self.assertTrue(self.permission.has_permission(request, None))
                self.assertTrue(
                    self.permission.has_object_permission(request, None, self.comment)
                )

            elif method in ("PUT", "PATCH"):
                self.assertTrue(self.permission.has_permission(request, None))
                self.assertFalse(
                    self.permission.has_object_permission(request, None, self.comment)
                )

    def test_comment_forbidden_by_unauthorized(self):
        """Аноним не может ничего, даже просматривать комменты."""

        for method in self.all_methods:
            request = getattr(self.factory, method.lower())("/")
            request.user = AnonymousUser()

            self.assertFalse(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.comment)
            )

    def test_comment_read_by_authorized(self):
        request = self.factory.get("/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))  # GET
        for method in ["PUT", "PATCH", "DELETE"]:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.comment)
            )

    def test_comment_read_by_manager(self):
        # GET:
        request = self.factory.get("/")
        request.user = self.manager
        self.assertTrue(self.permission.has_permission(request, None))
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.comment)
        )

        for method in ("PUT", "PATCH", "DELETE"):
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.comment)
            )

    def test_comment_read_create_by_task_owner(self):
        request = self.factory.get("/")
        request.user = self.owner

        self.assertTrue(self.permission.has_permission(request, None))  # GET
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.comment)
        )

        for method in ["PUT", "PATCH", "DELETE"]:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.comment)
            )

    def test_comment_read_create_by_task_executor(self):
        request = self.factory.get("/")
        request.user = self.executor
        # GET:
        self.assertTrue(self.permission.has_permission(request, None))
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.comment)
        )

        for method in ["PUT", "PATCH", "DELETE"]:
            request.method = method
            self.assertTrue(self.permission.has_permission(request, None))
            self.assertFalse(
                self.permission.has_object_permission(request, None, self.comment)
            )
