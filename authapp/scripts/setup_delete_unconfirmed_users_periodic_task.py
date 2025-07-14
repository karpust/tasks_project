from django_celery_beat.models import IntervalSchedule, PeriodicTask


def run():
    """Создаёт периодические задачи Celery Beat создается отдельно расписание в таблице
    бд создается отдельно задача в таблице бд."""

    schedule, _ = IntervalSchedule.objects.get_or_create(
        # в бд создается таблица django_celery_beat_intervalschedule
        every=7,
        period=IntervalSchedule.MINUTES,
    )

    task, created = PeriodicTask.objects.update_or_create(
        # в бд создается таблица django_celery_beat_periodictask
        name="Удаление неподтверждённых юзеров",
        task="authapp.tasks.delete_unconfirmed_users",
        # в defaults указывают поля кот обновятся если объект найден в бд;
        # хочу чтобы задача обновлялась при изменении расписания:
        defaults={
            "interval": schedule,
            "queue": "low_priority",
            # 'args': '[]',
        },
    )

    if created:
        print(f"Периодическая задача '{task.name}' создана.")

    else:
        print(f"Периодическая задача '{task.name}' обновлена.")


# python manage.py runscript setup_delete_unconfirmed_users_periodic_tasks
# создается новое расписание(или берется старое) в бд
# и обновляется или создается задача в бд
