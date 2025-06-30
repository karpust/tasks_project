from rest_framework import permissions

from tasks.models import Task


def get_group_name(user):
    group = user.groups.first()
    return group.name if group else "user"


def is_admin(user):
    return get_group_name(user) == "admin"


def is_manager(user):
    return get_group_name(user) == "manager"


def is_user(user):
    return get_group_name(user) == "user"


class TaskPermission(permissions.BasePermission):
    """Объединённое разрешение для работы с задачами."""

    def has_permission(self, request, view):
        # доступ к api /tasks/:
        if request.user.is_authenticated:
            if request.method == "POST":
                return is_admin(request.user) or is_manager(request.user)
            return True
        return False

    def has_object_permission(self, request, view, obj):

        if not request.user.is_authenticated:
            return False

        if is_admin(request.user):
            return True

        if is_manager(request.user):
            if request.user == obj.owner:
                return request.method in ["GET", "PATCH", "PUT"]
            return request.method == "GET"

        if is_user(request.user):
            # может изменять только поле 'status':
            if obj.executor.contains(request.user):  # m2m
                # same as request.user ==
                # obj.executor.filter(id=request.user.id).first()
                # юзер может изменять только те задачи, где назначен исполнителем:
                if request.method == "PATCH":
                    return set(request.data.keys()).issubset(
                        {"status"}
                    )  # статус или пустой
                if request.method == "GET":
                    return True

            return request.method == "GET"


"""
получает поля из request.data(из тела запроса на изменение)
преобразует их во множество
проверяет является ли это множество подмножеством {'status', 'comments'- убери}
"""


class CommentPermission(permissions.BasePermission):
    """Проверяет действия ролей, не аутентификацию."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        if request.method == "POST":
            # try to get task's creator or executor:
            # invalid data - no access:
            task_id = view.kwargs.get("task_pk")  # получаем task_pk из URL
            if not task_id:  # invalid data
                return False
            # from tasks.models import Task  # Импорт здесь, чтобы избежать циклов
            try:
                task = Task.objects.get(id=task_id)
                view.task = task
            except (ValueError, Task.DoesNotExist):
                return False

            return request.user in task.executor.all() or request.user == task.owner
        return True

    def has_object_permission(self, request, view, obj):

        if not request.user.is_authenticated:
            return False

        if is_admin(request.user):
            return request.method in ["GET", "DELETE"]

        if request.method in ("PUT", "PATCH", "DELETE"):
            return request.user == obj.author
        return True
