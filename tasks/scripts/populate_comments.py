import logging

from tasks.factories import CommentFactory

logger = logging.getLogger("data_fixtures")


def run(n=60):
    logger.info("Creation of comments...")
    count = 0
    for _ in range(n):
        try:
            comment = CommentFactory()
            if not comment or not comment.id:
                raise ValueError("Failed to create comment")
            count += 1
        except Exception:
            logger.exception("Failed to create comment")
    logger.info(f"{count} comments from {n} successfully created.")


# python manage.py runscript populate_comments
