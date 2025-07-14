import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters import BaseInFilter, CharFilter

from .models import Task, TaskPriority, TaskStatus

User = get_user_model()


class CharInFilter(BaseInFilter, CharFilter):
    """Фильтр, который обрабатывает список строк."""

    pass


class TaskFilter(django_filters.FilterSet):
    """Фильтрация по status_display(строке),

    а сортировка по status(числу) - для удобства и функциональности.
    """

    # custom:
    deadline_after = django_filters.DateTimeFilter(
        field_name="deadline", lookup_expr="gte"
    )
    deadline_before = django_filters.DateTimeFilter(
        field_name="deadline", lookup_expr="lte"
    )
    # GET /api/tasks/?deadline_after=2025-04-10T00:00:00&deadline_before=2025-04-...
    owner = django_filters.CharFilter(
        field_name="owner__username", lookup_expr="iexact"
    )
    # GET /api/tasks/?owner__username=johndoe
    executor = django_filters.CharFilter(
        field_name="executor__username", lookup_expr="iexact"
    )
    category = django_filters.CharFilter(
        field_name="category__name", lookup_expr="iexact"
    )
    tags = CharInFilter(field_name="tags__name", lookup_expr="in")
    search = django_filters.CharFilter(method="filter_search", lookup_expr="icontains")
    status_display = django_filters.ChoiceFilter(
        method="filter_by_status_display",
        choices=[(label, label) for _, label in TaskStatus.choices],
    )
    # ==> [('to_do', 'to_do'),('in_progress', 'in_progress'),('done', 'done')]
    # ==> ChoiceFilter ==> filter_by_status_display
    # value_из_урла = value_из_выпадающего_списка, чтобы не путаться
    priority_display = django_filters.ChoiceFilter(
        method="filter_by_prioriry_display",
        choices=[(label, label) for _, label in TaskPriority.choices],
    )

    class Meta:
        model = Task
        fields = [
            "status_display",
            "priority_display",
            "deadline_after",
            "deadline_before",
            "owner",
            "executor",
            "tags",
            "search",
            "category",
        ]  # here exact or custom

    def filter_search(self, queryset, name, value):  # name	- filter name "search"
        """Поиск слова по разным полям."""
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__text__icontains=value)
            | Q(tags__name__icontains=value)
            | Q(category__name__icontains=value)
        ).distinct()

    def filter_by_field_display(self, queryset, name, value, field_name, choices):
        """Метод для использования числовых и строковых значений статуса.

        при фильтрации - пользователь видит строку для удобства,
        а в базу передается число для быстроты работы.
        при сортировке - число необходимо для сравнения.

        :param queryset:
        :param name: имя фильтра, которое передается в URL-параметре(status_display),
        :param value:
        :param field_name: поле модели, по которому происходит фильтрация(status).
        :param choices:
        :return:
        """
        # формирую словарь для поиска значений:
        lookup = {
            label: val for val, label in choices
        }  # ==> {'to_do': 1,'in_progress': 2,'done': 3}
        # извлекаю значение для фильтрации:
        val = lookup.get(value)  # 'in_progress' ==> 2
        if val is not None:  # такого пока нет, но вдруг допишу чего
            return queryset.filter(**{field_name: val})  # filter by status=2
        return queryset.none()  # если значение не распознано, вернуть пустой queryset

    def filter_by_status_display(self, queryset, name, value):
        return self.filter_by_field_display(
            queryset, name, value, "status", TaskStatus.choices
        )

    def filter_by_prioriry_display(self, queryset, name, value):
        return self.filter_by_field_display(
            queryset, name, value, "priority", TaskPriority.choices
        )
