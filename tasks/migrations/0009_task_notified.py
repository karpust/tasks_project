# Generated by Django 5.1.7 on 2025-05-15 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "tasks",
            "0008_alter_category_options_alter_comment_options_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="notified",
            field=models.BooleanField(default=False),
        ),
    ]
