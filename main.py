import json
import os
import time
import asyncio
import uuid
import random
from datetime import datetime, timedelta, timezone
import logging
import re
import aiosqlite
import requests
from dotenv import load_dotenv
from pytoniq import LiteBalancer, WalletV4R2, begin_cell
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env faylidan tokenni olish
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    logger.error("API_TOKEN topilmadi. .env faylida TELEGRAM_BOT_TOKEN ni tekshiring.")
    exit(1)

# Til sozlamalari
LANGUAGES = {
    'en': {
        'welcome': "Welcome to Tronocoin Airdrop!\nReferral link: https://t.me/{bot_username}?start={user_id}",
        'main_menu': {
            'profile': "👤 Profile",
            'withdraw': "💸 Withdraw",
            'daily_bonus': "🎁 Daily Bonus",
            'earn': "🎯 Earn",
            'contact': "✉️ Contact",
            'top_users': "🏆 Top users",
            'admin_panel': "👨‍💼 Admin panel"
        },
        'contact_start': "✍️ Write your message. We will respond soon.",
        'contact_received': "✅ Your message has been sent. Please wait for our response.",
        'contact_admin_message': "📥 New message:\n\n👤 User: {user_name} (ID: {user_id})\n💬 Message:\n{message}",
        'reply_prompt': "✏️ Write your response.",
        'reply_sent': "✅ Response sent.",
        'reply_failed': "❌ Response not sent. The user may have blocked the bot.",
        'withdraw_start': "💼 Send your TON wallet address:",
        'cancel': "❌ Cancel",
        'invalid_wallet': "Invalid address. Please try again.",
        'captcha_prompt': "🧠 Captcha: {a} + {b} = ?",
        'invalid_captcha': "❌ Incorrect captcha. Please try again.",
        'captcha_number_only': "🔢 Enter only numbers.",
        'withdraw_amount': "💸 How much Tronocoin ($TRC) would you like to withdraw?",
        'invalid_amount': "❗ Please enter a valid number.",
        'insufficient_balance': "📉 Insufficient balance. You have: {balance} $TRC",
        'not_registered': "🚫 You are not registered.",
        'payment_instruction': "🔐 To cover blockchain fees and ensure system stability, send {fee} TON to the following address:\n`{wallet}`\n\n📝 Include the following memo:\n`{memo}`\n\n📌 Note: If the memo is not included, the payment will not be accepted.\n\n✅ After sending the payment, press /verify.",
        'verify_prompt': "Please press /verify after sending the payment.",
        'payment_checking': "⏳ Checking payment...",
        'payment_confirmed': "✅ Payment confirmed!\n💰 Amount: {amount:.4f} TON\n🔗 Transaction ID: {tx_id}...\n⏰ Tokens are being sent...",
        'payment_success': "🎉 Success!\n💰 {amount} TRC tokens have been sent to {wallet}!\n✅ Transaction completed.",
        'payment_failed': "❌ An error occurred!\n💰 {amount} TRC has been refunded to your balance.\n🔄 Please try again.",
        'payment_not_found': "❌ Payment not found!\nPlease ensure you sent the payment correctly and included the correct memo.\n\nMemo: {memo}",
        'daily_bonus_prompt': "<b>🎁 Daily Bonus</b>\n\n⏳ Wait until the following time to claim your bonus:\n🕒 <b>Time left:</b> {time}\n💸 <b>Bonus:</b> 0 $TRC\n\n",
        'daily_bonus_ready': "<b>🎁 Bonus ready!</b>\n\n<b>Time:</b> 00:00:00\n<b>Bonus:</b> 3000 $TRC\n\n🎉 Claim now!",
        'daily_bonus_received': "<b>✅ Bonus received!</b>\n\n<b>+3000 $TRC</b>\n🗓 Next bonus: in 12 hours.",
        'daily_bonus_not_ready': "<b>🎁 Daily Bonus</b>\n\n⏳ Bonus not available yet.\n\n<b>🕒 Time left:</b> {time}\n<b>💰 Bonus:</b> 0 $TRC",
        'top_users': "🏆 Top Users (by balance):\n{users_list}",
        'profile': "{profile_line}\n💰 Balance: {balance:,} $TRC\n👥 Referrals: {ref_count}\n🎁 Daily bonus: {bonus_status}\n\n🔗 Referral link:\n{referral_link}",
        'admin_panel': "👥 Total users: {user_count}\n💰 Total balance: {total_balance} Tronocoin\n\n🏆 Top referrers:\n{top_refs}",
        'broadcast_prompt': "Enter the message you want to send:",
        'broadcast_sent': "Message sent to all users.",
        'ad_start': "1. Send the channel link (e.g., https://t.me/channel_name):",
        'ad_reward': "2. Enter the TRC reward for joining the channel:",
        'ad_limit': "Enter the maximum TRC limit for the channel (number):",
        'ad_description': "3. Write a short description of the channel:",
        'ad_photo': "4. Send a photo for the channel:",
        'ad_placed': "✅ Ad placed:\n\nChannel: {link}\nReward: {reward} TRC\n{description}",
        'ad_notification': "📢 New ad! 💸 Earn {reward} TRC!\n🎯 Check the Earn section.",
        'ad_no_ads': "No ads available.",
        'ad_select': "Select an ad to delete:",
        'ad_deleted': "✅ {link} ad deleted.",
        'ad_stats': "Ad performance statistics:\n{stats}",
        'earn_no_ads': "No new ads available at the moment.",
        'earn_caption': "💸 Earn {reward} $TRC!\n🔗 Channel: {link}\n📜 {description}",
        'earn_limit_reached': "{link}\nReward limit reached.",
        'earn_already_received': "{link}\n✅ Reward already received.",
        'earn_not_subscribed': "{link}\n❌ You are not subscribed.",
        'earn_error': "{link}\n❌ Could not check channel: {error}",
        'earn_completed': "Check completed.",
        'invalid_reward': "Reward amount must be greater than 0.",
        'invalid_limit': "Limit amount must be greater than 0.",
        'invalid_number': "Please enter only numbers.",
        'invalid_description': "Please write a description.",
        'language_select': "🌍 Select language:"
    },
    'ru': {
        'welcome': "Добро пожаловать в Tronocoin Airdrop!\nРеферальная ссылка: https://t.me/{bot_username}?start={user_id}",
        'main_menu': {
            'profile': "👤 Профиль",
            'withdraw': "💸 Вывод",
            'daily_bonus': "🎁 Ежедневный бонус",
            'earn': "🎯 Заработать",
            'contact': "✉️ Связаться",
            'top_users': "🏆 Топ пользователей",
            'admin_panel': "👨‍💼 Панель администратора"
        },
        'contact_start': "✍️ Напишите ваше сообщение. Мы ответим в ближайшее время.",
        'contact_received': "✅ Ваше сообщение отправлено. Ожидайте ответа.",
        'contact_admin_message': "📥 Новое сообщение:\n\n👤 Пользователь: {user_name} (ID: {user_id})\n💬 Сообщение:\n{message}",
        'reply_prompt': "✏️ Напишите ваш ответ.",
        'reply_sent': "✅ Ответ отправлен.",
        'reply_failed': "❌ Ответ не отправлен. Пользователь мог заблокировать бота.",
        'withdraw_start': "💼 Отправьте адрес вашего TON кошелька:",
        'cancel': "❌ Отмена",
        'invalid_wallet': "Неверный адрес. Попробуйте снова.",
        'captcha_prompt': "🧠 Капча: {a} + {b} = ?",
        'invalid_captcha': "❌ Неверная капча. Попробуйте снова.",
        'captcha_number_only': "🔢 Вводите только цифры.",
        'withdraw_amount': "💸 Сколько Tronocoin ($TRC) вы хотите вывести?",
        'invalid_amount': "❗ Пожалуйста, введите правильное число.",
        'insufficient_balance': "📉 Недостаточно средств. У вас: {balance} $TRC",
        'not_registered': "🚫 Вы не зарегистрированы.",
        'payment_instruction': "🔐 Для покрытия комиссии блокчейна и стабильности системы отправьте {fee} TON на следующий адрес:\n`{wallet}`\n\n📝 Укажите в комментарии (memo):\n`{memo}`\n\n📌 Примечание: Если memo не указан, платеж не будет принят.\n\n✅ После отправки платежа нажмите /verify.",
        'verify_prompt': "Нажмите /verify после отправки платежа.",
        'payment_checking': "⏳ Проверка платежа...",
        'payment_confirmed': "✅ Платеж подтвержден!\n💰 Сумма: {amount:.4f} TON\n🔗 ID транзакции: {tx_id}...\n⏰ Токены отправляются...",
        'payment_success': "🎉 Успешно!\n💰 {amount} TRC токенов отправлено на {wallet}!\n✅ Транзакция завершена.",
        'payment_failed': "❌ Произошла ошибка!\n💰 {amount} TRC возвращено на ваш баланс.\n🔄 Попробуйте снова.",
        'payment_not_found': "❌ Платеж не найден!\nПожалуйста, убедитесь, что вы правильно отправили платеж и указали правильный memo.\n\nMemo: {memo}",
        'daily_bonus_prompt': "<b>🎁 Ежедневный бонус</b>\n\n⏳ Дождитесь следующего времени, чтобы получить бонус:\n🕒 <b>Оставшееся время:</b> {time}\n💸 <b>Бонус:</b> 0 $TRC\n\n",
        'daily_bonus_ready': "<b>🎁 Бонус готов!</b>\n\n<b>Время:</b> 00:00:00\n<b>Бонус:</b> 3000 $TRC\n\n🎉 Получите сейчас!",
        'daily_bonus_received': "<b>✅ Бонус получен!</b>\n\n<b>+3000 $TRC</b>\n🗓 Следующий бонус: через 12 часов.",
        'daily_bonus_not_ready': "<b>🎁 Ежедневный бонус</b>\n\n⏳ Бонус еще недоступен.\n\n<b>🕒 Оставшееся время:</b> {time}\n<b>💰 Бонус:</b> 0 $TRC",
        'top_users': "🏆 Топ пользователей (по балансу):\n{users_list}",
        'profile': "{profile_line}\n💰 Баланс: {balance:,} $TRC\n👥 Рефералы: {ref_count}\n🎁 Ежедневный бонус: {bonus_status}\n\n🔗 Реферальная ссылка:\n{referral_link}",
        'admin_panel': "👥 Всего пользователей: {user_count}\n💰 Общий баланс: {total_balance} Tronocoin\n\n🏆 Топ рефереров:\n{top_refs}",
        'broadcast_prompt': "Введите сообщение, которое хотите отправить:",
        'broadcast_sent': "Сообщение отправлено всем пользователям.",
        'ad_start': "1. Отправьте ссылку на канал (например: https://t.me/channel_name):",
        'ad_reward': "2. Введите количество TRC за подписку на канал:",
        'ad_limit': "Введите максимальный лимит TRC для канала (число):",
        'ad_description': "3. Напишите краткое описание канала:",
        'ad_photo': "4. Отправьте фото для канала:",
        'ad_placed': "✅ Реклама размещена:\n\nКанал: {link}\nНаграда: {reward} TRC\n{description}",
        'ad_notification': "📢 Новая реклама! 💸 Заработайте {reward} TRC!\n🎯 Проверьте раздел Earn.",
        'ad_no_ads': "Нет доступных объявлений.",
        'ad_select': "Выберите объявление для удаления:",
        'ad_deleted': "✅ {link} объявление удалено.",
        'ad_stats': "Статистика эффективности рекламы:\n{stats}",
        'earn_no_ads': "На данный момент новых объявлений нет.",
        'earn_caption': "💸 Заработайте {reward} $TRC!\n🔗 Канал: {link}\n📜 {description}",
        'earn_limit_reached': "{link}\nЛимит награды достигнут.",
        'earn_already_received': "{link}\n✅ Награда уже получена.",
        'earn_not_subscribed': "{link}\n❌ Вы не подписаны.",
        'earn_error': "{link}\n❌ Не удалось проверить канал: {error}",
        'earn_completed': "Проверка завершена.",
        'invalid_reward': "Сумма награды должна быть больше 0.",
        'invalid_limit': "Сумма лимита должна быть больше 0.",
        'invalid_number': "Пожалуйста, вводите только числа.",
        'invalid_description': "Пожалуйста, напишите описание.",
        'language_select': "🌍 Выберите язык:"
    }
}

# Bot konfiguratsiyasi
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # Admin ID from .env or default
PAYMENT_WALLET = os.getenv('PAYMENT_WALLET')  # Default wallet
BLOCKCHAIN_FEE = 0.04
LIMIT = "20"
BASE_URL = f"https://toncenter.com/api/v2/getTransactions?address={PAYMENT_WALLET}&limit={LIMIT}&to_lt=0&archival=false"
STATE_FILE = "deposit_state.json"
DB_PATH = 'tronocoin.db'
REFERRAL_BONUS = 5000

# States
class ContactState(StatesGroup):
    waiting_for_message = State()

class LanguageState(StatesGroup):
    waiting_for_language = State()

class WithdrawStates(StatesGroup):
    waiting_for_wallet = State()
    waiting_for_captcha = State()
    waiting_for_amount = State()
    waiting_for_verify = State()

class AddAdState(StatesGroup):
    waiting_for_link = State()
    waiting_for_reward = State()
    waiting_for_limit = State()
    waiting_for_description = State()
    waiting_for_photo = State()

class BroadcastMessage(StatesGroup):
    waiting_for_text = State()

# Bot va Dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
ads_data = []


# Utility Functions
def get_main_keyboard(user_id, language='en'):
    buttons = [
        [KeyboardButton(text=LANGUAGES[language]['main_menu']['profile']), KeyboardButton(text=LANGUAGES[language]['main_menu']['withdraw'])],
        [KeyboardButton(text=LANGUAGES[language]['main_menu']['daily_bonus']), KeyboardButton(text=LANGUAGES[language]['main_menu']['earn'])],
        [KeyboardButton(text=LANGUAGES[language]['main_menu']['contact']), KeyboardButton(text=LANGUAGES[language]['main_menu']['top_users'])],
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text=LANGUAGES[language]['main_menu']['admin_panel'])])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_earn_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Check", callback_data="check_earn")]])

def get_calm_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎁 Claim Bonus", callback_data="calm_bonus")]])

def get_cancel_keyboard(language='en'):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=LANGUAGES[language]['cancel'])]], resize_keyboard=True)

def get_verify_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="/verify")]], resize_keyboard=True)

def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])

def is_valid_ton_wallet(address: str) -> bool:
    return bool(re.match(r'^(EQ|UQ)[A-Za-z0-9_-]{46}$', address))

# Payment Monitoring Functions
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                state = json.load(f)
                return state.get('last_lt', 0), set(state.get('processed_txs', []))
            except json.JSONDecodeError:
                logger.error("Error reading state file, starting fresh")
    return 0, set()

def save_state(last_lt, processed_txs):
    state = {
        'last_lt': last_lt,
        'processed_txs': list(processed_txs)
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

async def check_payment(memo):
    last_lt, processed_txs = load_state()
    try:
        url = f"{BASE_URL}&to_lt={last_lt if last_lt > 0 else 0}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data.get('ok'):
            return False
        transactions = data.get('result', [])
        if not transactions:
            return False
        highest_lt = last_lt
        for tx in sorted(transactions, key=lambda x: x.get('transaction_id', {}).get('lt', 0), reverse=True):
            tx_id = tx.get('transaction_id', {}).get('hash', '')
            tx_lt = int(tx.get('transaction_id', {}).get('lt', '0'))
            if not tx_id or tx_lt == 0 or tx_id in processed_txs:
                continue
            in_msg = tx.get('in_msg', {})
            amount_nanotons = int(in_msg.get('value', '0'))
            amount_ton = amount_nanotons / 1_000_000_000
            comment = in_msg.get('message', '').strip()
            if amount_ton >= BLOCKCHAIN_FEE and comment == memo:
                sender = in_msg.get('source', 'Unknown')
                highest_lt = max(highest_lt, tx_lt)
                processed_txs.add(tx_id)
                save_state(highest_lt, processed_txs)
                return {
                    'tx_id': tx_id,
                    'lt': tx_lt,
                    'amount_ton': amount_ton,
                    'sender': sender,
                    'comment': comment,
                    'timestamp': tx.get('utime', 'N/A')
                }
        save_state(highest_lt, processed_txs)
        return False
    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        return False

async def process_trc_withdrawal(sender, trc_amount, memo):
    try:
        logger.info(f"Initiating TRC withdrawal: {trc_amount} TRC to {sender} (memo: {memo})")
        load_dotenv()
        mnemonic_string = os.getenv('MNEMONIC')
        if not mnemonic_string:
            logger.error("MNEMONIC not found in .env file")
            return False
        mnemonics = mnemonic_string.split()
        provider = LiteBalancer.from_mainnet_config(1)
        await provider.start_up()
        wallet = await WalletV4R2.from_mnemonic(provider=provider, mnemonics=mnemonics)
        USER_ADDRESS = wallet.address
        JETTON_MASTER_ADDRESS = os.getenv('JETTON_MASTER_ADDRESS')
        DESTINATION_ADDRESS = sender
        USER_JETTON_WALLET = (await provider.run_get_method(
            address=JETTON_MASTER_ADDRESS,
            method="get_wallet_address",
            stack=[begin_cell().store_address(USER_ADDRESS).end_cell().begin_parse()]
        ))[0].load_address()
        trc_amount_nano = int(trc_amount * 10**9)
        forward_payload = (begin_cell()
                          .store_uint(0, 32)
                          .store_snake_string("Token Sent Successfully.")
                          .end_cell())
        transfer_cell = (begin_cell()
                        .store_uint(0xf8a7ea5, 32)
                        .store_uint(0, 64)
                        .store_coins(trc_amount_nano)
                        .store_address(DESTINATION_ADDRESS)
                        .store_address(USER_ADDRESS)
                        .store_bit(0)
                        .store_coins(1)
                        .store_bit(1)
                        .store_ref(forward_payload)
                        .end_cell())
        await wallet.transfer(destination=USER_JETTON_WALLET, amount=int(0.05*1e9), body=transfer_cell)
        await provider.close_all()
        logger.info(f"TRC has been transferred to wallet: {sender}")
        return True
    except Exception as e:
        logger.error(f"Error in TRC withdrawal: {e}")
        return False

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['contact'], LANGUAGES['ru']['main_menu']['contact']}))
async def start_contact(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await state.set_state(ContactState.waiting_for_message)
    await message.answer(LANGUAGES[language]['contact_start'])

@router.message(ContactState.waiting_for_message)
async def receive_user_message(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    user_id = user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    text = LANGUAGES[language]['contact_admin_message'].format(user_name=user.full_name, user_id=user.id, message=message.text)
    await message.bot.send_message(ADMIN_ID, text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✍️ Write response", callback_data=f"reply_{user.id}")]
    ]))
    await message.answer(LANGUAGES[language]['contact_received'])

class ReplyState(StatesGroup):
    waiting_for_reply = State()

@router.callback_query(F.data.startswith("reply_"))
async def reply_to_user_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    await state.update_data(reply_to=user_id)
    await state.set_state(ReplyState.waiting_for_reply)
    await callback.message.answer(LANGUAGES['en']['reply_prompt'])
    await callback.answer()

@router.message(ReplyState.waiting_for_reply)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reply_to = data.get("reply_to")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (reply_to,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await state.clear()
    try:
        await message.bot.send_message(reply_to, f"📬 Admin response:\n\n{message.text}")
        await message.answer(LANGUAGES[language]['reply_sent'])
    except TelegramForbiddenError:
        await message.answer(LANGUAGES[language]['reply_failed'])

@router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    command_args = message.text.split(' ', 1)
    args = command_args[1] if len(command_args) > 1 else None
    user_id = message.from_user.id
    username = message.from_user.username
    language = 'en'  # Default til

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            referred_by = int(args) if args and args.isdigit() else None
            await db.execute('INSERT INTO users (user_id, username, referred_by, language) VALUES (?, ?, ?, ?)', (user_id, username, referred_by, language))
            await db.commit()
            if referred_by:
                await db.execute('UPDATE users SET balance = balance + ? WHERE user_id=?', (REFERRAL_BONUS, referred_by))
                await db.commit()
                try:
                    cur = await db.execute('SELECT language FROM users WHERE user_id=?', (referred_by,))
                    result = await cur.fetchone()
                    ref_lang = result[0] if result and result[0] in ['en', 'ru'] else 'en'
                    await bot.send_message(referred_by, f"New user joined: @{username or 'NoUsername'}\nBonus: {REFERRAL_BONUS} Tronocoin.")
                except TelegramForbiddenError:
                    pass
        else:
            language = user[4] if user[4] in ['en', 'ru'] else 'en'

    bot_user = await bot.get_me()
    bot_username = bot_user.username
    await message.answer(
        LANGUAGES[language]['language_select'],
        reply_markup=get_language_keyboard()
    )
    await state.set_state(LanguageState.waiting_for_language)

@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = callback.data.split("_")[1]
    if language not in ['en', 'ru']:
        language = 'en'
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        await db.commit()
    bot_user = await bot.get_me()
    bot_username = bot_user.username
    # edit_text o‘rniga send_message ishlatamiz
    await callback.message.answer(
        LANGUAGES[language]['welcome'].format(bot_username=bot_username, user_id=user_id),
        reply_markup=get_main_keyboard(user_id, language)
    )
    # Eski xabarni o‘chiramiz
    await callback.message.delete()
    await state.clear()
    await callback.answer()

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['withdraw'], LANGUAGES['ru']['main_menu']['withdraw']}))
async def withdraw_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await state.clear()
    await state.set_state(WithdrawStates.waiting_for_wallet)
    await message.answer(LANGUAGES[language]['withdraw_start'], reply_markup=get_cancel_keyboard(language))

@router.message(WithdrawStates.waiting_for_wallet)
async def wallet_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    
    if message.text == LANGUAGES[language]['cancel']:
        await state.clear()
        await message.answer(LANGUAGES[language]['cancel'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    if message.text in [LANGUAGES[language]['main_menu']['withdraw'], LANGUAGES[language]['main_menu']['profile'], LANGUAGES[language]['main_menu']['earn'], LANGUAGES[language]['main_menu']['daily_bonus'], LANGUAGES[language]['main_menu']['top_users']]:
        await state.clear()
        await message.answer(LANGUAGES[language]['invalid_wallet'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    wallet = message.text.strip()
    if not is_valid_ton_wallet(wallet):
        await message.answer(LANGUAGES[language]['invalid_wallet'])
        return
        
    await state.update_data(ton_wallet=wallet)
    a, b = random.randint(1, 20), random.randint(1, 20)
    await state.update_data(captcha_answer=a + b)
    await state.set_state(WithdrawStates.waiting_for_captcha)
    await message.answer(LANGUAGES[language]['captcha_prompt'].format(a=a, b=b), reply_markup=get_cancel_keyboard(language))

@router.message(WithdrawStates.waiting_for_captcha)
async def captcha_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    
    if message.text == LANGUAGES[language]['cancel']:
        await state.clear()
        await message.answer(LANGUAGES[language]['cancel'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    if message.text in [LANGUAGES[language]['main_menu']['withdraw'], LANGUAGES[language]['main_menu']['profile'], LANGUAGES[language]['main_menu']['earn'], LANGUAGES[language]['main_menu']['daily_bonus'], LANGUAGES[language]['main_menu']['top_users']]:
        await state.clear()
        await message.answer(LANGUAGES[language]['invalid_wallet'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    data = await state.get_data()
    correct = data.get("captcha_answer")
    try:
        if int(message.text.strip()) != correct:
            await message.answer(LANGUAGES[language]['invalid_captcha'])
            return
    except:
        await message.answer(LANGUAGES[language]['captcha_number_only'])
        return
        
    await state.set_state(WithdrawStates.waiting_for_amount)
    await message.answer(LANGUAGES[language]['withdraw_amount'], reply_markup=get_cancel_keyboard(language))

@router.message(WithdrawStates.waiting_for_amount)
async def withdraw_amount_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language, balance FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
        balance = result[1]
    
    if message.text == LANGUAGES[language]['cancel']:
        await state.clear()
        await message.answer(LANGUAGES[language]['cancel'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    if message.text in [LANGUAGES[language]['main_menu']['withdraw'], LANGUAGES[language]['main_menu']['profile'], LANGUAGES[language]['main_menu']['earn'], LANGUAGES[language]['main_menu']['daily_bonus'], LANGUAGES[language]['main_menu']['top_users']]:
        await state.clear()
        await message.answer(LANGUAGES[language]['invalid_wallet'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await message.answer(LANGUAGES[language]['invalid_amount'])
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
        user = await cur.fetchone()
        if not user:
            await message.answer(LANGUAGES[language]['not_registered'])
            await state.clear()
            return
        if amount > balance:
            await message.answer(LANGUAGES[language]['insufficient_balance'].format(balance=balance))
            return

    raw_random_data = uuid.uuid4()
    memo = "order_" + str(raw_random_data)[:11].replace("-", "")
    
    await state.update_data(amount=amount, memo=memo)
    await state.set_state(WithdrawStates.waiting_for_verify)
    
    await message.answer(
        LANGUAGES[language]['payment_instruction'].format(fee=BLOCKCHAIN_FEE, wallet=PAYMENT_WALLET, memo=memo),
        parse_mode="Markdown",
        reply_markup=get_verify_keyboard()
    )

@router.message(WithdrawStates.waiting_for_verify)
async def verify_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    
    if message.text == LANGUAGES[language]['cancel']:
        await state.clear()
        await message.answer(LANGUAGES[language]['cancel'], reply_markup=get_main_keyboard(user_id, language))
        return
        
    if message.text != "/verify":
        await message.answer(LANGUAGES[language]['verify_prompt'])
        return
        
    data = await state.get_data()
    memo = data.get('memo')
    amount = data.get('amount')
    wallet = data.get('ton_wallet')
    
    await message.answer(LANGUAGES[language]['payment_checking'])
    
    payment_info = await check_payment(memo)
    
    if payment_info:
        await message.answer(
            LANGUAGES[language]['payment_confirmed'].format(amount=payment_info['amount_ton'], tx_id=payment_info['tx_id'][:8]),
            reply_markup=get_main_keyboard(user_id, language)
        )
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                'UPDATE users SET balance = balance - ?, ton_wallet = ? WHERE user_id = ?',
                (amount, wallet, user_id)
            )
            await db.commit()
        
        success = await process_trc_withdrawal(wallet, amount, memo)
        
        if success:
            await message.answer(
                LANGUAGES[language]['payment_success'].format(amount=amount, wallet=wallet)
            )
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                    (amount, user_id)
                )
                await db.commit()
                
            await message.answer(
                LANGUAGES[language]['payment_failed'].format(amount=amount)
            )
    else:
        await message.answer(
            LANGUAGES[language]['payment_not_found'].format(memo=memo)
        )
        return
        
    await state.clear()

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['daily_bonus'], LANGUAGES['ru']['main_menu']['daily_bonus']}))
async def daily_bonus(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    now = datetime.now(timezone.utc)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language, last_bonus_time FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        if not result:
            await message.answer(LANGUAGES['en']['not_registered'])
            return
        language, last_bonus_time = result
        language = language if language in ['en', 'ru'] else 'en'

    if last_bonus_time:
        last_time = datetime.fromisoformat(last_bonus_time)
        next_time = last_time + timedelta(hours=12)
        if now < next_time:
            remain = next_time - now
            time_str = str(remain).split(".")[0]
            await message.answer(
                LANGUAGES[language]['daily_bonus_prompt'].format(time=time_str),
                reply_markup=get_calm_inline_keyboard(),
                parse_mode="HTML"
            )
            return

    await message.answer(
        LANGUAGES[language]['daily_bonus_ready'],
        reply_markup=get_calm_inline_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "calm_bonus")
async def calm_bonus_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    now = datetime.now(timezone.utc)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language, last_bonus_time, balance FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        if not result:
            await callback.message.answer(LANGUAGES['en']['not_registered'])
            return
        language, last_bonus_time, balance = result
        language = language if language in ['en', 'ru'] else 'en'

        if last_bonus_time:
            last_time = datetime.fromisoformat(last_bonus_time)
            if now < last_time + timedelta(hours=12):
                remain = last_time + timedelta(hours=12) - now
                time_str = str(remain).split(".")[0]
                await callback.message.edit_text(
                    LANGUAGES[language]['daily_bonus_not_ready'].format(time=time_str),
                    parse_mode="HTML"
                )
                return

        animation_frames = [
            "Loading...\n▢▢▢▢▢▢▢▢▢▢ 0%",
            "Loading...\n▇▢▢▢▢▢▢▢▢▢ 10%",
            "Loading...\n▇▇▢▢▢▢▢▢▢▢ 20%",
            "Loading...\n▇▇▇▢▢▢▢▢▢▢ 30%",
            "Loading...\n▇▇▇▇▢▢▢▢▢▢ 40%",
            "Loading...\n▇▇▇▇▇▢▢▢▢▢ 50%",
            "Loading...\n▇▇▇▇▇▇▢▢▢▢ 60%",
            "Loading...\n▇▇▇▇▇▇▇▢▢▢ 70%",
            "Loading...\n▇▇▇▇▇▇▇▇▢▢ 80%",
            "Loading...\n▇▇▇▇▇▇▇▇▇▢ 90%",
            "Loading...\n▇▇▇▇▇▇▇▇▇▇ 100%",
        ]

        for frame in animation_frames:
            await callback.message.edit_text(frame)
            await asyncio.sleep(0.15)

        new_balance = balance + 3000
        await db.execute('UPDATE users SET balance = ?, last_bonus_time = ? WHERE user_id=?',
                         (new_balance, now.isoformat(), user_id))
        await db.commit()

        await callback.message.edit_text(
            LANGUAGES[language]['daily_bonus_received'],
            parse_mode="HTML"
        )

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['top_users'], LANGUAGES['ru']['main_menu']['top_users']}))
async def top_users_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
        
        cur = await db.execute('''
            SELECT u.username, u.balance, COUNT(r.user_id) as referrals
            FROM users u
            LEFT JOIN users r ON r.referred_by = u.user_id
            GROUP BY u.user_id
            ORDER BY u.balance DESC
            LIMIT 10
        ''')
        top_users = await cur.fetchall()

    msg_text = LANGUAGES[language]['top_users'].format(users_list="")
    users_list = ""
    for idx, user in enumerate(top_users, start=1):
        username = user[0]
        balance = user[1]
        referrals = user[2]
        user_line = f"{idx}. 👤 "
        if username:
            user_line += f"@{username}\n"
        else:
            user_line += "NoUsername\n"
        user_line += f"   💰 Balance: {balance:,} $TRC\n"
        user_line += f"   👥 Referrals: {referrals}\n\n"
        users_list += user_line
    msg_text = LANGUAGES[language]['top_users'].format(users_list=users_list.strip())
    await message.answer(msg_text)

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['admin_panel'], LANGUAGES['ru']['main_menu']['admin_panel']}))
async def admin_panel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
        
        cur1 = await db.execute('SELECT COUNT(*) FROM users')
        user_count = (await cur1.fetchone())[0]
        cur2 = await db.execute('SELECT SUM(balance) FROM users')
        total_balance = (await cur2.fetchone())[0] or 0
        cur3 = await db.execute('''
            SELECT referred_by, COUNT(*) as total_refs 
            FROM users 
            WHERE referred_by IS NOT NULL 
            GROUP BY referred_by 
            ORDER BY total_refs DESC 
            LIMIT 3
        ''')
        top_refs = await cur3.fetchall()

    buttons = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Send Message")],
            [KeyboardButton(text="➕ Place Ad")],
            [KeyboardButton(text="🗑 Delete Ad")],
            [KeyboardButton(text="Ad Performance")],
            [KeyboardButton(text="⬅️ Back")]
        ],
        resize_keyboard=True
    )

    top_refs_text = ""
    for ref in top_refs:
        top_refs_text += f"ID: {ref[0]} — {ref[1]} referrals\n"
    
    msg = LANGUAGES[language]['admin_panel'].format(user_count=user_count, total_balance=total_balance, top_refs=top_refs_text)
    await message.answer(msg, reply_markup=buttons)

@router.message(F.text == "⬅️ Back")
async def back_to_main(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await message.answer(LANGUAGES[language]['cancel'], reply_markup=get_main_keyboard(user_id, language))

@router.message(F.text == "📢 Send Message")
async def start_broadcast(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await message.answer(LANGUAGES[language]['broadcast_prompt'])
    await state.set_state(BroadcastMessage.waiting_for_text)

@router.message(BroadcastMessage.waiting_for_text)
async def broadcast_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()
    for user in users:
        try:
            await message.bot.send_message(user[0], message.text)
        except TelegramForbiddenError:
            pass
    await message.answer(LANGUAGES[language]['broadcast_sent'])

@router.message(F.text == "➕ Place Ad")
async def start_ad_placement(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await message.answer(LANGUAGES[language]['ad_start'])
    await state.set_state(AddAdState.waiting_for_link)

@router.message(AddAdState.waiting_for_link)
async def receive_ad_link(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    await state.update_data(link=message.text)
    await message.answer(LANGUAGES[language]['ad_reward'])
    await state.set_state(AddAdState.waiting_for_reward)

@router.message(AddAdState.waiting_for_reward)
async def receive_ad_reward(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    try:
        reward = int(message.text)
        if reward <= 0:
            await message.answer(LANGUAGES[language]['invalid_reward'])
            return
    except ValueError:
        await message.answer(LANGUAGES[language]['invalid_number'])
        return
    await state.update_data(reward=reward)
    await message.answer(LANGUAGES[language]['ad_limit'])
    await state.set_state(AddAdState.waiting_for_limit)

@router.message(AddAdState.waiting_for_limit)
async def receive_ad_limit(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    try:
        trc_limit = int(message.text)
        if trc_limit <= 0:
            await message.answer(LANGUAGES[language]['invalid_limit'])
            return
    except ValueError:
        await message.answer(LANGUAGES[language]['invalid_number'])
        return
    await state.update_data(trc_limit=trc_limit)
    await message.answer(LANGUAGES[language]['ad_description'])
    await state.set_state(AddAdState.waiting_for_description)

@router.message(AddAdState.waiting_for_description)
async def receive_ad_description(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    if not message.text.strip():
        await message.answer(LANGUAGES[language]['invalid_description'])
        return
    await state.update_data(description=message.text)
    await message.answer(LANGUAGES[language]['ad_photo'])
    await state.set_state(AddAdState.waiting_for_photo)

@router.message(AddAdState.waiting_for_photo, F.photo)
async def receive_ad_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    ad = {
        "link": data["link"],
        "reward": data["reward"],
        "trc_limit": data["trc_limit"],
        "trc_given": 0,
        "limit_removed": False,
        "description": data["description"],
        "photo_id": file_id,
        "join_count": 0
    }
    ads_data.append(ad)
    await state.clear()

    text = LANGUAGES[language]['ad_placed'].format(link=ad['link'], reward=ad['reward'], description=ad['description'])
    try:
        await message.bot.send_photo(chat_id=ADMIN_ID, photo=ad["photo_id"], caption=text)
    except Exception as e:
        await message.answer(f"Error sending ad to admin: {str(e)}")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, language FROM users") as cursor:
            users = await cursor.fetchall()

    for user in users:
        try:
            user_language = user[1] if user[1] in ['en', 'ru'] else 'en'
            await message.bot.send_photo(
                chat_id=user[0],
                photo=ad["photo_id"],
                caption=LANGUAGES[user_language]['ad_notification'].format(reward=ad['reward'])
            )
        except TelegramForbiddenError:
            continue

    await message.answer(LANGUAGES[language]['ad_placed'].format(link=ad['link'], reward=ad['reward'], description=ad['description']))

@router.message(F.text == "🗑 Delete Ad")
async def start_delete_ad(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    if not ads_data:
        await message.answer(LANGUAGES[language]['ad_no_ads'])
        return
    
    buttons = [
        [InlineKeyboardButton(text=f"{ad['link']}", callback_data=f"delete_ad_{i}")]
        for i, ad in enumerate(ads_data)
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_admin")])
    
    await message.answer(
        LANGUAGES[language]['ad_select'],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("delete_ad_"))
async def delete_ad(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    ad_index = int(callback.data.replace("delete_ad_", ""))
    try:
        removed_ad = ads_data.pop(ad_index)
        await callback.message.answer(LANGUAGES[language]['ad_deleted'].format(link=removed_ad['link']))
        await callback.message.edit_reply_markup(reply_markup=None)
    except IndexError:
        await callback.message.answer("Error: Ad not found.")
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
        
        cur1 = await db.execute('SELECT COUNT(*) FROM users')
        user_count = (await cur1.fetchone())[0]
        cur2 = await db.execute('SELECT SUM(balance) FROM users')
        total_balance = (await cur2.fetchone())[0] or 0
        cur3 = await db.execute('''
            SELECT referred_by, COUNT(*) as total_refs 
            FROM users 
            WHERE referred_by IS NOT NULL 
            GROUP BY referred_by 
            ORDER BY total_refs DESC 
            LIMIT 3
        ''')
        top_refs = await cur3.fetchall()

    buttons = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Send Message")],
            [KeyboardButton(text="➕ Place Ad")],
            [KeyboardButton(text="🗑 Delete Ad")],
            [KeyboardButton(text="Ad Performance")],
            [KeyboardButton(text="⬅️ Back")]
        ],
        resize_keyboard=True
    )

    top_refs_text = ""
    for ref in top_refs:
        top_refs_text += f"ID: {ref[0]} — {ref[1]} referrals\n"

    msg = LANGUAGES[language]['admin_panel'].format(user_count=user_count, total_balance=total_balance, top_refs=top_refs_text)
    await callback.message.answer(msg, reply_markup=buttons)
    await callback.message.delete()
    await callback.answer()

@router.message(F.text == "Ad Performance")
async def ad_statistics(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
    if not ads_data:
        await message.answer(LANGUAGES[language]['ad_no_ads'])
        return
    stats = ""
    for ad in ads_data:
        stats += f"Channel: {ad['link']}\n"
        stats += f"Joins: {ad.get('join_count', 0)}\n"
        stats += f"TRC Given: {ad.get('trc_given', 0)} / "
        stats += f"{ad['trc_limit'] if not ad.get('limit_removed', False) else 'No Limit'}\n\n"
    await message.answer(LANGUAGES[language]['ad_stats'].format(stats=stats))

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['earn'], LANGUAGES['ru']['main_menu']['earn']}))
async def earn_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language, earned_channels FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        language = result[0] if result and result[0] in ['en', 'ru'] else 'en'
        user_channels = result[1].split(",") if result and result[1] else []

    found = False
    for ad in ads_data.copy():
        if ad["link"] not in user_channels:
            found = True
            caption = LANGUAGES[language]['earn_caption'].format(reward=ad['reward'], link=ad['link'], description=ad['description'])
            try:
                await message.bot.send_photo(
                    chat_id=user_id,
                    photo=ad["photo_id"],
                    caption=caption,
                    reply_markup=get_earn_keyboard()
                )
            except TelegramForbiddenError:
                continue

    if not found:
        await message.answer(LANGUAGES[language]['earn_no_ads'], reply_markup=get_main_keyboard(user_id, language))

@router.callback_query(F.data == "check_earn")
async def check_earn_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language, earned_channels, balance FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        if not result:
            await callback.message.answer(LANGUAGES['en']['not_registered'])
            return
        language, earned_channels, balance = result
        language = language if language in ['en', 'ru'] else 'en'
        user_channels = earned_channels.split(",") if earned_channels else []

    # Bosilgan xabardan kanal linkini olish
    message_text = callback.message.caption or ""
    link_match = re.search(r'https://t.me/[@a-zA-Z0-9_]+', message_text)
    if not link_match:
        await callback.message.answer(LANGUAGES[language]['earn_error'].format(link="Unknown", error="Kanal linki topilmadi"))
        await callback.answer()
        return

    channel_link = link_match.group(0)
    # ads_data dan mos kanalni topish
    ad = next((ad for ad in ads_data if ad["link"] == channel_link), None)
    if not ad:
        await callback.message.answer(LANGUAGES[language]['earn_error'].format(link=channel_link, error="Reklama topilmadi"))
        await callback.answer()
        return

    try:
        channel_username = ad["link"].replace("https://t.me/", "@").strip()
        member = await callback.bot.get_chat_member(channel_username, user_id)
        if member.status in ["member", "administrator", "creator"]:
            if ad["link"] not in user_channels:
                if not ad.get("limit_removed", False):
                    if ad.get("trc_given", 0) + ad["reward"] > ad["trc_limit"]:
                        await callback.message.answer(LANGUAGES[language]['earn_limit_reached'].format(link=ad['link']))
                        await callback.answer()
                        return
                # Balansni yangilash va kanalni qo‘shish
                new_channels = user_channels + [ad["link"]]
                ad["trc_given"] = ad.get("trc_given", 0) + ad["reward"]
                ad["join_count"] = ad.get("join_count", 0) + 1
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE users SET balance = ?, earned_channels = ? WHERE user_id = ?",
                        (balance + ad["reward"], ",".join(new_channels), user_id)
                    )
                    await db.commit()
                await callback.message.answer(f"✅ {ad['link']} awarded {ad['reward']} TRC")
            else:
                await callback.message.answer(LANGUAGES[language]['earn_already_received'].format(link=ad['link']))
        else:
            await callback.message.answer(LANGUAGES[language]['earn_not_subscribed'].format(link=ad['link']))
    except Exception as e:
        await callback.message.answer(LANGUAGES[language]['earn_error'].format(link=ad['link'], error=str(e)))

    await callback.message.answer(LANGUAGES[language]['earn_completed'], reply_markup=get_main_keyboard(user_id, language))
    await callback.answer()

@router.message(F.text.in_({LANGUAGES['en']['main_menu']['profile'], LANGUAGES['ru']['main_menu']['profile']}))
async def profile_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT language, balance, last_bonus_time FROM users WHERE user_id=?', (user_id,))
        result = await cur.fetchone()
        if not result:
            await message.answer(LANGUAGES['en']['not_registered'])
            return
        language, balance, last_bonus_time = result
        language = language if language in ['en', 'ru'] else 'en'
        cur = await db.execute('SELECT COUNT(*) FROM users WHERE referred_by=?', (user_id,))
        ref_count = (await cur.fetchone())[0]

    now = datetime.now(timezone.utc)
    bonus_status = "Not received" if language == 'en' else "Не получен"
    if last_bonus_time:
        try:
            last_time = datetime.fromisoformat(last_bonus_time)
            if now - last_time < timedelta(hours=12):
                bonus_status = "Received" if language == 'en' else "Получен"
        except:
            pass

    referral_link = f"https://t.me/Tronocoin_bot?start={user_id}"
    profile_line = f"👤 Profile: @{username}\n" if username else "👤 Profile\n"
    if language == 'ru':
        profile_line = f"👤 Профиль: @{username}\n" if username else "👤 Профиль\n"

    text = LANGUAGES[language]['profile'].format(
        profile_line=profile_line,
        balance=balance,
        ref_count=ref_count,
        bonus_status=bonus_status,
        referral_link=referral_link
    )
    await message.answer(text)

async def create_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            referred_by INTEGER,
            ton_wallet TEXT,
            earned_channels TEXT,
            last_bonus_time TEXT,
            last_withdraw INTEGER DEFAULT 0,
            language TEXT DEFAULT 'en'
        )''')
        await db.commit()

async def main():
    await create_db()
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())


