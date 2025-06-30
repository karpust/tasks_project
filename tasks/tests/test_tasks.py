from datetime import timedelta
from unittest.mock import patch

from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.utils import timezone
from rest_framework.test import APITestCase

from tasks.models import Task
from tasks.tasks import deadline_notification, left_time

User = get_user_model()


# @override_settings(CELERY_TASK_ALWAYS_EAGER=True,
#                    CELERY_TASK_EAGER_PROPAGATES=True,)
class TestNotificationTask(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # setUpTestData откатит все изменения тк TestCase
        user_group = Group.objects.create(name="user")
        cls.executor1 = User.objects.create(
            username="executor1", email="executor1@mail.com"
        )
        cls.executor2 = User.objects.create(
            username="executor2", email="executor2@mail.com"
        )
        cls.executor3 = User.objects.create(
            username="executor3", email="executor3@mail.com"
        )
        cls.executor4 = User.objects.create(
            username="executor4", email="executor4@mail.com"
        )
        cls.executor1.groups.set([user_group])
        cls.executor2.groups.set([user_group])
        cls.executor3.groups.set([user_group])
        cls.executor4.groups.set([user_group])

        cls.owner1 = User.objects.create(username="owner1", email="owner1@mail.com")
        cls.owner2 = User.objects.create(username="owner2", email="owner2@mail.com")
        cls.owner3 = User.objects.create(username="owner3", email="owner3@mail.com")
        cls.owner4 = User.objects.create(username="owner4", email="owner4@mail.com")
        manager_group = Group.objects.create(name="manager")
        cls.owner1.groups.set([manager_group])
        cls.owner2.groups.set([manager_group])
        cls.owner3.groups.set([manager_group])
        cls.owner4.groups.set([manager_group])

        cls.task1 = Task.objects.create(
            owner=cls.owner1,
            title="task1",
            notified=False,
            deadline=timezone.now() + timedelta(hours=left_time),
        )  # нужно уведомить
        cls.task1.executor.set([cls.executor1])
        cls.task2 = Task.objects.create(
            owner=cls.owner2,
            notified=False,
            title="task2",
            deadline=timezone.now() + timedelta(hours=1),
        )  # нужно уведомить
        cls.task2.executor.set([cls.executor2, cls.executor3])
        cls.task3 = Task.objects.create(
            owner=cls.owner3,
            title="task3",
            notified=False,
            deadline=timezone.now() + timedelta(hours=left_time + 6),
        )  # рано уведомлять
        cls.task3.executor.set([cls.executor3])
        cls.task4 = Task.objects.create(
            owner=cls.owner4,
            title="task4",
            notified=False,
            deadline=timezone.now() - timedelta(hours=1),
        )  # просрочена
        cls.task4.executor.set([cls.executor4])
        cls.task5 = Task.objects.create(
            owner=cls.owner4,
            title="task5",
            notified=True,
            deadline=timezone.now() + timedelta(hours=15),
        )  # уже уведомили
        cls.task5.executor.set([cls.executor1, cls.executor4])

        cls.all_tasks = [cls.task1, cls.task2, cls.task3, cls.task4, cls.task5]

    @patch("tasks.tasks.logger")
    @patch(
        "tasks.tasks.EmailMultiAlternatives.send",
        side_effect=Exception("SMTP error"),
    )
    def test_exeptions(self, mock_send, mock_logger):
        with patch.object(
            deadline_notification, "retry", side_effect=Retry("retry called")
        ):
            # мокаю метод deadline_notification.retry
            with self.assertRaises(Retry):
                deadline_notification()

        mock_send.assert_called_once()
        self.assertEqual(len(mail.outbox), 0)
        mock_logger.exception.assert_called_once_with(
            "[FAILURE] Type: Deadline notifications"
        )

    def test_deadline_soon_not_notified(self):
        """Тест задачи с близким дедлайном(24ч), о котором еще не было уведомления.

        проверка, чо уведомление отсылается на почту,
        среди уведомленных юзеров - создатель и испольнители именно этой задачи.
        проверяю без celery
        """
        self.assertEqual(self.task1.notified, False)
        self.assertEqual(self.task2.notified, False)

        deadline_notification()

        for task in self.all_tasks:
            task.refresh_from_db()

        self.assertEqual(self.task1.notified, True)
        self.assertEqual(self.task2.notified, True)
        self.assertEqual(self.task3.notified, False)
        self.assertEqual(self.task4.notified, False)
        self.assertEqual(self.task5.notified, True)

        # проверяю сколько всего отправилось писем:
        self.assertEqual(len(mail.outbox), 5)  # for task1(2), task2(3)
        emails = [email.to[0] for email in mail.outbox]
        # проверяю кому конкретно:
        self.assertIn("owner1@mail.com", emails)
        self.assertIn("executor1@mail.com", emails)
        self.assertIn("owner2@mail.com", emails)
        self.assertIn("executor2@mail.com", emails)
        self.assertIn("executor3@mail.com", emails)

        # expected_emails = {
        #     'owner1@mail.com',
        #     'executor1@mail.com',
        #     'owner2@mail.com',
        #     'executor2@mail.com',
        #     'executor3@mail.com',
        # }
        # self.assertEqual(set(emails), expected_emails)

        # проверяю кому какой текст отправлен:
        for email in mail.outbox:
            self.assertIn(
                (
                    "Скоро дедлайн выполняемой вами задачи"
                    if email.to[0].startswith("executor")
                    else "Скоро дедлайн созданной вами задачи"
                ),
                email.subject,
            )
