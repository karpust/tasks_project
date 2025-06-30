from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        #  вызывается перед каждым API-запросом, требующим аутентификации и
        #  ищет токен в куках а не в заголовке:
        token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        if not token:
            return None  # Нет токена — нет аутентификации

        validated_token = self.get_validated_token(token)
        return self.get_user(validated_token), validated_token
