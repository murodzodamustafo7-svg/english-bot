import json
import logging
import random
import asyncio
from datetime import date, timedelta, datetime, time as dtime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

import database as db

# ------------------ SETTINGS ------------------
BOT_TOKEN = "PUT_YOUR TOKEN_HERE"   # аз @BotFather гиред
WORDS_PER_DAY = 10
SEND_HOUR = 8      # соате, ки калимаҳо ҳар рӯз фиристода мешаванд (24-соата, вақти сервер)
SEND_MINUTE = 0
# ------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

with open("words.json", "r", encoding="utf-8") as f:
    ALL_WORDS = json.load(f)

WORD_LOOKUP = {w["en"]: w for w in ALL_WORDS}


def pick_new_words(user_id: int, count: int = WORDS_PER_DAY):
    sent_already = set(db.get_sent_words_for_user(user_id))
    remaining = [w for w in ALL_WORDS if w["en"] not in sent_already]
    if not remaining:
        return []
    random.shuffle(remaining)
    return remaining[:count]


def build_quiz_keyboard(correct_word: dict, sent_date: str):
    wrong_pool = [w for w in ALL_WORDS if w["en"] != correct_word["en"]]
    wrong_choices = random.sample(wrong_pool, k=min(3, len(wrong_pool)))
    options = wrong_choices + [correct_word]
    random.shuffle(options)

    buttons = []
    for opt in options:
        is_correct = 1 if opt["en"] == correct_word["en"] else 0
        callback_data = f"q|{sent_date}|{correct_word['en']}|{is_correct}"
        buttons.append([InlineKeyboardButton(opt["tj"], callback_data=callback_data)])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        "Ассалому алейкум! 👋\n\n"
        "Ман ботам, ки ҳар рӯз ба шумо 10 калимаи нави англисӣ мефиристам "
        "ва баъд викторина медиҳам, то донишатонро санҷем.\n\n"
        "Дастурҳо:\n"
        "/words — гирифтани калимаҳои имрӯза (ҳозир)\n"
        "/stats — дидани холҳои ҳафтагӣ ва моҳона\n\n"
        f"Калимаҳои нав ҳар рӯз соати {SEND_HOUR}:00 ба таври худкор фиристода мешаванд."
    )


async def send_daily_words(user_id: int, bot):
    words = pick_new_words(user_id)
    if not words:
        await bot.send_message(
            user_id,
            "🎉 Табрик! Шумо ҳамаи калимаҳои дар бот мавҷударо аллакай омӯхтед!\n"
            "Ба зудӣ калимаҳои нав илова хоҳанд шуд.",
        )
        return

    today = date.today().isoformat()
    db.record_sent_words(user_id, words)

    text = "📚 *Калимаҳои имрӯза:*\n\n"
    for i, w in enumerate(words, 1):
        text += f"{i}. *{w['en']}* — {w['tj']}\n   _{w['example']}_\n\n"
    text += "Ҳоло викторина сар мешавад 👇"

    await bot.send_message(user_id, text, parse_mode="Markdown")

    for w in words:
        kb = build_quiz_keyboard(w, today)
        await bot.send_message(
            user_id, f"❓ Тарҷумаи калимаи *{w['en']}* чист?", reply_markup=kb, parse_mode="Markdown"
        )


async def words_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    await send_daily_words(user.id, context.bot)


async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, sent_date, word_en, is_correct = query.data.split("|")
    is_correct = bool(int(is_correct))
    user_id = query.from_user.id

    db.record_answer(user_id, word_en, sent_date, is_correct)

    correct_tj = WORD_LOOKUP.get(word_en, {}).get("tj", "?")
    if is_correct:
        result_text = f"✅ Дуруст! *{word_en}* = {correct_tj}"
    else:
        result_text = f"❌ Хато. Тарҷумаи дурусти *{word_en}* — {correct_tj}"

    await query.edit_message_text(result_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    today = date.today()
    week_start = (today - timedelta(days=7)).isoformat()
    month_start = (today - timedelta(days=30)).isoformat()

    week_score, week_total = db.get_score(user.id, week_start)
    month_score, month_total = db.get_score(user.id, month_start)
    today_score, today_total = db.get_score(user.id, today.isoformat())
    learned = db.get_total_learned(user.id)

    text = (
        "📊 *Омори шумо*\n\n"
        f"Имрӯз: {today_score}/{today_total} хол\n"
        f"Дар ин ҳафта: {week_score}/{week_total} хол\n"
        f"Дар ин моҳ: {month_score}/{month_total} хол\n\n"
        f"📖 Ҳамагӣ калимаҳои омӯхташуда: *{learned}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def daily_loop(app: Application):
    """
    Давраи бесамар (background loop), ки ҳар рӯз соати SEND_HOUR:SEND_MINUTE
    ба ҳамаи корбарон калимаҳои нав мефиристад.
    Ин ба ҷои job-queue (APScheduler) истифода мешавад, то бо ҳама версияи
    Python (аз ҷумла 3.14) бе мушкил кор кунад.
    """
    sent_today_for = set()
    while True:
        now = datetime.now()
        target_reached = (
            now.hour == SEND_HOUR
            and now.minute == SEND_MINUTE
        )
        today_key = now.date().isoformat()

        if target_reached and today_key not in sent_today_for:
            logger.info("Вақти фиристодани калимаҳои рӯзона расид...")
            for user_id in db.get_all_users():
                try:
                    await send_daily_words(user_id, app.bot)
                except Exception as e:
                    logger.error(f"Хатогӣ ҳангоми фиристодан ба {user_id}: {e}")
            sent_today_for.add(today_key)

        # Тоза кардани сабти рӯзҳои гузашта, то хотира зиёд нашавад
        if len(sent_today_for) > 3:
            sent_today_for = {today_key}

        await asyncio.sleep(30)  # ҳар 30 сония санҷиш мекунад


async def post_init(app: Application):
    # Давраи рӯзонаро ҳамчун вазифаи алоҳида дар паси парда оғоз мекунад
    asyncio.create_task(daily_loop(app))


def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("words", words_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^q\|"))

    logger.info("Бот оғоз шуд...")
    app.run_polling()


if __name__ == "__main__":
    main()
python bot.py
