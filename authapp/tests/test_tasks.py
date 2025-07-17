from datetime import timedelta
from unittest.mock import patch

from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from authapp.tasks import delete_unconfirmed_users, send_email_task

User = get_user_model()


class TestSendEmailConfirmation(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user", email="user@email.com")

    def test_send_email_success(self):
        email_types = (
            "register_confirmation",
            "repeat_register_confirmation",
            "reset_password_confirmation",
        )
        subject_types = (
            "Подтверждение email",
            "Повторное подтверждение email",
            "Сброс пароля",
        )
        body_types = (
            "подтвердите свой email",
            "подтвердите свой email",
            "Перейдите по ссылке для сброса пароля",
        )

        for i in range(len(email_types)):
            send_email_task(
                email_types[i],
                context={"user": self.user, "confirmation_link": "some_link"},
                recipient=self.user.email,
            )

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].subject, subject_types[i])
            self.assertIn(body_types[i], mail.outbox[0].body)
            self.assertEqual(mail.outbox[0].to, ["user@email.com"])
            mail.outbox.clear()

    @patch("authapp.tasks.auth_logger")
    @patch(
        "authapp.tasks.EmailMultiAlternatives.send",
        side_effect=Exception("SMTP error"),
    )
    def test_send_email_failure(self, mock_send, mock_logger):
        with patch.object(send_email_task, "retry", side_effect=Retry("retry called")):
            with self.assertRaises(Retry):
                send_email_task(
                    "register_confirmation",
                    context={
                        "user": self.user,
                        "confirmation_link": "some_link",
                    },
                    recipient=self.user.email,
                )

        mock_send.assert_called_once()
        self.assertEqual(len(mail.outbox), 0)
        mock_logger.exception.assert_called_once_with(
            "[FAILURE] Type: register_confirmation"
        )


class TestDeleteUconfirmedUsers(TestCase):
    def setUp(self):
        self.user1 = User.objects.create(username="user1", is_active=True)
        self.user2 = User.objects.create(
            username="user2",
            is_active=False,
            date_joined=timezone.now() - timedelta(minutes=2),
        )
        self.user3 = User.objects.create(
            username="user3",
            is_active=False,
            date_joined=timezone.now() - timedelta(minutes=10),
        )

    def test_delete_confirmed_users(self):
        delete_unconfirmed_users()

        self.assertEqual(User.objects.all().count(), 2)
        self.assertIn(self.user1, User.objects.all())
        self.assertIn(self.user2, User.objects.all())
        self.assertNotIn(self.user3, User.objects.all())
