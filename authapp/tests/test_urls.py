from django.test import SimpleTestCase
from django.urls import resolve, reverse

from authapp.views import (
    ChangePasswordAPIView,
    ConfirmRegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    RefreshTokenAPIView,
    RegisterAPIView,
    RepeatConfirmRegisterAPIView,
    ResetPasswordAPIView,
)


class URLTestCase(SimpleTestCase):  # ?
    def test_register_url_resolves(self):
        """Проверка, что URL register/ вызывает правильную вью."""
        url = reverse("register")  # беру URL по имени
        self.assertEqual(
            resolve(url).func.view_class, RegisterAPIView
        )  # resolve(url) ищет связанный вью

    def test_verify_email_url_resolves(self):
        """Проверка, что url verify_email/ вызывает правильную вью."""
        url = reverse("confirm_register")
        self.assertEqual(resolve(url).func.view_class, ConfirmRegisterAPIView)

    def test_resend_verify_email_url_resolves(self):
        url = reverse("repeat_confirm_register")
        self.assertEqual(resolve(url).func.view_class, RepeatConfirmRegisterAPIView)

    def test_login_url_resolves(self):
        url = reverse("login")
        self.assertEqual(resolve(url).func.view_class, LoginAPIView)

    def test_logout_url_resolves(self):
        url = reverse("logout")
        self.assertEqual(resolve(url).func.view_class, LogoutAPIView)

    def test_refresh_token_url_resolves(self):
        url = reverse("refresh_token")
        self.assertEqual(resolve(url).func.view_class, RefreshTokenAPIView)

    def test_reset_password_url_resolves(self):
        url = reverse("reset_password")
        self.assertEqual(resolve(url).func.view_class, ResetPasswordAPIView)

    def test_change_password_url_resolves(self):
        url = reverse(
            "change_password",
            kwargs={"uid": "some_uid", "token": "some_token"},
        )
        self.assertEqual(resolve(url).func.view_class, ChangePasswordAPIView)
