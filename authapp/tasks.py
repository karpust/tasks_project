import logging
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger("email_tasks")


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_email_task(self, email_type, context, recipient):
    """Выполняет задачи с разными приоритетами, на разных воркерах, принимает тип
    письма, по которому выбирает шаблон-html.

    на выполнение задачи дается 3 попытки c интервалом в 5 мин
    """
    logger.info("[SEND EMAIL TASK CODE STARTED]")
    try:
        template_name = f"emails/{email_type}"
        text_content = render_to_string(f"{template_name}.txt", context)
        html_content = render_to_string(f"{template_name}.html", context)
        subject_map = {
            "register_confirmation": "Подтверждение email",
            "repeat_register_confirmation": "Повторное подтверждение email",
            "reset_password_confirmation": "Сброс пароля",
        }
        subject = subject_map.get(email_type, "Письмо")

        msg = EmailMultiAlternatives(subject, text_content, to=[recipient])
        msg.attach_alternative(html_content, "text/html")
        # print(f'msg.recipients() = {msg.recipients()}')  # кому
        # print(f'msg.body = {msg.body}')  # текстовая часть
        # print(f'msg.alternatives = {msg.alternatives}')  # список с html
        msg.send()
        logger.info(f"[SUCCESS] Type: {email_type} | Email: {recipient}")

    except Exception as e:
        logger.exception(f"[FAILURE] Type: {email_type}")
        raise self.retry(exc=e)


User = get_user_model()


@shared_task
def delete_unconfirmed_users():
    logger.info("[DELETE UNCONFIRMED USERS CODE STARTED")
    cutoff = timezone.now() - timedelta(minutes=5)
    users = User.objects.filter(is_active=False, date_joined__lt=cutoff)

    count = users.count()
    users.delete()

    # logger.info(f"Удалено {count} неподтверждённых аккаунтов")
    logger.info(f"[SUCCESS] Deleted {count} unconfirmed users")
