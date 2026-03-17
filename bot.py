import datetime
import re
from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters

from database import conn, cursor

import os
TOKEN = os.getenv("TOKEN")


# 新增預約
async def book(update, context):

    try:
        name = context.args[0]
        date = context.args[1]   # 只需要 MM-DD
        time = context.args[2]

        cursor.execute(
            "INSERT INTO bookings(name,date,time) VALUES (?,?,?)",
            (name, date, time)
        )

        conn.commit()

        await update.message.reply_text(
            f"{name} 已成功預約 ✅\n{date} {time}"
        )

    except:
        await update.message.reply_text(
            "格式錯誤\n請輸入：\n/book 客戶名稱 月-日 時間\n\n例如：\n/book 王小明 03-18 15:00"
        )

async def cancel(update, context):

    try:
        name = context.args[0]
        date = context.args[1]

        cursor.execute(
            "DELETE FROM bookings WHERE name = ? AND date = ?",
            (name, date)
        )

        conn.commit()

        if cursor.rowcount == 0:
            await update.message.reply_text(
                "❌ 找不到該預約"
            )
        else:
            await update.message.reply_text(
                f"✅ 已取消 {name} {date} 的預約"
            )

    except:
        await update.message.reply_text(
            "格式錯誤\n請輸入：\n/cancel 客戶名稱 月-日\n\n例如：\n/cancel 王小明 03-18"
        )

def parse_date(text):

    text = text.strip()

    # 0318
    if text.isdigit() and len(text) == 4:
        return text[:2] + "-" + text[2:]

    # 03/18 或 03.18 或 03-18
    for sep in ["/", ".", "-"]:
        if sep in text:
            parts = text.split(sep)
            if len(parts) == 2:
                m = parts[0].zfill(2)
                d = parts[1].zfill(2)
                return f"{m}-{d}"

    return None

async def menu(update, context):

    text = update.message.text.strip()

    # ===== 按鈕 =====
    if text == "今日預約":
        await today(update, context)
        return

    if text == "明日預約":
        await tomorrow(update, context)
        return

    if text == "指令說明":
        await help_command(update, context)
        return

    if text == "新增預約":
        await update.message.reply_text("請輸入：\n/book 客戶名稱 月-日 時間")
        return

    if text == "取消預約":
        await update.message.reply_text("請輸入：\n/cancel 客戶名稱 月-日")
        return

    if text == "查詢日期":
        await update.message.reply_text("請輸入：\n/list 月-日")
        return

    # ===== ⭐ 半 AI =====

    # 👉 查人
    if "預約" in text:

        keywords = [
            "幫我", "查", "有沒有", "沒有", "預約", "看",
            "一下", "嗎", "的", "了", "有"
    ]

        name = text

        for k in keywords:
            name = name.replace(k, "")

        name = re.sub(r"\d{4}", "", name)
        name = re.sub(r"\d{2}[\/\.\-]\d{2}", "", name)

        name = name.replace("?", "").replace("？", "")
        name = name.strip()

        rows = cursor.execute(
            "SELECT name, date, time FROM bookings WHERE name LIKE ?",
            (f"%{name}%",)
    ).fetchall()

        if not rows:
            await update.message.reply_text(f"{name} 沒有預約")
        else:
            msg = f"{name} 的預約\n\n"
            for r in rows:
               msg += f"{r[1]} {r[2]}\n"

            await update.message.reply_text(msg)

        return
    # 👉 今天
    if "今天" in text or "今日" in text:
        await today(update, context)
        return

    # 👉 明天
    if "明天" in text or "明日" in text:
        await tomorrow(update, context)
        return

    # 👉 今天幾個人
    if "今天" in text and ("幾個" in text or "人" in text):

        today_date = datetime.datetime.now().strftime("%m-%d")

        rows = cursor.execute(
            "SELECT COUNT(*) FROM bookings WHERE date = ?",
            (today_date,)
        ).fetchone()

        await update.message.reply_text(f"📊 今天共有 {rows[0]} 位預約")
        return

    # 👉 日期解析
    parsed_date = parse_date(text)

    if parsed_date:

        rows = cursor.execute(
            "SELECT name, time FROM bookings WHERE date = ?",
            (parsed_date,)
        ).fetchall()

        if not rows:
            await update.message.reply_text(f"{parsed_date} 沒有預約")
        else:
            msg = f"📅 {parsed_date} 預約名單\n\n"
            for r in rows:
                msg += f"{r[0]} {r[1]}\n"

            await update.message.reply_text(msg)

        return

    # 👉 fallback
    await update.message.reply_text("❓看不懂你的意思，可以試試輸入：\n王小明有沒有預約")
                
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["新增預約"],
        ["今日預約", "明日預約"],
        ["查詢日期", "取消預約"],
        ["指令說明"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "預約系統已啟動\n請選擇功能",
        reply_markup=reply_markup
    )


# 查看今日預約
import datetime

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    today_date = datetime.datetime.now().strftime("%m-%d")

    rows = cursor.execute(
        "SELECT name,time FROM bookings WHERE date = ?",
        (today_date,)
    ).fetchall()

    if not rows:
        await update.message.reply_text("今天還沒有預約")
        return

    msg = "今日預約客戶\n\n"

    for r in rows:
        msg += f"{r[0]} {r[1]}\n"

    await update.message.reply_text(msg)

async def daily_list(context: ContextTypes.DEFAULT_TYPE):

    today_date = datetime.datetime.now().strftime("%m-%d")

    rows = cursor.execute(
        "SELECT name, time FROM bookings WHERE date = ?",
        (today_date,)
    ).fetchall()

    if not rows:
        msg = f"📅 今日預約清單（{today_date}）\n\n目前沒有預約"
    else:
        msg = f"📅 今日預約清單（{today_date}）\n\n"

        for r in rows:
            msg += f"{r[0]} {r[1]}\n"

    await context.bot.send_message(
        chat_id=8243633524,
        text=msg
    )

async def getid(update, context):
    await update.message.reply_text(str(update.effective_chat.id))


async def list_booking(update, context):

    try:
        date = context.args[0]

        rows = cursor.execute(
            "SELECT name,time FROM bookings WHERE date = ?",
            (date,)
        ).fetchall()

        if not rows:
            await update.message.reply_text(f"{date} 沒有預約")
            return

        msg = f"{date} 預約名單\n\n"

        for r in rows:
            msg += f"{r[0]} {r[1]}\n"

        await update.message.reply_text(msg)

    except:
        await update.message.reply_text(
            "格式錯誤\n請輸入：\n/list 月-日\n\n例如：\n/list 03-18"
        )

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tomorrow_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%m-%d")

    rows = cursor.execute(
        "SELECT name,time FROM bookings WHERE date = ?",
        (tomorrow_date,)
    ).fetchall()

    if not rows:
        await update.message.reply_text("明天還沒有預約")
        return

    msg = "📅 明日預約\n\n"

    for r in rows:
        msg += f"{r[0]} {r[1]}\n"

    await update.message.reply_text(msg)

async def help_command(update, context):

    msg = (
        "📋 可使用指令\n\n"
        "/book 客戶名稱 月-日 時間\n"
        "➡ 新增預約\n"
        "例：/book 王小明 03-18 15:00\n\n"

        "/today\n"
        "➡ 查看今日預約\n\n"

        "/tomorrow\n"
        "➡ 查看明日預約\n\n"

        "/list 月-日\n"
        "➡ 查看指定日期預約\n"
        "例：/list 03-18\n\n"

        "/cancel 客戶名稱 月-日\n"
        "➡ 取消預約\n"
        "例：/cancel 王小明 03-18\n\n"

        "/help\n"
        "➡ 查看所有指令說明"
    )

    await update.message.reply_text(msg)


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("book", book))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("tomorrow", tomorrow))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_booking))
    app.add_handler(CommandHandler("id", getid))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))
    # ⭐ 官方排程（最穩）
    import datetime as dt

    if app.job_queue:
        app.job_queue.run_daily(
            daily_list,
            time=dt.time(hour=0, minute=0)
    )

    print("Bot started")

    app.run_polling()


if __name__ == "__main__":
    main()
