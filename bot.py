"""
🤖 VIP VIRAL VIDEOS Telegram Bot
Bot: @VIP_VIRAL_VIDE0S_BOT
Features: Force Join + Broadcast + Mini App + Firebase
Render Ready ✅
"""

import os
import json
import time
import hmac
import hashlib
import asyncio
import logging
import aiohttp
from urllib.parse import parse_qsl
from aiohttp import web
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    WebAppInfo, BotCommand
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import TelegramError, Forbidden, BadRequest
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ============ 🔑 CONFIG ============
BOT_TOKEN = "8833851494:AAGCqVhxe-Dbzq4ViB8_I1kIdLKrEA7UpdI"
WEBAPP_URL = "https://6abdb9f3e657de5d7fd4d8c8--peppy-bonbon-d7e1ea.netlify.app/"
BOT_USERNAME = "VIP_VIRAL_VIDE0S_BOT"

# ✅ Render এর জন্য PORT handling
PORT = int(os.getenv("PORT", 8080))

FIREBASE_DB_URL = "https://vip-viral-videos-916c1-default-rtdb.firebaseio.com"
HTML_FILE = "VIP_VIRAL_VIDEOS.html"

# ✅ Admin সেটআপ
ADMIN_IDS = [
    8404401644,
]

# ✅ Force Join চ্যানেল
FORCE_JOIN_CHANNELS = [
    {
        "name": "VIP VIRAL VIDEOS Official",
        "url": "https://t.me/VIP_VIRAL_VIDE0S",
        "id": "@VIP_VIRAL_VIDE0S",
    },
]
# ===================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============ 🌐 SHARED HTTP SESSION ============
_session = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
    return _session


async def close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


# ============ 🔐 FORCE JOIN CHECK ============
async def is_user_joined(bot, user_id: int) -> bool:
    """সব চ্যানেলে join করেছে কিনা চেক"""
    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(
                chat_id=ch["id"],
                user_id=user_id
            )
            if member.status in [
                ChatMemberStatus.LEFT,
                ChatMemberStatus.BANNED
            ]:
                logger.info(f"❌ User {user_id} not in {ch['id']}")
                return False
        except BadRequest as e:
            logger.warning(f"⚠️ Force join check failed for {ch['id']}: {e}")
            continue
        except TelegramError as e:
            logger.warning(f"⚠️ Telegram error: {e}")
            continue
    return True


def force_join_keyboard():
    keyboard = []
    for ch in FORCE_JOIN_CHANNELS:
        keyboard.append([
            InlineKeyboardButton(f"📢 {ch['name']}", url=ch["url"])
        ])
    keyboard.append([
        InlineKeyboardButton("✅ আমি যোগ দিয়েছি", callback_data="check_join")
    ])
    return InlineKeyboardMarkup(keyboard)


async def send_force_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔒 <b>প্রিয় ইউজার,</b>\n\n"
        "বটটি ব্যবহার করতে হলে প্রথমে আমাদের <b>অফিসিয়াল চ্যানেলে</b> যোগ দিতে হবে।\n\n"
        "নিচের বাটনে ক্লিক করে চ্যানেলে যোগ দিন, তারপর "
        "<b>«✅ আমি যোগ দিয়েছি»</b> বাটনে ক্লিক করুন।\n\n"
        "💡 <i>যোগ দেওয়ার পর বট সম্পূর্ণ ফ্রি ব্যবহার করতে পারবেন।</i>"
    )
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(
                text, reply_markup=force_join_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except BadRequest:
            await update.callback_query.message.reply_text(
                text, reply_markup=force_join_keyboard(),
                parse_mode=ParseMode.HTML
            )
    else:
        await update.message.reply_text(
            text, reply_markup=force_join_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )


# ============ 🚪 JOIN CHECK CALLBACK ============
async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await is_user_joined(context.bot, user_id):
        try:
            await query.message.delete()
        except Exception:
            pass
        await send_welcome(context, query.from_user, query.message, context.args)
    else:
        await query.answer(
            "❌ আপনি এখনও সব চ্যানেলে যোগ দেননি!",
            show_alert=True
        )


# ============ WELCOME ============
async def send_welcome(context, user, message, args=None):
    deep_link = args[0] if args else None

    if deep_link:
        if deep_link.startswith('video_'):
            deep_link = deep_link.replace('video_', '', 1)
        clean_id = deep_link.lstrip('-')
        webapp_url = f"{WEBAPP_URL}#video={clean_id}"
        logger.info(f"📥 Deep link from {user.id}: {deep_link}")

        video = await fetch_video(clean_id)
        if video:
            name = video.get('name', 'Premium Video')
            image_url = video.get('image_url', '')
            views = video.get('view_count', 0)
            category = video.get('category', '')

            caption = (
                f"🎬 <b>{name}</b>\n\n"
                f"👁 <b>Views:</b> {views}\n"
                f"🎯 <b>Category:</b> {category}\n\n"
                f"🔓 আনলক করতে নিচের বাটনে ক্লিক করুন।"
            )
            keyboard = [[
                InlineKeyboardButton(
                    "🎬 এখনই দেখুন",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if image_url:
                try:
                    await message.reply_photo(
                        photo=image_url, caption=caption,
                        reply_markup=reply_markup, parse_mode=ParseMode.HTML
                    )
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Photo failed: {e}")

            await message.reply_text(
                caption, reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            text = (
                f"🎬 <b>VIP VIRAL VIDEOS 💋</b>\n\n"
                f"আপনার শেয়ার করা ভিডিওটি প্রস্তুত!\n"
                f"নিচের বাটনে ক্লিক করে দেখুন। 👇"
            )
            keyboard = [[
                InlineKeyboardButton(
                    "🎬 ভিডিও দেখুন",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]]
            await message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML, disable_web_page_preview=True
            )
    else:
        text = (
            f"🔥 <b>VIP VIRAL VIDEOS 💋</b> এ স্বাগতম, {user.first_name}!\n\n"
            f"🎬 প্রিমিয়াম ভিডিও দেখতে নিচের বাটনে ক্লিক করুন।\n"
            f"📱 সম্পূর্ণ ফ্রি | 🎁 প্রতিদিন নতুন ভিডিও"
        )
        keyboard = [[
            InlineKeyboardButton(
                "🎬 ভিডিও দেখুন",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]]
        await message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )


# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /start from {user.id} ({user.first_name})")

    if not await is_user_joined(context.bot, user.id):
        await send_force_join_message(update, context)
        return

    await send_welcome(context, user, update.message, context.args)


# ============ HELP ============
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_joined(context.bot, user.id):
        await send_force_join_message(update, context)
        return

    text = (
        "📖 <b>সাহায্য</b>\n\n"
        "🔹 /start — অ্যাপ চালু করুন\n"
        "🔹 /help — সাহায্য দেখুন\n"
        "🔹 /share — বট লিংক পান\n\n"
        "💡 <b>টিপস:</b> অ্যাপে যেকোনো ভিডিওর 🔗 বাটনে ক্লিক করে বন্ধুদের সাথে শেয়ার করুন।"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ============ SHARE ============
async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_joined(context.bot, user.id):
        await send_force_join_message(update, context)
        return

    text = (
        f"🔗 <b>শেয়ার লিংক</b>\n\n"
        f"<b>বট লিংক:</b>\n"
        f"<code>https://t.me/{BOT_USERNAME}</code>\n\n"
        f"💡 <b>টিপস:</b> অ্যাপের ভিতরে 🔗 বাটনে ক্লিক করে সরাসরি ভিডিও শেয়ার করুন।"
    )
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


# ============ 📢 BROADCAST ============
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "⛔️ <b>আপনি অ্যাডমিন নন!</b>\n\n"
            "এই কমান্ড শুধুমাত্র অ্যাডমিন ব্যবহার করতে পারবেন।",
            parse_mode=ParseMode.HTML
        )
        return

    if not update.message.reply_to_message:
        text = (
            "📢 <b>ব্রডকাস্ট গাইড</b>\n\n"
            "<b>ব্যবহার:</b>\n"
            "১. যে মেসেজ পাঠাতে চান সেটি বটে পাঠান\n"
            "২. সেই মেসেজে <b>Reply</b> করে <code>/broadcast</code> লিখুন\n"
            "৩. বট সব ইউজারকে সেই মেসেজ পাঠাবে\n\n"
            "💡 <b>সাপোর্ট:</b> টেক্সট, ছবি, ভিডিও, অডিও, ফাইল, স্টিকার সবই।\n\n"
            "🔒 <i>শুধু অ্যাডমিনরা ব্যবহার করতে পারবে।</i>"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    reply_msg = update.message.reply_to_message
    status_msg = await update.message.reply_text(
        "⏳ <b>ব্রডকাস্ট শুরু হচ্ছে...</b>\n\n"
        "📊 ইউজার লিস্ট লোড হচ্ছে...",
        parse_mode=ParseMode.HTML
    )

    user_ids = await get_all_user_ids()

    if not user_ids:
        await status_msg.edit_text(
            "❌ <b>কোনো ইউজার পাওয়া যায়নি!</b>",
            parse_mode=ParseMode.HTML
        )
        return

    total = len(user_ids)
    success = 0
    failed = 0
    blocked = 0
    last_update = time.time()

    for idx, uid in enumerate(user_ids, 1):
        try:
            await reply_msg.copy(chat_id=uid)
            success += 1
        except Forbidden:
            blocked += 1
        except BadRequest as e:
            logger.warning(f"⚠️ BadRequest for {uid}: {e}")
            failed += 1
        except TelegramError as e:
            logger.warning(f"⚠️ Error for {uid}: {e}")
            failed += 1

        if time.time() - last_update >= 5:
            try:
                await status_msg.edit_text(
                    f"📢 <b>ব্রডকাস্ট চলছে...</b>\n\n"
                    f"👥 মোট: <b>{total}</b>\n"
                    f"✅ সফল: <b>{success}</b>\n"
                    f"❌ ব্যর্থ: <b>{failed}</b>\n"
                    f"🚫 ব্লকড: <b>{blocked}</b>\n\n"
                    f"📊 প্রোগ্রেস: <b>{idx}/{total}</b> "
                    f"({int(idx/total*100)}%)",
                    parse_mode=ParseMode.HTML
                )
                last_update = time.time()
            except Exception:
                pass

        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>ব্রডকাস্ট সম্পন্ন!</b>\n\n"
        f"👥 মোট: <b>{total}</b>\n"
        f"✅ সফল: <b>{success}</b>\n"
        f"❌ ব্যর্থ: <b>{failed}</b>\n"
        f"🚫 ব্লকড: <b>{blocked}</b>\n\n"
        f"📊 সাকসেস রেট: <b>{int(success/total*100)}%</b>",
        parse_mode=ParseMode.HTML
    )
    logger.info(f"📢 Broadcast done: {success}/{total}")


async def get_all_user_ids():
    try:
        session = await get_session()
        url = f"{FIREBASE_DB_URL}/users.json"
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            if not data:
                return []
            user_ids = []
            for uid_str in data.keys():
                try:
                    user_ids.append(int(uid_str))
                except (ValueError, TypeError):
                    continue
            logger.info(f"✅ Loaded {len(user_ids)} users")
            return user_ids
    except Exception as e:
        logger.error(f"❌ get_all_user_ids error: {e}")
        return []


# ============ 📊 STATS ============
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "⛔️ <b>আপনি অ্যাডমিন নন!</b>",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await update.message.reply_text(
        "📊 <b>স্ট্যাটস লোড হচ্ছে...</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        user_ids = await get_all_user_ids()
        session = await get_session()
        videos_count = 0
        try:
            async with session.get(f"{FIREBASE_DB_URL}/videos.json") as resp:
                if resp.status == 200:
                    vdata = await resp.json()
                    videos_count = len(vdata) if vdata else 0
        except Exception:
            pass

        text = (
            f"📊 <b>বট স্ট্যাটস</b>\n\n"
            f"🤖 <b>বট:</b> @{BOT_USERNAME}\n"
            f"👥 <b>মোট ইউজার:</b> {len(user_ids)}\n"
            f"🎬 <b>মোট ভিডিও:</b> {videos_count}\n"
            f"📢 <b>Force Join:</b> {len(FORCE_JOIN_CHANNELS)}\n"
            f"👑 <b>অ্যাডমিন:</b> {len(ADMIN_IDS)}\n"
            f"⏰ <b>সময়:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        await status_msg.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Error:</b> {e}",
            parse_mode=ParseMode.HTML
        )


# ============ 🔥 FETCH VIDEO ============
async def fetch_video(video_id):
    if not video_id:
        return None
    clean_id = video_id.lstrip('-')
    try:
        session = await get_session()
        for vid in [video_id, clean_id, f'-{clean_id}']:
            try:
                url = f"{FIREBASE_DB_URL}/videos/{vid}.json"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data:
                            return data
            except Exception:
                continue
        try:
            url = f"{FIREBASE_DB_URL}/videos.json"
            async with session.get(url) as resp:
                if resp.status == 200:
                    all_v = await resp.json()
                    if all_v:
                        for key, val in all_v.items():
                            if key.lstrip('-') == clean_id:
                                return val
        except Exception as e:
            logger.warning(f"List fetch failed: {e}")
    except Exception as e:
        logger.error(f"❌ Firebase error: {e}")
    return None


# ============ TEXT HANDLER ============
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_joined(context.bot, user.id):
        await send_force_join_message(update, context)
        return
    await send_welcome(context, user, update.message, None)


# ============ 🔐 VERIFY INIT DATA ============
def verify_telegram_init_data(init_data: str, bot_token: str):
    try:
        if not init_data:
            return None
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        hash_received = parsed.pop('hash', None)
        if not hash_received:
            return None

        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        calculated = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if calculated != hash_received:
            logger.warning("❌ HMAC mismatch")
            return None

        auth_date = int(parsed.get('auth_date', 0))
        if time.time() - auth_date > 86400:
            logger.warning("❌ initData expired")
            return None

        user = json.loads(parsed.get('user', '{}'))
        return user if user.get('id') else None
    except Exception as e:
        logger.error(f"verify error: {e}")
        return None


# ============ 🌐 WEB SERVER ============
async def serve_html(request):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(script_dir, HTML_FILE)
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(
            text=f"<h2>❌ {HTML_FILE} পাওয়া যায়নি</h2>",
            content_type='text/html', status=404
        )


async def health_check(request):
    return web.json_response({
        "status": "ok",
        "bot": BOT_USERNAME,
        "webapp_url": WEBAPP_URL,
        "firebase": FIREBASE_DB_URL,
        "force_join": [ch["id"] for ch in FORCE_JOIN_CHANNELS],
        "admins": ADMIN_IDS,
        "timestamp": int(time.time())
    })


async def verify_api(request):
    try:
        body = await request.json()
        init_data = body.get('initData', '')
        if not init_data:
            return web.json_response(
                {"ok": False, "error": "initData missing"}, status=400
            )
        user = verify_telegram_init_data(init_data, BOT_TOKEN)
        if not user:
            return web.json_response(
                {"ok": False, "error": "Invalid initData"}, status=401
            )
        logger.info(f"✅ /api/verify OK — user_id={user.get('id')}")
        return web.json_response({"ok": True, "user": user})
    except Exception as e:
        logger.error(f"❌ /api/verify error: {e}")
        return web.json_response(
            {"ok": False, "error": str(e)}, status=500
        )


def create_web_app():
    app = web.Application()
    app.router.add_get('/', serve_html)
    app.router.add_get(f'/{HTML_FILE}', serve_html)
    app.router.add_get('/health', health_check)
    app.router.add_post('/api/verify', verify_api)
    return app


async def run_web_server():
    """পোর্ট ব্যস্ত থাকলে (Errno 98) পরের পোর্টে চেষ্টা করে; কোনোটাই না পেলে
    ওয়েব সার্ভার ছাড়াই বট চালু থাকবে (বটের কাজ ওয়েব সার্ভারের উপর নির্ভর করে না)।"""
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()

    for port in [PORT] + list(range(PORT + 1, PORT + 21)) + [0]:
        try:
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            real_port = site._server.sockets[0].getsockname()[1]
            if port != PORT:
                logger.warning(f"⚠️ পোর্ট {PORT} ব্যস্ত ছিল — {real_port} এ চালু হলো")
            logger.info(f"✅ Web server চালু — পোর্ট {real_port}")
            return runner
        except OSError as e:
            logger.warning(f"⚠️ পোর্ট {port} বাইন্ড হয়নি: {e}")

    logger.error("❌ কোনো পোর্ট পাওয়া যায়নি — ওয়েব সার্ভার ছাড়াই বট চলবে")
    await runner.cleanup()
    return None


# ============ POST INIT ============
async def post_init(application: Application):
    commands = [
        BotCommand("start", "🎬 অ্যাপ চালু করুন"),
        BotCommand("help", "📖 সাহায্য"),
        BotCommand("share", "🔗 শেয়ার লিংক"),
        BotCommand("broadcast", "📢 ব্রডকাস্ট (Admin)"),
        BotCommand("stats", "📊 স্ট্যাটস (Admin)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands সেট হয়েছে")
    logger.info(f"👑 Admins: {ADMIN_IDS}")
    logger.info(f"📢 Force Join: {[ch['id'] for ch in FORCE_JOIN_CHANNELS]}")


# ============ MAIN ============
async def main_async():
    logger.info("=" * 55)
    logger.info("🚀 VIP VIRAL VIDEOS 💋 Bot চালু হচ্ছে...")
    logger.info(f"🤖 Bot: @{BOT_USERNAME}")
    logger.info(f"🌐 WebApp: {WEBAPP_URL}")
    logger.info(f"🔥 Firebase: {FIREBASE_DB_URL}")
    logger.info(f"📡 Port: {PORT}")
    logger.info(f"👑 Admins: {ADMIN_IDS}")
    logger.info(f"📢 Force Join: {[ch['id'] for ch in FORCE_JOIN_CHANNELS]}")
    logger.info("=" * 55)

    runner = await run_web_server()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("share", share_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

    logger.info("=" * 55)
    logger.info("✅ সব চালু! Ctrl+C দিয়ে বন্ধ করুন।")
    logger.info("=" * 55)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 বন্ধ করা হচ্ছে...")
    finally:
        await close_session()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        if runner:
            await runner.cleanup()
        logger.info("👋 বন্ধ হয়েছে")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("👋 বন্ধ হয়েছে")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
