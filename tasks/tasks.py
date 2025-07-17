import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from tasks.models import Task
from tasks.permissions import is_admin, is_manager

logger = logging.getLogger("notification_tasks")


left_time = 24


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def deadline_notification(self):
    """Уведомляет создателя задачи и назначенных исполнителей.

    о дедлайне за 24 часа;
    если у задачи notified=False, но она просрочена - уведомление не посылается;
    """
    logger.info("[DEADLINE NOTIFICATION CODE STARTED]")
    # logger.info(f"Database used: {connection.settings_dict['NAME']}")
    try:
        logger.info("[TRY TO FIND SOME TASKS]")
        now_time = timezone.now()
        logger.info(f"[EVALUATE NOW_TIME]: {now_time}")
        check_time = now_time + timedelta(hours=left_time)
        logger.info(f"[EVALUATE CHECK_TIME]: {check_time}")
        tasks = Task.objects.filter(
            deadline__lte=check_time, deadline__gte=now_time, notified=False
        )
        # ищу задачи у которых дедлайн через 24 часа или меньше, не просроченные,
        # еще не уведомлялись
        logger.info(f"[FINDED {tasks.count()} TASKS WITH A CLOSE DEADLINE]")
        for task in tasks:
            users = [task.owner]
            users.extend(task.executor.all())

            logger.info(f"[TASK'S DEADLINE IS '{task.deadline}']")
            logger.info(
                f"[USERS THAT MUST BE NOTIFICATED IS {task.owner, task.executor.all()}]"
            )

            for user in users:
                context = {
                    "task": task,
                    "username": user.username,
                }
                subject = (
                    f"Скоро дедлайн созданной вами задачи {task.title}"
                    if is_admin(user) or is_manager(user)
                    else f"Скоро дедлайн выполняемой вами задачи {task.title}"
                )
                text_content = render_to_string(
                    "notifications/deadline_notification.txt", context
                )
                html_content = render_to_string(
                    "notifications/deadline_notification.html", context
                )

                recipient = user.email
                msg = EmailMultiAlternatives(subject, text_content, to=[recipient])
                msg.attach_alternative(html_content, "text/html")

                # print(f'msg.recipients() = {msg.recipients()}')  # кому
                # print(f'msg.body = {msg.body}')  # текстовая часть
                # print(f'msg.alternatives = {msg.alternatives}')  # список с html
                logger.debug(f"Email details: to={recipient}, subject={subject}")

                msg.send()
                logger.info(
                    f"[SUCCESS] Type: Deadline notifications | Email: {recipient}"
                )

                task.notified = True

                # task.save()  # make полный UPDATE всех полей
                task.save(update_fields=["notified"])  # обновление только этого поля
                # UPDATE tasks_task SET notified = true WHERE id = 123;

    except Exception as e:
        # logger.error(f"[FAILURE] Deadline notifications | Error: {str(e)}")
        logger.exception("[FAILURE] Type: Deadline notifications")  # покажет traceback

        raise self.retry(exc=e)
