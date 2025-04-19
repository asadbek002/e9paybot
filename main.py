from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import pandas as pd
import re
import os
import asyncio
from datetime import datetime
import shutil

# Настройки
BOT_TOKEN = "7365174406:AAGBwSuWFIUDSXoFCbw1r5gpmdrBU7txXis"
GROUP_ID = -4535050669
ADMIN_ID = 5897615611
user_sessions = {}

TEXTS = {
    "start": {
        "uz": "👋 Iltimos, E9pay tizimida ro'yxatdan o'tgan telefon raqamingizni kiriting.",
        "ru": "👋 Пожалуйста, введите номер телефона, зарегистрированный в системе E9pay.",
        "en": "👋 Please enter the phone number registered in the E9pay system."
    },
    "passport_request": {
        "uz": "🛬 Iltimos, xorijiy pasportingiz suratini yuboring.",
        "ru": "🛬 Пожалуйста, отправьте фото вашего заграничного паспорта.",
        "en": "🛬 Please send a photo of your international passport."
    },
    "ask_id_card": {
        "uz": "🆔 Agar sizda koreyscha ID karta bo‘lsa — uni ham yuboring. Aks holda, quyidagi tugmani bosing.",
        "ru": "🆔 Если у вас есть корейская ID-карта — отправьте её. В противном случае нажмите на кнопку ниже.",
        "en": "🆔 If you have a Korean ID card — send it. Otherwise, press the button below."
    },
    "start_button": {
        "uz": "🟢 Boshlash",
        "ru": "🟢 Старт",
        "en": "🟢 Start"
    }
}

PHONE_REGEX = re.compile(r"^010\d{8}$")


def log_action(text):
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")


def save_to_csv(session, user):
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": user.full_name,
        "phone": session["phone"],
        "user_id": user.id
    }
    df = pd.DataFrame([row])
    df.to_csv("data.csv", mode="a", header=not os.path.exists(
        "data.csv"), index=False)

# Старт


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    telegram_lang = update.effective_user.language_code or "uz"
    lang = "uz"
    if telegram_lang.startswith("ru"):
        lang = "ru"
    elif telegram_lang.startswith("en"):
        lang = "en"

    user_sessions[user_id] = {"lang": lang}
    label = TEXTS["start_button"][lang]

    await update.message.reply_text(
        {
            "uz": f"{label} uchun tugmani bosing:",
            "ru": f"Нажмите кнопку {label}:",
            "en": f"Press the {label} button:"
        }[lang],
        reply_markup=ReplyKeyboardMarkup(
            [[label]],  # Кнопка на нужном языке
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )


# Обработка текста


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type in ["group", "supergroup"]:
        return
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    session = user_sessions.get(user_id)
    if not session:
        session = {"lang": "uz"}
        user_sessions[user_id] = session
    lang = session.get("lang", "uz")

    # Обработка нажатия на кнопку старт
    if text == TEXTS["start_button"][lang]:
        await update.message.reply_text(TEXTS["start"][lang])
        return

    if "start" in text.lower():  # на всякий случай
        await update.message.reply_text(TEXTS["start"][lang])
        return

    if not PHONE_REGEX.match(text):
        await update.message.reply_text({
            "uz": "❌ Telefon raqami noto'g'ri. Format: 010XXXXXXXX",
            "ru": "❌ Неверный формат номера. Пример: 010XXXXXXXX",
            "en": "❌ Invalid phone number format. Use: 010XXXXXXXX"
        }[lang])
        return

    session["phone"] = text
    await update.message.reply_text(TEXTS["passport_request"][lang], reply_markup=ReplyKeyboardRemove())


# Обработка фото


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Игнорировать сообщения, если они из группы
    if update.message.chat.type in ["group", "supergroup"]:
        return

    user_id = update.message.from_user.id
    photo = update.message.photo[-1]
    session = user_sessions.get(user_id)
    lang = session.get("lang", "uz") if session else "uz"

    if not session or "phone" not in session:
        await update.message.reply_text(TEXTS["start"][lang])
        return

    # 2. Принято фото — начинаем обработку
    await update.message.reply_text({
        "uz": "⏳ Rasm qabul qilinmoqda...",
        "ru": "⏳ Фото обрабатывается...",
        "en": "⏳ Processing your image..."
    }[lang])

    # 3. Через 5 секунд — предупреждение о медленном интернете
    await asyncio.sleep(5)
    await update.message.reply_text({
        "uz": "⚠️ Internetingiz sekin bo‘lishi mumkin. Kuting yoki qayta yuboring.",
        "ru": "⚠️ Возможно, у вас медленный интернет. Подождите или отправьте заново.",
        "en": "⚠️ Your internet might be slow. Please wait or resend the photo."
    }[lang])

    # 4. Дополнительная пауза (эмуляция обработки)
    await asyncio.sleep(2)

    # 5. Сохраняем фото в сессию
    if "passport_photo" not in session:
        session["passport_photo"] = photo.file_id
        await update.message.reply_text(TEXTS["ask_id_card"][lang],
                                        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Davom etish / Продолжить / Continue", callback_data="submit")]]))
    elif "id_card_photo" not in session:
        session["id_card_photo"] = photo.file_id
        await update.message.reply_text({
            "uz": "✅ ID karta qabul qilindi.",
            "ru": "✅ ID-карта принята.",
            "en": "✅ ID card received."
        }[lang], reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Davom etish / Продолжить / Continue", callback_data="submit")]]))

# Завершение подачи


async def handle_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = user_sessions.get(user_id)
    lang = session.get("lang", "uz") if session else "uz"

    if not session or "passport_photo" not in session:
        await query.edit_message_text("❗ Please upload your passport first.")
        return

    # Получаем информацию о пользователе
    user = query.from_user
    full_name = user.full_name
    username = f"@{user.username}" if user.username else "—"

    # Формируем сообщение для группы
    caption = (
        f"📞 Telefon: {session['phone']}\n"
        f"👤 Foydalanuvchi: {full_name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user.id}"
    )

    await context.bot.send_message(chat_id=GROUP_ID, text=caption)
    await context.bot.send_photo(chat_id=GROUP_ID, photo=session["passport_photo"])
    if "id_card_photo" in session:
        await context.bot.send_photo(chat_id=GROUP_ID, photo=session["id_card_photo"])

    await query.edit_message_text({
        "uz": "✅ Ma'lumotlar yuborildi. Rahmat!",
        "ru": "✅ Данные отправлены. Спасибо!",
        "en": "✅ Your data has been submitted. Thank you!"
    }[lang])

    # Сохраняем в лог и CSV
    log_action(f"{full_name} | {session['phone']} | {user.id} | {username}")
    save_to_csv(session, user)

    # Сброс сессии
    user_sessions[user_id] = {"lang": lang}
    label = TEXTS["start_button"][lang]
    await context.bot.send_message(
        chat_id=user_id,
        text={
            "uz": "🟢 Yangi ariza topshirish uchun tugmani bosing:",
            "ru": "🟢 Чтобы подать новую заявку, нажмите кнопку:",
            "en": "🟢 To submit a new request, press the button:"
        }[lang],
        reply_markup=ReplyKeyboardMarkup(
            [[f"{label} / Start / Старт"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return
    buttons = [
        [InlineKeyboardButton("📂 Logni ko‘rish", callback_data="view_log")],
        [InlineKeyboardButton("🧹 Logni tozalash", callback_data="clear_log")],
        [InlineKeyboardButton(
            "📋 Arizalar soni", callback_data="count_entries")]
    ]
    await update.message.reply_text("🔧 Admin panel:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Sizda ruxsat yo'q.")
        return

    if query.data == "view_log":
        try:
            with open("logs.txt", "r", encoding="utf-8") as f:
                content = f.read()
                await query.message.reply_text(f"📂 Log mazmuni:\n{content[-4000:]}")
        except:
            await query.message.reply_text("❌ Logni o'qib bo'lmadi.")
    elif query.data == "clear_log":
        open("logs.txt", "w").close()
        await query.message.reply_text("🧹 Log tozalandi.")
    elif query.data == "count_entries":
        try:
            with open("logs.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                await query.message.reply_text(f"📋 Jami arizalar: {len(lines)} ta")
        except:
            await query.message.reply_text("❌ Hisoblab bo‘lmadi.")

# Команды: /filter_logs, /find, /archive_logs, /msg


async def filter_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Нет доступа.")
    if not context.args:
        return await update.message.reply_text("❗ Укажите дату в формате YYYY-MM-DD")
    keyword = context.args[0]
    try:
        with open("logs.txt", "r", encoding="utf-8") as f:
            filtered = [line for line in f if keyword in line]
        if not filtered:
            return await update.message.reply_text("⚠️ Ничего не найдено.")
        await update.message.reply_text("📄 Найдено:\n" + "".join(filtered[-30:]))
    except:
        await update.message.reply_text("❌ Ошибка при чтении логов.")


async def find_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Нет доступа.")
    if not context.args:
        return await update.message.reply_text("❗ Укажите имя для поиска.")
    name = " ".join(context.args)
    try:
        with open("logs.txt", "r", encoding="utf-8") as f:
            filtered = [line for line in f if name.lower() in line.lower()]
        if not filtered:
            return await update.message.reply_text("⚠️ Не найдено.")
        await update.message.reply_text("🔍 Результаты:\n" + "".join(filtered[-30:]))
    except:
        await update.message.reply_text("❌ Ошибка при поиске.")


async def archive_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Нет доступа.")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        shutil.copy("logs.txt", f"logs_{today}.txt")
        open("logs.txt", "w").close()
        await update.message.reply_text(f"✅ Архив logs_{today}.txt создан и log очищен.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Нет доступа.")
    if len(context.args) < 2:
        return await update.message.reply_text("❗ Формат: /msg user_id текст")
    try:
        user_id = int(context.args[0])
        text = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=user_id, text=f"📩 Сообщение от администратора:\n{text}")
        await update.message.reply_text("✅ Сообщение отправлено.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отправки: {e}")

# === RUN BOT ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("filter_logs", filter_logs))
app.add_handler(CommandHandler("find", find_by_name))
app.add_handler(CommandHandler("archive_logs", archive_logs))
app.add_handler(CommandHandler("msg", msg_command))
app.add_handler(CallbackQueryHandler(handle_submit, pattern="^submit$"))
app.add_handler(CallbackQueryHandler(handle_admin_buttons,
                pattern="^(view_log|clear_log|count_entries)$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("🤖 Bot ishga tushdi...")
app.run_polling()
