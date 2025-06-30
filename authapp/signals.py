from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
# post_save - сигнал, срабатывает после сохранения пользователя (User) в бд.
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # sender-модель для которой сработает сигнал
    # created(True-если объект создан, False-если обновлен)
    if created:
        # создаем профиль юзера:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()


"""
@receiver(post_save, sender=User) сообщает Django,
что функция create_or_update_user_profile будет вызываться,
когда сработает сигнал post_save для модели User.
т е сигнал будет слушать сохранение объектов User.
"""
