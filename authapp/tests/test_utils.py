import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

# from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from authapp.utils import (
    create_verification_link,
    generate_email_verification_token,
    send_verification_email,
    time_email_verification,
)
from tasks_project.settings import DOMAIN_NAME

User = get_user_model()


class EmailVerificationUtilsTestCase(APITestCase):
    """Правильный ли токен, правильная ли ссылка, отправляется ли письмо."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            username="testuser",
        )

    def test_generate_email_verification_token(self):
        """Проверяет корректно ли генерируется и сохраняется в кэше UUID-токен, user_id,
        created_at."""
        token, created_at, lifetime = generate_email_verification_token(self.user)

        self.assertIsInstance(token, uuid.UUID)
        self.assertIsInstance(created_at, datetime)
        self.assertEqual(lifetime, timedelta(minutes=10))

        cached_data = cache.get(f"email_verification_token_{token}")  # кэш
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data["user_id"], self.user.id)
        self.assertEqual(cached_data["created_at"], created_at)

    def test_token_removal_from_cache_after_ttl(self):
        """Проверяет, что токен удаляется из кэша, не превышая ttl; TTL (Time- To-Live)
        — это время жизни ключа в кэше."""
        # cache_backend = caches['default']  # см какой кэш юзаю
        # print(cache_backend._cache)  # покажет все ключи и их значения
        cache.clear()  # очистка кеша перед тестом - необязательно

        with freeze_time("2025-03-19 12:00:00") as frozen:
            # print("created at ", datetime.now())

            # создаю токен со временем жизни time_email_verification:
            token, _, _ = generate_email_verification_token(self.user)

            # проверяю, что токен попал в кэш:
            cached_token = cache.get(f"email_verification_token_{token}")
            self.assertIsNotNone(cached_token)

            # перемещаю время, чтобы токен истек:
            frozen.tick(delta=timedelta(minutes=time_email_verification))  # 10 минут
            # print("time pass...", datetime.now())

            cached_token = cache.get(f"email_verification_token_{token}")
            self.assertIsNone(cached_token)

    @patch("authapp.utils.generate_email_verification_token")
    def test_create_verification_link(self, mock_generate_token):
        """Проверяет корректно ли генерируется ссылка подтверждения email."""
        mock_token = uuid.uuid4()
        mock_created_at = timezone.now()
        mock_lifetime = timedelta(minutes=10)
        # мок-функция симулирует работу:
        mock_generate_token.return_value = (
            mock_token,
            mock_created_at,
            mock_lifetime,
        )

        # вызывает mock_generate_token:
        verification_link = create_verification_link(self.user)
        expected_link = (
            f'{DOMAIN_NAME}{reverse("confirm_register")}'
            f"?token={mock_token}&expires_at="
            f"{mock_created_at + mock_lifetime}"
        )
        # reverse('verify_email')  # /api/authapp/verify_email/

        # проверяю что ф-ция вызывается:
        mock_generate_token.assert_called_once()
        # сравниваем результ create_verification_link и собраную вручную:
        self.assertEqual(verification_link, expected_link)

    @patch("authapp.utils.send_mail")  # где импорт, оттуда подменяю
    @patch(
        "authapp.utils.create_verification_link"
    )  # ф-ция проверена выше, можно мокать
    def test_send_verification_email(self, mock_create_link, mock_send_mail):
        """Проверяет отправляется ли письмо-подтвержение."""
        mock_create_link.return_value = "http://testserver/confirm_register?token=1234"

        send_verification_email(self.user)  # вызовет mock_create_link и mock_send_mail

        mock_create_link.assert_called_once_with(self.user)
        mock_send_mail.assert_called_once_with(
            "Подтверждение email",
            "Пожалуйста, подтвердите свой email, перейдя по ссылке: "
            "http://testserver/confirm_register?token=1234",
            "noreply@yourdomain.com",
            [self.user.email],
        )
