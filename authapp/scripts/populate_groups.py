import logging

from django.contrib.auth.models import Group

logger = logging.getLogger("data_fixtures")


def run():
    roles = ["admin", "manager", "user"]
    logger.info("Creation of groups...")
    try:
        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            logger.info(
                f"""Group "{role}" {"created successfully" if created
                else "already created earlier"}."""
            )
        logger.info("All groups created.")
    except Exception:
        logger.exception("Failed to create groups.")


# python manage.py runscript populate_groups
