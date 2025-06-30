from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from tasks.models import Task
from tasks.tasks import deadline_notification, left_time

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CeleryIntegrationTest(TestCase):
    def setUp(self):
        # print(f"Database used: {connection.settings_dict['NAME']}")
        self.executor = User.objects.create(
            username="executor", email="executor@mail.com"
        )
        self.owner = User.objects.create(username="owner", email="owner@mail.com")

        self.task = Task.objects.create(
            title="Important task",
            owner=self.owner,
            notified=False,
            deadline=timezone.now() + timedelta(hours=left_time),
        )
        self.task.executor.set([self.executor])

    def test_celery_task_runs_and_updates(self):
        # 1. Ставим задачу в очередь
        result = deadline_notification.delay()

        # 2. Ждём выполнения (до 10 сек)
        result.get(timeout=10)

        # 3. Проверяем, что задача отработала успешно
        self.assertTrue(result.successful())

        # 4. Обновляем объект из БД
        self.task.refresh_from_db()

        # 5. Проверяем, что notified стал True
        self.assertTrue(self.task.notified)

        # 6. Проверяем, что письма были отправлены
        self.assertEqual(len(mail.outbox), 2)
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn("owner@mail.com", recipients)
        self.assertIn("executor@mail.com", recipients)
