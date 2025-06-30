from django.contrib import admin

from tasks.models import Category, Comment, Tag, Task

# Register your models here.

admin.site.register(Category)
admin.site.register(Tag)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "owner",
        "get_owner_group",
        "get_executor",
        "status",
        "deadline",
        "notified",
    )
    ordering = ("id",)

    def get_executor(self, object):
        return ", ".join([str(executor.id) for executor in object.executor.all()])

    get_executor.short_description = "Исполнители"

    def get_owner_group(self, object):
        return ", ".join([group.name for group in object.owner.groups.all()])

    get_owner_group.short_description = "Роли создателей"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "task", "author")
    ordering = ("id",)
