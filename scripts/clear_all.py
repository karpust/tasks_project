import logging

logger = logging.getLogger("data_fixtures")


def run():
    from django.contrib.auth.models import Group, User

    from tasks.models import Category, Comment, Task

    logger.info("Removing comments...")
    Comment.objects.all().delete()

    logger.info("Removing tasks...")
    Task.objects.all().delete()

    logger.info("Removing categories...")
    Category.objects.all().delete()

    logger.info("Removing users...")
    User.objects.all().delete()

    # logger.info("Removing users, except superuser...")
    # User.objects.exclude(is_superuser=True).delete()

    logger.info("Removing groups...")
    Group.objects.all().delete()

    logger.info("Data successfully cleaned!")
