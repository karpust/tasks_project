from authapp.scripts import setup_delete_unconfirmed_users_periodic_task
from tasks.scripts import setup_deadline_notification_periodic_task


def run():
    """Скрипт для запуска всех периодических задач проекта."""
    setup_deadline_notification_periodic_task.run()
    setup_delete_unconfirmed_users_periodic_task.run()
    print("Все периодические задачи зарегистрированы.")
