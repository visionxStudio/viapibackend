from datetime import timedelta
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import PasswordResetOTP
from .serializers import EmailTokenObtainPairSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"id": user.id, "email": user.email, "name": user.first_name},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"


class PasswordResetOTPRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password_reset_request"

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        if not email:
            raise ValidationError({"email": ["Email is required."]})

        user = User.objects.filter(email__iexact=email).first()
        # Return success response even if user doesn't exist to avoid user enumeration.
        if user:
            PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
            otp = f"{randint(0, 999999):06d}"
            PasswordResetOTP.objects.create(
                user=user,
                otp=otp,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            try:
                connection = get_connection(fail_silently=False)
                connection.open()
                subject = "ViaMusic password reset code"
                context = {
                    "otp": otp,
                    "email": user.email,
                    "expiry_minutes": 10,
                }
                text_body = render_to_string(
                    "accounts/password_reset_otp_email.txt",
                    context,
                )
                html_body = render_to_string(
                    "accounts/password_reset_otp_email.html",
                    context,
                )
                email = EmailMultiAlternatives(
                    subject="Your Backup API password reset OTP",
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                    connection=connection,
                )
                email.subject = subject
                email.attach_alternative(html_body, "text/html")
                email.send(fail_silently=False)
                connection.close()
            except Exception as exc:
                smtp_debug = (
                    f"host={settings.EMAIL_HOST or 'empty'}, "
                    f"port={settings.EMAIL_PORT}, "
                    f"tls={settings.EMAIL_USE_TLS}, "
                    f"ssl={settings.EMAIL_USE_SSL}, "
                    f"user_set={'yes' if settings.EMAIL_HOST_USER else 'no'}"
                )
                raise ValidationError(
                    {
                        "detail": (
                            "Failed to send OTP email. "
                            f"SMTP[{smtp_debug}] Error: {exc}"
                        )
                    }
                ) from exc

        return Response(
            {"detail": "If this email is registered, an OTP has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetOTPConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password_reset_confirm"

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        otp = str(request.data.get("otp", "")).strip()
        new_password = str(request.data.get("password", ""))

        if not email or not otp or not new_password:
            raise ValidationError(
                {"detail": "email, otp and password are required."}
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError({"detail": "Invalid OTP or email."})

        otp_entry = (
            PasswordResetOTP.objects.filter(user=user, otp=otp, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp_entry or not otp_entry.is_valid():
            raise ValidationError({"detail": "Invalid or expired OTP."})

        if len(new_password) < 8:
            raise ValidationError({"password": ["Password must be at least 8 characters long."]})
        user.set_password(new_password)
        user.save(update_fields=["password"])

        otp_entry.is_used = True
        otp_entry.save(update_fields=["is_used"])

        return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)
