import logging

from tasks.factories import TaskFactory

logger = logging.getLogger("data_fixtures")


def run(n=50):
    logger.info("Creation of tasks...")
    count = 0
    for _ in range(n):
        try:
            task = TaskFactory()
            if not task or not task.id:
                raise ValueError("Failed to create task")
            count += 1
        except Exception:
            logger.exception("Failed to create task")
    logger.info(f"{count} tasks from {n} successfully created.")


# python manage.py runscript populate_tasks
