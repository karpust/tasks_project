from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Comment, Tag, Task, TaskPriority, TaskStatus

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для модели категорий."""

    class Meta:
        model = Category
        fields = ["id", "name"]


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели тэгов."""

    class Meta:
        model = Tag
        fields = ["id", "name"]


@extend_schema_field(OpenApiTypes.STR)
class TagListField(serializers.ListField):
    def to_representation(self, instance):
        return [tag.name for tag in instance.all()]  # instance.all() - все теги задачи

    def create_or_get_tags(self, tag_names):
        """Return list of tag objects."""
        tags = []
        for tag_name in tag_names:
            tag_name = tag_name.strip().capitalize()
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)
        return tags  # дубликаты удалятся при task.tags.set(tags)


@extend_schema_field(OpenApiTypes.STR)
class LabelChoiceField(serializers.ChoiceField):
    def to_representation(self, value):
        # value => label
        # 1 => "to_do
        return self.choices[value]

    def to_internal_value(self, data):
        # label => value
        # "to_do" => 1
        for key, label in self.choices.items():
            if label == data:
                return key
        self.fail("invalid_choice", input=data)


class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор для модели задач."""

    owner = serializers.HiddenField(
        default=serializers.CurrentUserDefault(), help_text="Создатель задачи"
    )
    tags = TagListField(
        required=False,
        help_text="Список тэгов. Принимает массив строк, например: ['API', 'DRF']",
    )
    category = serializers.CharField(required=False, help_text="Название категории")
    # status_display = serializers.CharField(source='get_status_display',
    # read_only=True)  # get field from method
    # говорю не брать напрямую priority, а вызвать obj.get_priority_display()
    # и положить результат в priority_display.
    # priority_display = serializers.CharField(source='get_priority_display',
    # read_only=True)
    status = LabelChoiceField(
        choices=TaskStatus.choices,
        help_text="Статус задачи, допустимые значения: to_do, in_progress, done",
    )
    priority = LabelChoiceField(
        choices=TaskPriority.choices,
        help_text="Приоритет задачи, допустимые значения: low, medium, high",
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "deadline",
            "owner",
            "executor",
            "category",
            "tags",
            "priority",
            "status",
        ]
        extra_kwargs = {
            "title": {"help_text": "Название задачи"},
            "description": {"help_text": "Описание задачи"},
            "deadline": {"help_text": "Срок выполнения"},
            "executor": {"help_text": "Список исполнителей задачи"},
        }

    def create_or_get_category(self, category_name):
        category_name = category_name.strip()  # убираю пробелы, исключая дублирование
        category, _ = Category.objects.get_or_create(name=category_name)
        return category

    def create(self, validated_data):
        category_data = validated_data.pop("category", None)
        tags_data = validated_data.pop("tags", [])
        executor = validated_data.pop("executor")

        category = self.create_or_get_category(category_data) if category_data else None
        tags = TagListField().create_or_get_tags(tags_data)

        task = Task.objects.create(category=category, **validated_data)
        task.executor.set(executor)
        task.tags.set(tags)
        return task

    def update(self, instance, validated_data):
        category_data = validated_data.pop("category", None)
        tags_data = validated_data.pop("tags", [])
        validated_data.pop("owner", None)  # not change owner if update

        if category_data:
            category = self.create_or_get_category(category_data)
            instance.category = category

        if tags_data:
            tags = TagListField().create_or_get_tags(tags_data)
            instance.tags.set(tags)
        # update remaining fields:
        # for attr, value in validated_data.items():
        #     setattr(instance, attr, value)
        # instance.save()
        # return instance
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.category:
            rep["category"] = instance.category.name
        return rep


class CommentSerializer(serializers.ModelSerializer):
    """Сериализатор для модели комментариев."""

    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(), help_text="Автор комментария"
    )

    class Meta:
        model = Comment
        fields = ["id", "task", "author", "text", "created_at"]
        read_only_fields = ["task", "created_at"]
