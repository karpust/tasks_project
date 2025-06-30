from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

allowed_groups = ["user", "admin", "manager"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class UserSerializer(serializers.HyperlinkedModelSerializer):
    # groups = serializers.SlugRelatedField(
    #     slug_field='name',
    #     queryset=Group.objects.filter(name__in=allowed_groups),
    # защита от ляпа админа
    #     required=False,
    # )

    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]

    # def create(self, validated_data):
    #     user = super().create(validated_data)
    #     default_group, _ = Group.objects.get_or_create(name='user')
    #     user.groups.set([default_group])
    #     return user
    #
    # def update(self, instance, validated_data):
    #     """
    #     admin can change user's group
    #     """
    #     group = validated_data.pop('groups', None)
    #     if group:
    #         instance.groups.set([group])
    #     instance.save(update_fields=['groups'])
    #     return instance


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя и отправления ссылки подтверждения на
    email."""

    # полностью переопределить поле:
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
        help_text="Email",
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]
        # изменить поле:
        extra_kwargs = {
            "password": {
                "write_only": True,
            },
            "username": {
                "min_length": 3,
                "max_length": 30,
            },
        }

    def validate_password(self, value):
        # применяет все валидаторы, из AUTH_PASSWORD_VALIDATORS
        # нет доп логики, можно было validators=[validate_password]
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def create(self, validated_data):
        # вызывается при создании нового пользователя(POST-запрос в API).
        # принимает данные, которые были авт проверены ModelSerializer
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],  # автоматом хешируется при create_user
            is_active=False,  # user is not active before confirm email
        )
        default_group, _ = Group.objects.get_or_create(name="user")
        user.groups.set([default_group])
        return user


class RepeatConfirmRegisterSerializer(serializers.Serializer):
    """Сериализатор для повторного запроса ссылки на подтверждение регистрации."""

    username = serializers.CharField(help_text="Имя пользователя")
    password = serializers.CharField(help_text="Пароль")


class LoginSerializer(serializers.Serializer):
    """Сериализатор для логина пользователя."""

    username = serializers.CharField(help_text="Имя пользователя")
    password = serializers.CharField(help_text="Пароль")


class ResetPasswordSerializer(serializers.Serializer):
    """Сериализатор для запроса на email ссылки на смену пароля."""

    email = serializers.EmailField(help_text="Email для сброса пароля")


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля по ссылке восстановления."""

    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        help_text="Новый пароль",
    )
    confirm_password = serializers.CharField(
        required=True, write_only=True, help_text="Подтверждение нового пароля"
    )

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"new_password": "Пароли не совпадают."})
        return data


class GenericResponseSerializer(serializers.Serializer):
    message = serializers.CharField(
        required=False, help_text="Успешное выполнение запроса"
    )
    detail = serializers.CharField(
        required=False, help_text="Ошибка выполнения запроса"
    )
    action = serializers.CharField(required=False, help_text="Действие пользователя")

    username = serializers.ListField(child=serializers.EmailField(), required=False)
    email = serializers.ListField(child=serializers.EmailField(), required=False)
    password = serializers.ListField(
        child=serializers.EmailField(), required=False, write_only=True
    )
