import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from django.db import close_old_connections
from asgiref.sync import sync_to_async
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Налаштування Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bd.settings')

import django

django.setup()
from bd_random_code.models import RandomCode
from django.contrib.auth.models import User
from django.conf import settings

# Конфіг бота
from config import DataTg

bot = Bot(token=DataTg.telegram_token)
dp = Dispatcher(storage=MemoryStorage())

# Константи
BAN_TIME_SECONDS = 20  # Час бана між запросами кодів


# Стани для FSM
class AdminStates(StatesGroup):
    waiting_for_start = State()
    waiting_for_end = State()


# Словник для зберігання часу останнього запиту коду
last_request_time = {}


class CodeManager:
    @staticmethod
    @sync_to_async
    def get_unused_code():
        """Отримати невикористаний код"""
        close_old_connections()
        return RandomCode.objects.filter(bool_field=False).order_by('?').first()

    @staticmethod
    @sync_to_async
    def count_unused_codes():
        """Підрахувати кількість невикористаних кодів"""
        close_old_connections()
        return RandomCode.objects.filter(bool_field=False).count()

    @staticmethod
    @sync_to_async
    def generate_codes_in_range(start, end):
        """Згенерувати коди в діапазоні"""
        close_old_connections()
        created = 0
        for code in range(start, end + 1):
            if not RandomCode.objects.filter(int_field=code).exists():
                RandomCode.objects.create(int_field=code, bool_field=False)
                created += 1
        return created

    @staticmethod
    @sync_to_async
    def mark_code_used(code_obj, user_id, username):
        """Позначити код як використаний"""
        close_old_connections()
        user, _ = User.objects.get_or_create(
            username=str(user_id),
            defaults={'first_name': username}
        )
        code_obj.bool_field = True
        code_obj.user = user
        code_obj.username = username
        code_obj.save()
        return code_obj

    @staticmethod
    @sync_to_async
    def get_admins():
        """Отримати список адміністраторів"""
        close_old_connections()
        return list(User.objects.filter(is_staff=True).values_list('username', flat=True))


@sync_to_async
def is_admin(user: types.User) -> bool:
    """Перевірити, чи є користувач адміністратором"""
    close_old_connections()
    if not user.username:
        return False
    print(user.username)

    return User.objects.filter(username=user.username, is_active=True).exists()


def get_user_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Отримати клавіатуру відповідно до статусу користувача"""
    buttons = [[KeyboardButton(text="🎯 Отримати код")]]
    if is_admin:
        buttons.extend([
            [KeyboardButton(text="📊 Кількість вільних кодів")],
            [KeyboardButton(text="➕ Згенерувати коди")]
        ])
    buttons.append([KeyboardButton(text="ℹ️ Допомога")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    admin_status = await is_admin(message.from_user)
    keyboard = get_user_keyboard(admin_status)
    await message.answer(
        "👋 Вітаю! Натисніть кнопку, щоб отримати унікальний код.",
        reply_markup=keyboard
    )


@dp.message(F.text == "🎯 Отримати код")
async def send_code(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.full_name

    # Перевірка бана
    now = datetime.now()
    last_time = last_request_time.get(user_id)
    if last_time and (now - last_time) < timedelta(seconds=BAN_TIME_SECONDS):
        remaining = BAN_TIME_SECONDS - (now - last_time).seconds
        await message.answer(f"⏳ Ви можете отримати наступний код через {remaining} секунд")
        return

    try:
        code_obj = await CodeManager.get_unused_code()

        if not code_obj:
            # Повідомляємо адміністраторів про закінчення кодів
            admins = await CodeManager.get_admins()
            for admin_username in admins:
                try:

                    await bot.send_message(
                        chat_id=1276640872,
                        text=f"⚠️ Увага! Закінчилися коди для видачі. Користувач {username} не отримав код."
                    )
                except Exception as e:
                    print(f"Не вдалося повідомити адміна {admin_username}: {e}")

            await message.answer("😔 Наразі всі коди вичерпано. Адміністратор вже повідомлений.")
            return

        await CodeManager.mark_code_used(code_obj, user_id, username)

        response = (
            f"🔢 Ваш код: <code>{code_obj.int_field}</code>\n"
            f"💁 Власник: {username}\n"
            f"📦 Отримано з бази даних"
        )
        await message.answer(response, parse_mode='HTML')

        # Оновлюємо час останнього запиту
        last_request_time[user_id] = now

    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")


@dp.message(F.text == "📊 Кількість вільних кодів")
async def show_free_codes_count(message: types.Message):
    if not await is_admin(message.from_user):
        await message.answer("⛔ У вас немає прав доступу до цієї команди.")
        return

    try:
        count = await CodeManager.count_unused_codes()
        await message.answer(f"📊 Вільних кодів у базі: {count}")
    except Exception as e:
        await message.answer(f"⚠️ Помилка: {str(e)}")


@dp.message(F.text == "➕ Згенерувати коди")
async def start_generate_codes(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user):
        await message.answer("⛔ У вас немає прав доступу до цієї команди.")
        return

    await message.answer("🔢 Введіть початкове число діапазону:")
    await state.set_state(AdminStates.waiting_for_start)


@dp.message(AdminStates.waiting_for_start)
async def process_start_number(message: types.Message, state: FSMContext):
    try:
        start = int(message.text)
        await state.update_data(start=start)
        await message.answer("🔢 Введіть кінцеве число діапазону:")
        await state.set_state(AdminStates.waiting_for_end)
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне число.")


@dp.message(AdminStates.waiting_for_end)
async def process_end_number(message: types.Message, state: FSMContext):
    try:
        end = int(message.text)
        data = await state.get_data()
        start = data['start']

        if start > end:
            await message.answer("❌ Початкове число повинно бути менше або дорівнювати кінцевому.")
            return

        await message.answer(f"⏳ Генерую коди у діапазоні {start}-{end}...")
        created = await CodeManager.generate_codes_in_range(start, end)
        await message.answer(f"✅ Згенеровано {created} нових кодів у діапазоні {start}-{end}.")

        await state.clear()
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне число.")


@dp.message(F.text == "ℹ️ Допомога")
async def show_help(message: types.Message):
    admin_status = await is_admin(message.from_user)
    help_text = (
        f"ℹ️ Інформація:\n\n"
        f"• Натисніть 'Отримати код' для отримання коду\n"
        f"• Кожен код можна використати лише один раз\n"
        f"• Між запитами кодів пауза {BAN_TIME_SECONDS} секунд\n"
        f"• При проблемах звертайтеся до адміністратора"
    )

    if admin_status:
        help_text += (
            "\n\n⚙️ Адмін-команди:\n"
            "• 'Кількість вільних кодів' - перевірити доступні коди\n"
            "• 'Згенерувати коди' - створити нові коди у вказаному діапазоні"
        )

    await message.answer(help_text)


async def start_bot():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot())