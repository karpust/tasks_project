from django.urls import path

# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from authapp.views import (
    ChangePasswordAPIView,
    ConfirmRegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    RefreshTokenAPIView,
    RegisterAPIView,
    RepeatConfirmRegisterAPIView,
    ResetPasswordAPIView,
)

urlpatterns = [
    # path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path(
        "confirm_register/",
        ConfirmRegisterAPIView.as_view(),
        name="confirm_register",
    ),
    path(
        "repeat_confirm_register",
        RepeatConfirmRegisterAPIView.as_view(),
        name="repeat_confirm_register",
    ),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh-token/", RefreshTokenAPIView.as_view(), name="refresh_token"),
    path(
        "reset_password/",
        ResetPasswordAPIView.as_view(),
        name="reset_password",
    ),
    path(
        "change_password/<str:uid>/<str:token>/",
        ChangePasswordAPIView.as_view(),
        name="change_password",
    ),
]
