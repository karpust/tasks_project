from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from authapp.serializers import ChangePasswordSerializer, RegisterSerializer

User = get_user_model()


class RegisterSerializerTest(APITestCase):
    """Тестирование сериализатора регистрации пользователя: все валидные данные удачное
    создание юзера невалидный username дублирующийся username невалидный email слабый
    пароль."""

    def setUp(self):
        # Создаем пользователя для теста на уникальность email и username
        self.existing_user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="strongpassword123",
        )

    def test_valid_data(self):
        """Проверка сериализатора с валидными данными."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "strongpassword123",
        }

        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_successful_user_creation(self):
        """Проверка, что пользователь создается корректно."""
        valid_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "strongpassword123",
        }
        serializer = RegisterSerializer(data=valid_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, valid_data["username"])
        self.assertEqual(user.email, valid_data["email"])
        self.assertTrue(
            user.check_password(valid_data["password"])
        )  # что пароль хешируется
        self.assertFalse(user.is_active)  # что пользователь не активен по умолчанию

    def test_invalid_username(self):
        """Проверка сериализатора на невалидный username."""
        invalid_data = {
            "username": "n3",
            "email": "newuser@example.com",
            "password": "strongpassword123",
        }

        serializer = RegisterSerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_duplicate_username(self):
        """Проверка сериализатора на дублирующийся username."""
        invalid_data = {
            "username": "existinguser",
            "email": "newuser@example.com",
            "password": "strongpassword123",
        }

        serializer = RegisterSerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)
        self.assertEqual(
            serializer.errors["username"][0],
            "A user with that username already exists.",
        )

    def test_invalid_email(self):
        """Параметризованный тест для проверки всех ошибок валидации email."""
        invalid_cases = [
            {
                "data": {
                    "email": "not-an-email",
                    "password": "securepassword",
                },
                "field": "email",
                "msg": "Enter a valid email address.",
            },
            {
                "data": {
                    "email": "existing@example.com",
                    "password": "securepassword",
                },
                "field": "email",
                "msg": "This field must be unique.",
            },
            {
                "data": {"email": "", "password": "securepassword"},
                "field": "email",
                "msg": "This field may not be blank.",
            },
        ]

        for case in invalid_cases:
            with self.subTest(
                msg=case["msg"]
            ):  # подтесты – тестирует каждую невалидность отдельно
                serializer = RegisterSerializer(data=case["data"])
                self.assertFalse(serializer.is_valid())
                self.assertIn(case["field"], serializer.errors)
                self.assertEqual(serializer.errors["email"][0], case["msg"])

    def test_weak_password(self):
        """Проверка сериализатора на слишком слабый пароль."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "short1",  # пароль слишком короткий
        }

        serializer = RegisterSerializer(data=data)

        # Проверка, что данные не валидны из-за слабого пароля
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)
        self.assertEqual(
            serializer.errors["password"][0],
            "This password is too short." " It must contain at least 8 characters.",
        )


class ChangePasswordSerializerTest(APITestCase):
    def test_passwords_match_and_valid(self):
        data = {
            "new_password": "new_password123",
            "confirm_password": "new_password123",
        }

        serializer = ChangePasswordSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertNotIn("new_password", serializer.errors)

    def test_passwords_not_match(self):
        invalid_data = {
            "new_password": "new_password123",
            "confirm_password": "other_password123",
        }

        serializer = ChangePasswordSerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)
        self.assertEqual(serializer.errors["new_password"][0], "Пароли не совпадают.")

    def test_password_invalid_data(self):
        invalid_data = {"new_password": "pas123", "confirm_password": "pas123"}

        serializer = ChangePasswordSerializer(data=invalid_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)
