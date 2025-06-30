from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.test import TestCase

from authapp.models import UserProfile
from authapp.signals import create_or_update_user_profile


class UserProfileSignalTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.assertEqual(User.objects.count(), 1)

    def test_profile_created_on_user_creation(self):
        """Проверяет, что профиль создается автоматически при создании юзера."""
        self.assertEqual(UserProfile.objects.count(), 1)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.user, self.user)

    def test_profile_not_created_when_signals_disabled(self):
        """Проверяет, что профиль не создается, если сигналы отключены."""

        # отключение сигнала и создание нового юзера:
        post_save.disconnect(create_or_update_user_profile, sender=User)
        new_user = User.objects.create_user(username="newuser", password="testpassword")
        self.assertEqual(User.objects.count(), 2)

        # проверка, что новый профиль не создался (только профиль из setUp):
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertFalse(UserProfile.objects.filter(user=new_user).exists())

        # включаем сигнал обратно, нужно для setUp для дальнейших тестов:
        post_save.connect(create_or_update_user_profile, sender=User)

    def test_profile_persists_on_user_update(self):
        """Проверяет, что профиль сохраняется при обновлении юзера."""
        # профиль от setUp:
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(UserProfile.objects.count(), 1)

        # обновляю юзера:
        self.user.username = "updateduser"
        self.user.save()

        # проверяю, что профиль остался привязан к юзеру, не создан новый:
        self.assertEqual(UserProfile.objects.count(), 1)
        updated_profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(updated_profile, profile)
        self.assertEqual(updated_profile.user.username, "updateduser")

    # def tearDown(self):
    #     """Очистка после тестов"""
    #     User.objects.all().delete()
    #     UserProfile.objects.all().delete()
