from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    PasswordResetOTPConfirmView,
    PasswordResetOTPRequestView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "password-reset/request-otp/",
        PasswordResetOTPRequestView.as_view(),
        name="password_reset_request_otp",
    ),
    path(
        "password-reset/confirm-otp/",
        PasswordResetOTPConfirmView.as_view(),
        name="password_reset_confirm_otp",
    ),
]
