from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class RandomCode(models.Model):
    bool_field = models.BooleanField(default=False, verbose_name="Активний")
    int_field = models.IntegerField(default=0, verbose_name="Код")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Користувач"
    )
    username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Ім'я користувача"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата створення"
    )

    class Meta:
        verbose_name = "Випадковий код"
        verbose_name_plural = "Випадкові коди"

    def __str__(self):
        return f"Код {self.int_field} ({self.username or 'немає користувача'})"

class TelegramAdmin(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_admin',
        verbose_name="Користувач"
    )
    telegram_username = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Telegram username"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення"
    )

    class Meta:
        verbose_name = "Telegram адміністратор"
        verbose_name_plural = "Telegram адміністратори"

    def __str__(self):
        return f"{self.user.username} ({self.telegram_username})"