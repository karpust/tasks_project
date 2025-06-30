from django_celery_beat.models import IntervalSchedule, PeriodicTask


def run():
    """Создает периодические задачи в celery-beat Уведомляет юзеров о дедлайне задачи,
    которую они выполняют или создали."""

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=5, period=IntervalSchedule.MINUTES
    )

    task, created = PeriodicTask.objects.update_or_create(
        name="Уведомление о скором дедлайне",
        task="tasks.tasks.deadline_notification",
        defaults={
            "interval": schedule,
        },
    )

    if created:
        print(f"Периодическая задача '{task.name}' создана")
    else:
        print(f"Периодическая задача '{task.name}' обновлена")


# запуском python manage.py runscript setup_deadline_notification_periodic_task
# создается новое расписание(или берется старое) в бд
# и обновляется или создается задача в бд
