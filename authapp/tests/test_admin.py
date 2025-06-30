from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AdminUserFormTest(APITestCase):
    def setUp(self):
        # создаю админа и логинюсь, проверяю логин:
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.client.login(
            username="admin", password="adminpass"
        )  # логинюсь не вообще, а в админку!
        res = self.client.get("/admin/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # создаю тестового юзера и группы:
        self.user = User.objects.create_user(
            username="testuser", email="u@example.com", password="123456789"
        )
        self.group1 = Group.objects.create(name="user")
        self.group2 = Group.objects.create(name="manager")

    def test_user_change_form_group_selection(self):
        # назначу юзеру группу user:
        self.user.groups.set([self.group1])

        # открою страницу редактирования юзера в админке:
        url = reverse("admin:auth_user_change", args=[self.user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # проверю, что в форме та группа которая была задана:
        self.assertContains(response, "<select", html=False)
        self.assertIn('name="groups"', response.content.decode())
        self.assertIn(
            f'<option value="{self.group1.pk}" selected>',
            response.content.decode(),
        )

        # отправляю форму с другой группой, проверяю что форма ушла:
        data = {
            "username": "testuser",
            "email": "u@example.com",
            "password": self.user.password,
            "groups": self.group2.pk,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login_0": "",
            "last_login_1": "",
            "date_joined_0": self.user.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": self.user.date_joined.strftime("%H:%M:%S"),
            "_save": "Сохранить",
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        # обновлю юзера и проверю, что группа тоже обновилась:
        self.user.refresh_from_db()
        user_groups = list(self.user.groups.all())
        self.assertEqual(len(user_groups), 1)
        self.assertEqual(user_groups[0], self.group2)
