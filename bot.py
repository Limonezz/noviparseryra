import asyncio
import sqlite3
import os
from datetime import datetime
import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import logging
import time as time_module

# ===== КОНФИГУРАЦИЯ =====
# Для парсинга (пользовательский аккаунт)
API_ID = '24826804'
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="  # получите из generate_session.py

# Для отправки (бот)
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

CHANNELS = [
    'gubernator_46', 'kursk_info46', 'Alekhin_Telega', 'rian_ru',
    'kursk_ak46', 'zhest_kursk_146', 'novosti_efir', 'kursk_tipich',
    'seymkursk', 'kursk_smi', 'kursk_russia', 'belgorod01', 'kurskadm',
    'Avtokadr46', 'kurskbomond', 'prigranichie_radar1', 'grohot_pgr',
    'kursk_nasv', 'mchs_46', 'patriot046', 'kursk_now', 'Hinshtein',
    'incidentkursk', 'zhest_belgorod', 'Pogoda_Kursk', 'pb_032',
    'tipicl32', 'bryansk_smi'
]

SUBSCRIBERS_FILE = 'subscribers.txt'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== ФУНКЦИИ ДЛЯ ПОДПИСЧИКОВ =====
def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        return []

def save_subscribers(subscribers):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        for user_id in subscribers:
            f.write(f"{user_id}\n")

def add_subscriber(user_id):
    subscribers = load_subscribers()
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        logger.info(f"✅ Новый подписчик: {user_id}")
    return subscribers

def remove_subscriber(user_id):
    subscribers = load_subscribers()
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        logger.info(f"❌ Отписался: {user_id}")
    return subscribers

# ===== ФУНКЦИИ ДЛЯ РАССЫЛКИ =====
def init_db():
    conn = sqlite3.connect('news.db')  # Используем файл для persistence
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parsed_posts (
            post_id TEXT PRIMARY KEY,
            channel TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    return conn

def is_post_sent(conn, post_id):
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM parsed_posts WHERE post_id = ?", (post_id,))
    return cursor.fetchone() is not None

def mark_post_as_sent(conn, post_id, channel, text):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO parsed_posts (post_id, channel, text) VALUES (?, ?, ?)",
        (post_id, channel, text)
    )
    conn.commit()

def generate_post_id(channel_name, message_id):
    return f"{channel_name}_{message_id}"

async def parse_channel(user_client, channel_name, conn):
    """Парсим каналы через пользовательский аккаунт"""
    try:
        logger.info(f"🔍 Парсим канал: {channel_name}")
        messages = await user_client.get_messages(channel_name, limit=5)
        new_posts = []
        
        for message in messages:
            if not message.text or not message.text.strip():
                continue
            
            post_id = generate_post_id(channel_name, message.id)
            
            if not is_post_sent(conn, post_id):
                post_text = message.text.strip()
                if len(post_text) > 1000:
                    post_text = post_text[:1000] + "..."
                
                formatted_post = f"📢 **{channel_name}**\n\n{post_text}\n\n🕒 *Время публикации:* {message.date.astimezone(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')}"
                
                new_posts.append({
                    'text': formatted_post,
                    'post_id': post_id,
                    'channel': channel_name
                })
                
                mark_post_as_sent(conn, post_id, channel_name, message.text)
                
                if len(new_posts) >= 2:  # Максимум 2 новости с канала
                    break
        
        return new_posts
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга {channel_name}: {e}")
        return []

async def send_news_to_user(bot_client, user_id, posts):
    """Отправляем новости через бота"""
    if not posts:
        return
    
    moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')
    
    try:
        await bot_client.send_message(
            user_id,
            f"📊 **СВЕЖИЕ НОВОСТИ**\n"
            f"🕒 *Актуально на:* {moscow_time} (МСК)\n"
            f"📈 *Всего новостей:* {len(posts)}\n"
            f"────────────────",
            parse_mode='md'
        )
        
        for post in posts:
            await bot_client.send_message(user_id, post['text'], parse_mode='md')
            await asyncio.sleep(1)  # Anti-flood
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")

async def collect_news(user_client):
    """Собираем новости через пользовательский аккаунт"""
    db_conn = init_db()
    all_news = []
    
    for channel in CHANNELS:
        try:
            channel_news = await parse_channel(user_client, channel, db_conn)
            all_news.extend(channel_news)
            await asyncio.sleep(2)  # Anti-flood для парсинга
        except Exception as e:
            logger.error(f"❌ Ошибка канала {channel}: {e}")
    
    db_conn.close()
    return all_news

async def send_news_to_all_subscribers(user_client, bot_client):
    """Основная функция рассылки"""
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("📭 Нет подписчиков для отправки")
        return
    
    logger.info(f"📨 Начинаем отправку для {len(subscribers)} подписчиков")
    
    # Собираем новости через пользовательский аккаунт
    all_news = await collect_news(user_client)
    
    if not all_news:
        logger.info("📭 Нет новых новостей")
        return
    
    # Отправляем через бота
    for user_id in subscribers:
        try:
            await send_news_to_user(bot_client, user_id, all_news)
            logger.info(f"✅ Отправили пользователю {user_id}")
            await asyncio.sleep(1)  # Anti-flood для отправки
        except Exception as e:
            logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
    
    logger.info(f"✅ Отправка завершена для {len(subscribers)} подписчиков")

def should_send_news():
    """Проверяем, нужно ли сейчас рассылать новости"""
    moscow_time = datetime.now(pytz.timezone('Europe/Moscow'))
    current_hour = moscow_time.hour
    current_minute = moscow_time.minute
    return current_hour in [9, 13, 19] and current_minute == 0

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
async def main():
    # Клиент для парсинга (пользователь)
    user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    # Клиент для отправки (бот)
    bot_client = TelegramClient('bot_session', API_ID, API_HASH)
    
    # Обработчики команд для бота
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.chat_id
        add_subscriber(user_id)
        await event.reply("🎉 Вы подписались на ежедневные новости! Вы будете получать сводку в 9:00, 13:00 и 19:00 по МСК.")
    
    @bot_client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        user_id = event.chat_id
        remove_subscriber(user_id)
        await event.reply("❌ Вы отписались от новостей")
    
    @bot_client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        subscribers = load_subscribers()
        await event.reply(f"📊 Подписчиков: {len(subscribers)}")
    
    @bot_client.on(events.NewMessage(pattern='/news'))
    async def news_handler(event):
        user_id = event.chat_id
        await event.reply("⏳ Запрашиваю свежие новости...")
        all_news = await collect_news(user_client)
        await send_news_to_user(bot_client, user_id, all_news)
    
    try:
        # Запускаем оба клиента
        await user_client.start()
        await bot_client.start(bot_token=BOT_TOKEN)
        
        logger.info("✅ Оба клиента запущены")
        logger.info(f"🤖 Парсинг от: {await user_client.get_me()}")
        logger.info(f"🤖 Бот: {await bot_client.get_me()}")
        
        # Бесконечный цикл для проверки времени
        while True:
            if should_send_news():
                logger.info("🕒 Время рассылать новости!")
                await send_news_to_all_subscribers(user_client, bot_client)
                # Ждем 2 минуты после рассылки чтобы не спамить
                await asyncio.sleep(120)
            
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        await user_client.disconnect()
        await bot_client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())