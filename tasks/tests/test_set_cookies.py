from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class CookieAuthTests(APITestCase):
    """Проверяет, что токен устанавливается в httponly cookie.

    нужно для создание метода аутентификации для тестов
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.access_token = str(AccessToken.for_user(self.user))

        # записываю токен в куку (перезапись кук а не добавление!):
        self.client.cookies.load(
            {
                "access_token": self.access_token,
                # 'refresh_token':
            }
        )
        # добавляю необходимые параметры загруженному токену:
        # но этот тест проходит и без них
        self.client.cookies["access_token"]["httponly"] = True
        self.client.cookies["access_token"]["samesite"] = "Lax"
        # secure=False по умолчанию - т к для тестов

    def test_protected_view(self):
        response = self.client.get("/users/")  # check permissions.IsAuthenticated
        self.assertEqual(response.status_code, 200)
