from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import RandomCode, TelegramAdmin


# Додаємо модель TelegramAdmin до адмінки
class TelegramAdminInline(admin.StackedInline):
    model = TelegramAdmin
    can_delete = False
    verbose_name_plural = 'Telegram адміністратори'
    fk_name = 'user'


# Кастомізований UserAdmin для відображення TelegramAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (TelegramAdminInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_telegram_admin')
    list_select_related = ('telegram_admin',)

    def is_telegram_admin(self, instance):
        return hasattr(instance, 'telegram_admin')

    is_telegram_admin.boolean = True
    is_telegram_admin.short_description = 'Telegram адмін'


# Налаштування адмінки для RandomCode
class RandomCodeAdmin(admin.ModelAdmin):
    list_display = ('int_field', 'username', 'bool_field', 'created_at')
    list_filter = ('bool_field', 'created_at')
    search_fields = ('int_field', 'username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': ('int_field', 'bool_field', 'user', 'username')
        }),
        ('Додаткова інформація', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# Реєстрація моделей
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(RandomCode, RandomCodeAdmin)
admin.site.register(TelegramAdmin)