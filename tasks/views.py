from django.db.models import DurationField, ExpressionWrapper, F
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from tasks.models import Category, Comment, Tag, Task
from tasks.serializers import (
    CategorySerializer,
    CommentSerializer,
    TagSerializer,
    TaskSerializer,
)

from .filters import TaskFilter
from .permissions import CommentPermission, TaskPermission


@extend_schema_view(
    list=extend_schema(
        summary="Получение списка задач",
        description=(
            "Возвращает список задач с возможностью **фильтрации** и "
            "**сортировки**.\n\n"
            "### Фильтрация:\n"
            "- `status_display`: статус задачи (`to_do`, `in_progress`, `done`)\n"
            "- `priority`: числовой приоритет (чем меньше — тем важнее)\n"
            "- `deadline_before`, `deadline_after`: дедлайн до/после указанной даты\n"
            "- `executor`: имя исполнителя (можно несколько)\n"
            "- `owner`: имя автора задачи\n"
            "- `tags`: название тега (можно несколько)\n"
            "- `search`: поик по частичному совпадению (по заголовку, "
            "описанию и т.п.)\n\n"
            "### Сортировка (`?ordering=`):\n"
            "- `urgency`: задачи с ближайшими дедлайнами первыми\n"
            "- `-urgency`: задачи с отдалёнными дедлайнами первыми\n"
            "- `priority`, `deadline`, `status`\n\n"
            "Можно указывать несколько полей: `?ordering=priority,-urgency,"
            "status,deadline`\n\n"
            "### Примеры:\n"
            "- `/api/tasks/?ordering=priority,-urgency`\n"
            "- `/api/tasks/?status=todo&ordering=-deadline`"
        ),
        parameters=[
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач по названию категории.",
            ),
            OpenApiParameter(
                name="tags",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач по названию тэга.",
                many=True,  # список строк
            ),
            OpenApiParameter(
                name="executor",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач по имени исполнителя.",
                many=True,  # список значений
            ),
            OpenApiParameter(
                name="owner",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач по имени создателя.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Сортировка задач по полям: `urgency`, `priority`, "
                "`status`, `deadline`. С возможностью комбинировать.",
            ),
            OpenApiParameter(
                name="status_display",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=[
                    "to_do",
                    "in_progress",
                    "done",
                ],  # для выпадающего списка
                required=False,
                description="Фильтрация по статусу выполнения задачи "
                "(`to_do`, `in_progress`, `done`).",
            ),
            OpenApiParameter(
                name="priority_display",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=["low", "medium", "high"],
                required=False,
                description="Фильтрация по приоритету задачи "
                "(`low`, `medium`, `high`).",
            ),
            OpenApiParameter(
                name="deadline_before",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач с дедлайном **до** выбранной даты.",
            ),
            OpenApiParameter(
                name="deadline_after",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач с дедлайном **после** выбранной даты.",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Фильтрация задач по частичному совпадению в названии, "
                "описании, комментарии, теге или категории.",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Получение задачи по ID",
        description="Возвращает задачу по её идентификатору.",
    ),
    create=extend_schema(
        summary="Создание задачи",
        description="Создаёт новую задачу. Требует данные по заголовку, "
        "описанию, дедлайну и приоритету.",
    ),
    update=extend_schema(
        summary="Обновление задачи",
        description="Полностью обновляет задачу (все поля перезаписываются).",
    ),
    partial_update=extend_schema(
        summary="Частичное обновление задачи",
        description="Обновляет только переданные поля задачи.",
    ),
    destroy=extend_schema(
        summary="Удаление задачи", description="Удаляет задачу по ID."
    ),
)
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ["deadline", "urgency", "priority", "status"]
    ordering = ["urgency"]  # по умолчанию — срочные сверху
    # /api/tasks/?ordering=urgency	срочные первыми
    # /api/tasks/?ordering=-urgency	 cначала задачи с дальним дедлайном
    # /api/tasks/?ordering=priority,-urgency  cначала по приоритету, потом по срочности

    def get_queryset(self):
        return Task.objects.annotate(
            urgency=ExpressionWrapper(
                F("deadline") - now(), output_field=DurationField()
            )
        )


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [CommentPermission]

    def get_queryset(self):
        # фильтрую комментарии по задаче из URL:
        return Comment.objects.filter(task_id=self.kwargs["task_pk"])
        # kwargs-словарь параметров URL, извлечённых из маршрута
        # task_pk-ключ кот исп drf-nested-routers на основе lookup='task' урла
        # поле task — это ForeignKey, а в базе оно хранится как task_id

    def perform_create(self, serializer):
        # автоматически привязываю задачу и автора:
        # task = Task.objects.get(id=self.kwargs['task_pk'])
        task = getattr(self, "task", None) or Task.objects.get(
            id=self.kwargs["task_pk"]
        )
        serializer.save(task=task)  # author=self.request.user,


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [TaskPermission]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [TaskPermission]
