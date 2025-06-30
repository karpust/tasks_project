from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.urls.base import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from authapp.serializers import (
    ChangePasswordSerializer,
    GenericResponseSerializer,
    GroupSerializer,
    LoginSerializer,
    RegisterSerializer,
    RepeatConfirmRegisterSerializer,
    ResetPasswordSerializer,
    UserSerializer,
)
from authapp.tasks import send_email_task
from authapp.utils import create_verification_link, generate_email_verification_token


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint that allows authapp to be viewed or edited."""

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """API endpoint that allows groups to be viewed or edited."""

    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [JWTAuthentication]


class RegisterAPIView(APIView):
    """Регистрации пользователя.

    Пользователь вводит имя, пароль, email-адрес. Если данные верны, получает на почту
    письмо, содержащее ссылку, для подтверждения регистрации.
    """

    # renderer_classes = [JSONRenderer, BrowsableAPIRenderer]
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        # auth=[],  # <-- это обнулит security для этого метода
        summary="Регистрация пользователя",
        description="Создает нового пользователя и отправляет ссылку "
        "на email для подтверждения регистрации.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="Успешная регистрация",
                response=GenericResponseSerializer,
            ),
            400: OpenApiResponse(
                description="Ошибка регистрации",
                response=GenericResponseSerializer,
            ),
        },
        examples=[
            OpenApiExample(
                "Пример ошибок",
                value={
                    "username": ["Ensure this field has at least 3 characters."],
                    "email": ["This field must be unique."],
                    "password": [
                        "This password is too short. It must contain "
                        "at least 8 characters."
                    ],
                },
                response_only=True,  # signal that example only applies to responses
                status_codes=[400],
            ),
            OpenApiExample(
                "Пример удачного выполнения",
                value={
                    "message": "Спасибо за регистрацию! На ваш email было отправлено "
                    "письмо-подтверждение. Пожалуйста, пройдите по ссылке "
                    "из письма."
                },
                response_only=True,  # signal that example only applies to responses
                status_codes=[201],
            ),
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            response_data = {
                "message": "Спасибо за регистрацию! "
                "На ваш email было отправлено письмо-подтверждение. "
                "Пожалуйста, пройдите по ссылке из письма."
            }

            # создаю токен, ссылку, отправляю письмо:
            token, created_at, lifetime = generate_email_verification_token(user)

            # в режиме отладки вывожу токен с ответом:
            if settings.DEBUG:
                response_data["token"] = token

            confirmation_link = create_verification_link(
                user, token=token, created_at=created_at, lifetime=lifetime
            )
            context = {
                "username": user.username,
                "confirmation_link": confirmation_link,
            }

            send_email_task.apply_async(
                args=["register_confirmation", context, user.email],
                queue="high_priority",
            )

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmRegisterAPIView(APIView):
    """Подтверждение регистрации.

    Пользователь переходит по ссылке из письма, Передавая серверу токен через параметры
    запроса. Сервер проверяет токен и при успехе активирует пользователя.
    """

    permission_classes = [permissions.AllowAny]
    queryset = User.objects.all()

    @extend_schema(
        tags=["Authentication"],
        summary="Подтверждение регистрации пользователя по токену",
        description=(
            "Используется для подтверждения регистрации пользователя. "
            "Ожидает токен подтверждения в query-параметрах запроса. "
            "Если токен действителен, активирует пользователя. "
            "Если токен отсутствует, недействителен или пользователь не найден"
            " — возвращает ошибку."
        ),
        # request = None, не нужно для GET и POST без тела
        parameters=[
            OpenApiParameter(
                name="token",
                type=str,
                location=OpenApiParameter.QUERY,
                description=(
                    "Токен подтверждения email, полученный на почту. "
                    "Если не указан - вернется ошибка."
                ),
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Успешное подтверждение регистрации",
                response=inline_serializer(
                    "ConfirmRegisterMessageSerializer",
                    fields={
                        "message": serializers.CharField(),
                    },
                ),
            ),
            400: OpenApiResponse(
                description="Ошибка подтверждения: токен отсутствует, недействителен "
                "или email уже подтвержден",
                response=inline_serializer(
                    "ConfirmRegisterErrorSerializer",
                    fields={
                        "detail": serializers.CharField(required=False),
                        "action": serializers.CharField(required=False),
                        "resend_url": serializers.CharField(
                            required=False,
                            help_text="Ссылка для подтвердения email",
                        ),
                    },
                ),
            ),
            404: OpenApiResponse(
                description="Пользователь не найден",
                response=inline_serializer(
                    "ConfirmRegisterError404Serializer",
                    fields={
                        "detail": serializers.CharField(),
                    },
                ),
            ),
        },
        examples=[
            OpenApiExample(
                "Ошибка: отсутствует токен",
                value={
                    "detail": "The link has invalid token.",
                    "action": "Request a new letter of confirmation "
                    "by the link below.",
                    "resend_url": "http://127.0.0.1:8000/api/auth/"
                    "repeat_confirm_register",
                },
                status_codes=[400],
            ),
            OpenApiExample(
                "Успешный запрос",
                value={
                    "message": "Email is successfully confirmed. "
                    "You can enter the system."
                },
                status_codes=[200],
            ),
        ],
    )
    def get(self, request):
        # check if token in request:
        token = request.query_params.get("token")
        if not token:
            return Response(
                {
                    "detail": "The token was expired or not provided",
                    "action": "Request a new letter of confirmation "
                    "by the link below.",
                    "resend_url": request.build_absolute_uri(
                        reverse("repeat_confirm_register")
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # check if token still in cache:
        token_data = cache.get(f"email_verification_token_{token}")
        cache.delete(f"email_verification_token_{token}")

        if not token_data:
            return Response(
                {
                    "detail": "The link has invalid token.",
                    "action": "Request a new letter of confirmation "
                    "by the link below.",
                    "resend_url": request.build_absolute_uri(
                        reverse("repeat_confirm_register")
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # get user from token:
        user_id = token_data["user_id"]

        # find this user in db:
        try:
            user = User.objects.get(id=user_id)

            if not user.is_active:
                user.is_active = True
                user.save()
                return Response(
                    {
                        "message": "Email is successfully confirmed. "
                        "You can enter the system."
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "detail": "Email has already been confirmed. "
                        "You can enter the system."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return Response(
                {"detail": "The user was not found. Please, repeat the registration."},
                status=status.HTTP_404_NOT_FOUND,
            )


class RepeatConfirmRegisterAPIView(APIView):
    """Запрос на повторное подтверждение email.

    Пользователь переходит по ссылке, вводит имя и пароль. Если введенные данные верны,
    на его почту отправляется письмо со ссылкой для подтвержения регистрации.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Запрос на повторное подтверждение email",
        description="Пользователь, не подтвердивший email с первого раза, "
        "переходит по ссылке, вводит имя и пароль, "
        "запрашивая повторное подтверждение регистрации. ",
        request=RepeatConfirmRegisterSerializer,
        responses={
            200: OpenApiResponse(
                description="Успешный запрос на повторное подтверждение",
                response=GenericResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Пример удачного выполнения",
                        value={
                            "message": "На ваш email было отправлено "
                            "письмо-подтверждение. "
                            "Пожалуйста, пройдите по ссылке из письма."
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Ошибка запроса на повторное подтверждение",
                response=GenericResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Неверные данные",
                        value={"detail": "Неверный логин или пароль"},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Подтверждение уже выполнено",
                        value={
                            "detail": "Email has already been confirmed. "
                            "You can enter the system."
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def post(self, request):

        serializer = RepeatConfirmRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        # проверка что юзер в бд и пароль совпадает:
        user = User.objects.filter(username=username).first()  # if not - user=None
        if not user or not check_password(
            password, user.password
        ):  # сравниваю с хешем пароля
            return Response(
                {"detail": "Неверный логин или пароль"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_active:
            return Response(
                {
                    "detail": "Email has already been confirmed. "
                    "You can enter the system."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )  # редиректнуть на логин

        response_data = {
            "message": "На ваш email было отправлено письмо-подтверждение. "
            "Пожалуйста, пройдите по ссылке из письма."
        }

        # создаю токен, ссылку, отправляю письмо:
        token, created_at, lifetime = generate_email_verification_token(user)

        # в режиме отладки вывожу токен с ответом:
        if settings.DEBUG:
            response_data["token"] = token

        confirmation_link = create_verification_link(
            user, token=token, created_at=created_at, lifetime=lifetime
        )
        context = {
            "username": user.username,
            "confirmation_link": confirmation_link,
        }

        # отправление письма-подтверждения со ссылкой:
        send_email_task.apply_async(
            args=["repeat_register_confirmation", context, user.email],
            queue="default",
        )
        return Response(response_data, status=status.HTTP_200_OK)


class LoginAPIView(APIView):
    """POST-запрос для аутентификации пользователя с помощью имени пользователя и
    пароля.

    При успешной аутентификации устанавливаются HttpOnly cookies с access и refresh
    токенами.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Логин пользователя",
        description=(
            "Принимает имя пользователя и пароль, "
            "аутентифицирует пользователя и устанавливает JWT access и "
            "refresh токены в HttpOnly cookies."
            "В режиме разработки (DEBUG=True) токены также возвращаются "
            "в теле ответа для тестирования."
        ),
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Успешная авторизация. В режиме DEBUG токены "
                "и в теле ответа.",
            ),
            400: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Неверные учетные данные или пользователь "
                "уже вошел в систему.",
            ),
        },
        examples=[
            OpenApiExample(
                "Успешный ответ",
                value={"message": "Login successful"},
                response_only=True,
                status_codes=[200],
            ),
            OpenApiExample(
                "Ошибка - неверные данные",
                value={"detail": "Invalid credentials"},
                response_only=True,
                status_codes=[400],
            ),
            OpenApiExample(
                "Ошибка - пользователь уже вошел",
                value={
                    "detail": "Вы уже вошли в систему. Выйдите перед повторным входом."
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        user = request.user

        # проверяем, авторизован ли пользователь, передал ли он токен:
        if user.is_authenticated:
            return Response(
                {"detail": "Вы уже вошли в систему. Выйдите перед повторным входом."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # если пользователь не залогинен, продолжаем аутентификацию:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.data["username"]
        password = serializer.data["password"]
        # проверяем есть ли такой юзер с паролем в системе:
        user = authenticate(request, username=username, password=password)
        if user:

            # генерация нового JWT-токена:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            response_data = {"message": "Login successful"}

            # в режиме отладки возвращаю токены в ответе:
            if settings.DEBUG:
                response_data.update(
                    {
                        "access": access_token,
                        "refresh": refresh_token,
                    }
                )

            response = Response(response_data)

            response.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=access_token,
                # expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                httponly=True,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
                max_age=15 * 60,  # 15 минут
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                # expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                httponly=True,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
                max_age=7 * 24 * 60 * 60,  # 7 дней
            )

            return response

        return Response(
            {"detail": "Invalid credentials"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LogoutAPIView(APIView):
    """Выход юзера и удаление его токенов из кук."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Выход пользователя",
        description="Удаляет JWT токены (access и refresh) из cookies и "
        "завершает сессию пользователя.",
        request=None,  # нет запроса с телом
        responses={
            200: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Успешный выход и удаление токенов",
            ),
            401: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Не переданы данные для аутентификации",
            ),
        },
        examples=[
            OpenApiExample(
                "Успешный выход",
                # description="Ответ при успешном удалении токенов из cookies.",
                value={"message": "Выход выполнен"},
                response_only=True,
                status_codes=[200],
            ),
            OpenApiExample(
                "Ошибка аутентификации",
                # description="Ответ при успешном удалении токенов из cookies.",
                value={"detail": "Authentication credentials were not provided."},
                response_only=True,
                status_codes=[401],
            ),
        ],
    )
    def post(self, request):
        response = Response({"message": "Выход выполнен"}, status=status.HTTP_200_OK)
        response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"])  # access-token
        response.delete_cookie("refresh_token")
        return response


class RefreshTokenAPIView(APIView):
    """Обновление access-токена.

    Клиент вызывает обработчик, переходя по ссылке для обновления access- токена. Когда
    access истёк, но refresh всё ещё действителен.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=None,
        summary="Обновление access-токена",
        description=(
            "Использует refresh-токен из cookies для генерации нового access-токена. "
            "Если refresh отсутствует или недействителен — возвращается 401. "
        ),
        responses={
            200: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Успешное обновление access-токена",
            ),
            401: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Ошибка refresh-токена",
            ),
        },
        examples=[
            OpenApiExample(
                "Успешный ответ",
                value={"message": "Токен обновлен"},
                response_only=True,
                status_codes=[200],
            ),
            OpenApiExample(
                "Ошибка: отсутствует токен обновления",
                value={"detail": "Токен обновления отсутствует"},
                response_only=True,
                status_codes=[401],
            ),
            OpenApiExample(
                "Ошибка: недействительный токен обновления",
                value={"detail": "Недействительный refresh-токен"},
                response_only=True,
                status_codes=[401],
            ),
        ],
    )
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            raise AuthenticationFailed("Токен обновления отсутствует")

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
        except Exception:
            raise AuthenticationFailed("Недействительный refresh-токен")

        response_data = {"message": "Токен обновлен"}

        if settings.DEBUG:
            response_data["access_token"] = access_token

        response = Response(response_data)
        response.set_cookie(
            key=settings.SIMPLE_JWT["AUTH_COOKIE"],
            value=access_token,
            httponly=True,
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            max_age=15 * 60,  # 15 минут
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            max_age=1 * 24 * 60 * 60,  # 1 day
        )

        return response


class ResetPasswordAPIView(APIView):
    """Сброс пароля.

    Пользователь вводит свой email для сброса пароля. По email определяется id
    пользователя. Создается одноразовый токен и uid(закодированный id пользователя),
    Токен и uid вшиваются в ссылку, которая посылается на email пользователя.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Запрос на сброс пароля",
        description="Этот эндпоинт генерирует уникальную ссылку для сброса пароля. "
        "Отправляется email с инструкциями.",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Успешный запрос, даже если email не существует",
            ),
            400: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Ошибка в поле email",
            ),
        },
        examples=[
            OpenApiExample(
                "Успешный запрос",
                value={
                    "message": "Если email существует, мы отправили ссылку "
                    "для сброса пароля."
                },
                response_only=True,
                status_codes=[200],
            ),
            OpenApiExample(
                "Успешный запрос: несуществующий email",
                # description="Email валидный по формату, но не существует в системе.
                # Ответ всё равно успешный.",
                value={
                    "message": "Если email существует, мы отправили ссылку "
                    "для сброса пароля."
                },
                response_only=True,
                status_codes=[200],
            ),
            OpenApiExample(
                "Ошибка: невалидный email",
                # description="Email валидный по формату, но не существует в системе.
                # Ответ всё равно успешный.",
                value={"email": ["Enter a valid email address."]},
                response_only=True,
                status_codes=[400],
            ),
        ],
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email).first()

        response_data = {
            "message": "Если email существует, мы отправили ссылку для сброса пароля."
        }

        if user:
            # создаю токен встроенными методами джанги:
            token = default_token_generator.make_token(
                user
            )  # создает одноразовый токен используя данные юзера
            uid = urlsafe_base64_encode(
                force_bytes(user.pk)
            )  # кодирует id юзера в Base64 (URL-безопасный формат)
            # чтобы передавать uid в URL без спецсимволов
            confirmation_link = (
                f"{settings.DOMAIN_NAME}"
                f"""{reverse("change_password",
                                              kwargs={"uid": uid, "token": token})}"""
            )

            if settings.DEBUG:
                # в режиме отладки возвращаю токен и uid в ответе
                response_data.update({"uid": uid, "token": token})
                # response_data["token"] = token

            context = {
                "username": user.username,
                "confirmation_link": confirmation_link,
            }
            # отправка email:
            send_email_task.apply_async(
                args=["reset_password_confirmation", context, email],
                queue="low_priority",
            )

        # отправляю одинаковый ответ, чтобы не раскрывать существование email:
        return Response(response_data, status=status.HTTP_200_OK)


class ChangePasswordAPIView(APIView):
    """Смена пароля.

    Пользователь переходит по ссылке из письма, передавая серверу uid и токен в
    параметрах запроса. Вводит пароль и подтверждение пароля. Сервер разбирает uid,
    токен, проверяет новый пароль. В случае успеха принимает изменения.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Смена пароля по ссылке восстановления",
        description="Изменяет пароль пользователя, если передан корректный UID "
        "и токен восстановления.",
        parameters=[
            OpenApiParameter(
                name="uid",
                description="UID пользователя в формате base64",
                type=str,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="token",
                description="Токен восстановления пароля",
                type=str,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=ChangePasswordSerializer,
        responses={
            400: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Недействительный токен или ссылка",
            ),
            401: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Данные для аутентификации не предоставлены",
            ),
            200: OpenApiResponse(
                response=GenericResponseSerializer,
                description="Пароль успешно изменен",
            ),
        },
        examples=[
            OpenApiExample(
                "Ошибка: недействительный токен",
                value={"detail": "Недействительный токен."},
                response_only=True,
                status_codes=[400],
            ),
            OpenApiExample(
                "Ошибка: недействительная ссылка",
                value={"detail": "Недействительная ссылка."},
                response_only=True,
                status_codes=[400],
            ),
            OpenApiExample(
                "Успешный запрос",
                value={"message": "Пароль успешно изменен."},
                response_only=True,
                status_codes=[200],
            ),
            OpenApiExample(
                "Ошибка аутентификации",
                value={"detail": "Authentication credentials were not provided."},
                response_only=True,
                status_codes=[401],
            ),
        ],
    )
    def post(self, request, uid, token):
        try:
            # находим юзера в бд по id:
            uid = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=uid)

            # генерит токен по данным юзера и сравнивает с токеном из запроса:
            if not default_token_generator.check_token(user, token):
                return Response(
                    {"detail": "Недействительный токен."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = ChangePasswordSerializer(data=request.data)
            if serializer.is_valid():
                user.set_password(serializer.validated_data["new_password"])
                user.save()
                return Response(
                    {"message": "Пароль успешно изменен."},
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Недействительная ссылка."},
                status=status.HTTP_400_BAD_REQUEST,
            )
