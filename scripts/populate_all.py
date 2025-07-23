import logging

from django.core.management import call_command

logger = logging.getLogger("data_fixtures")


def run():
    print("Cleaning old data...")
    call_command("runscript", "clear_all")

    print("Creation of groups...")
    call_command("runscript", "populate_groups")

    print("Creation of users...")
    call_command("runscript", "populate_users")

    print("Creation of categories...")
    call_command("runscript", "populate_tasks")

    print("Creation of tasks...")
    call_command("runscript", "populate_comments")

    print("The data is successfully filled!")
