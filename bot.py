import asyncio
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import logging
import re
from collections import Counter 
import html
import aiohttp
from bs4 import BeautifulSoup
import json
import feedparser

# ===== КОНФИГУРАЦИЯ =====
API_ID = 24826804  # убрал кавычки
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

# Telegram каналы (проверенные рабочие)
CHANNELS = [
    'rian_ru', 'RT_russian', 'meduzalive', 'bbbreaking', 
    'breakingmash', 'readovkanews', 'rian_ru', 'rupulse',
    'sputnik_results', 'tass_agency', 'vestiru'
]

# Веб-сайты для парсинга (только RSS)
WEBSITES = [
    {
        'name': 'РИА Новости',
        'url': 'https://ria.ru/export/rss2/archive/index.xml',
        'type': 'rss'
    },
    {
        'name': 'ТАСС',
        'url': 'https://tass.ru/rss/v2.xml',
        'type': 'rss'
    },
    {
        'name': 'Интерфакс',
        'url': 'https://www.interfax.ru/rss.asp',
        'type': 'rss'
    }
]

# ===== КЛЮЧЕВЫЕ СЛОВА ДЛЯ ФИЛЬТРАЦИИ =====
KEYWORDS = [
    'Курск', 'Курская область', 'Брянск', 'Брянская область', 
    'Белгород', 'Белгородская область', 'Украина', 'Россия',
    'США', 'НАТО', 'санкции', 'война', 'обстрел', 'атака',
    'Путин', 'Зеленский', 'правительство', 'администрация',
    'бюджет', 'финансирование', 'коррупция', 'авария', 'катастрофа',
    'полиция', 'суд', 'арест', 'задержание', 'Москва', 'Киев'
]

SUBSCRIBERS_FILE = 'subscribers.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== ФУНКЦИИ ДЛЯ ПОДПИСЧИКОВ =====
def load_subscribers():
    """Загрузка списка подписчиков"""
    try:
        if not os.path.exists(SUBSCRIBERS_FILE):
            return []
        with open(SUBSCRIBERS_FILE, 'r') as f:
            subscribers = []
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    subscribers.append(int(line))
            return subscribers
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки подписчиков: {e}")
        return []

def save_subscribers(subscribers):
    """Сохранение списка подписчиков"""
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            for user_id in subscribers:
                f.write(f"{user_id}\n")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения подписчиков: {e}")

def add_subscriber(user_id):
    """Добавление подписчика"""
    subscribers = load_subscribers()
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        logger.info(f"✅ Новый подписчик: {user_id}")
        return True
    return False

def remove_subscriber(user_id):
    """Удаление подписчика"""
    subscribers = load_subscribers()
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        logger.info(f"❌ Отписался: {user_id}")
        return True
    return False

# ===== ФУНКЦИИ ФИЛЬТРАЦИИ =====
def contains_keywords(text):
    """Проверяет, содержит ли текст ключевые слова"""
    if not text:
        return False
        
    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword.lower() in text_lower:
            logger.info(f"✅ Найдено ключевое слово: {keyword}")
            return True
    return False

def is_spam_message(text):
    """Упрощенная проверка на спам"""
    if not text:
        return True
        
    text_lower = text.lower()
    
    # Очевидный спам
    spam_phrases = [
        'бесплатно', 'купить', 'продать', 'заказать', 'скидка', 'акция',
        'реклама', 'коммерция', 'озон', 'wildberries', 'накрутка',
        'подписчиков', 'лайков', 'диплом', 'курсовая'
    ]
    
    for phrase in spam_phrases:
        if phrase in text_lower:
            return True
    
    # Слишком много ссылок
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    if len(urls) > 3:
        return True
    
    return False

# ===== БАЗА ДАННЫХ =====
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('news.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parsed_posts (
            post_id TEXT PRIMARY KEY,
            channel TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def is_post_sent(conn, post_id):
    """Проверка, отправлялся ли пост"""
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM parsed_posts WHERE post_id = ?", (post_id,))
    return cursor.fetchone() is not None

def mark_post_as_sent(conn, post_id, channel, text):
    """Пометить пост как отправленный"""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO parsed_posts (post_id, channel, text) VALUES (?, ?, ?)",
        (post_id, channel, text)
    )
    conn.commit()

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С СООБЩЕНИЯМИ =====
def format_message(text, source, url=None):
    """Форматирование сообщения для отправки"""
    # Обрезаем текст если слишком длинный
    if len(text) > 1000:
        text = text[:1000] + "..."
    
    if url:
        return f"📰 **{source}**\n\n{text}\n\n🔗 [Читать далее]({url})"
    else:
        return f"📰 **{source}**\n\n{text}"

# ===== ПАРСИНГ САЙТОВ =====
async def parse_rss_feed(feed_url):
    """Парсинг RSS ленты"""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        
        for entry in feed.entries[:5]:  # Берем 5 последних статей
            try:
                title = entry.title
                link = entry.link
                summary = entry.get('summary', '') or entry.get('description', '')
                
                # Объединяем заголовок и описание для проверки
                full_text = f"{title} {summary}"
                
                if contains_keywords(full_text) and not is_spam_message(full_text):
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'text': full_text
                    })
                    
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга элемента RSS: {e}")
                continue
                
        return articles
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга RSS: {e}")
        return []

async def check_all_feeds(conn, bot):
    """Проверка всех RSS лент"""
    try:
        for website in WEBSITES:
            logger.info(f"🔍 Проверяем {website['name']}")
            
            articles = await parse_rss_feed(website['url'])
            logger.info(f"📄 Найдено статей на {website['name']}: {len(articles)}")
            
            for article in articles:
                # Создаем ID на основе ссылки
                article_id = f"rss_{hash(article['link']) % 1000000}"
                
                if not is_post_sent(conn, article_id):
                    # Отправляем подписчикам
                    subscribers = load_subscribers()
                    message = format_message(
                        f"{article['title']}\n\n{article['summary']}", 
                        website['name'], 
                        article['link']
                    )
                    
                    sent_count = 0
                    for user_id in subscribers:
                        try:
                            await bot.send_message(user_id, message, parse_mode='Markdown')
                            sent_count += 1
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
                    
                    if sent_count > 0:
                        mark_post_as_sent(conn, article_id, website['name'], article['title'])
                        logger.info(f"✅ Отправлено {sent_count} подписчикам с {website['name']}")
            
            await asyncio.sleep(2)  # Пауза между сайтами
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки лент: {e}")

# ===== ОБРАБОТКА TELEGRAM КАНАЛОВ =====
async def handle_channel_message(event, conn, bot):
    """Обработка сообщения из канала"""
    try:
        message = event.message
        if not message.text:
            return
            
        text = message.text
        chat = await event.get_chat()
        channel_name = chat.username or chat.title
        
        logger.info(f"📨 Сообщение из {channel_name}: {text[:100]}...")
        
        # Проверяем на спам и релевантность
        if is_spam_message(text) or not contains_keywords(text):
            return
        
        # Создаем ID сообщения
        message_id = f"tg_{channel_name}_{message.id}"
        
        # Проверяем, не отправляли ли уже
        if is_post_sent(conn, message_id):
            return
        
        # Форматируем и отправляем
        subscribers = load_subscribers()
        message_text = format_message(text, channel_name)
        
        sent_count = 0
        for user_id in subscribers:
            try:
                await bot.send_message(user_id, message_text, parse_mode='Markdown')
                sent_count += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
        
        if sent_count > 0:
            mark_post_as_sent(conn, message_id, channel_name, text)
            logger.info(f"✅ Переслано сообщение из {channel_name} для {sent_count} подписчиков")
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
async def main():
    """Главная функция"""
    # Инициализация клиентов
    user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    bot_client = TelegramClient('bot', API_ID, API_HASH)
    
    # Инициализация БД
    db_conn = init_db()
    
    # Обработчики команд для бота
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        if add_subscriber(user_id):
            await event.reply(
                "🎉 **Добро пожаловать!**\n\n"
                "Вы подписались на новостную рассылку. "
                "Теперь вы будете получать актуальные новости.\n\n"
                "Используйте /stop чтобы отписаться."
            )
        else:
            await event.reply("✅ Вы уже подписаны на рассылку!")
    
    @bot_client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        user_id = event.sender_id
        if remove_subscriber(user_id):
            await event.reply("❌ Вы отписались от рассылки.")
        else:
            await event.reply("ℹ️ Вы не были подписаны.")
    
    @bot_client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        subscribers = load_subscribers()
        await event.reply(f"📊 Статистика:\n👥 Подписчиков: {len(subscribers)}")
    
    @bot_client.on(events.NewMessage(pattern='/test'))
    async def test_handler(event):
        """Тестовая команда для проверки работы"""
        await event.reply("🤖 Бот работает! Ожидайте новости...")
    
    # Обработчик для каналов
    @user_client.on(events.NewMessage(chats=CHANNELS))
    async def channel_message_handler(event):
        await handle_channel_message(event, db_conn, bot_client)
    
    async def rss_checker():
        """Фоновая задача для проверки RSS"""
        while True:
            try:
                logger.info("🔄 Проверка RSS лент...")
                await check_all_feeds(db_conn, bot_client)
                logger.info("💤 Следующая проверка через 10 минут")
                await asyncio.sleep(600)  # 10 минут
            except Exception as e:
                logger.error(f"❌ Ошибка в RSS чекере: {e}")
                await asyncio.sleep(60)
    
    # Запуск бота
    try:
        logger.info("🚀 Запуск бота...")
        
        # Запускаем клиенты
        await bot_client.start(bot_token=BOT_TOKEN)
        await user_client.start()
        
        # Проверяем подписчиков
        subscribers = load_subscribers()
        logger.info(f"👥 Загружено подписчиков: {len(subscribers)}")
        
        # Запускаем фоновые задачи
        asyncio.create_task(rss_checker())
        
        logger.info("✅ Бот успешно запущен!")
        logger.info(f"📊 Мониторим {len(CHANNELS)} каналов и {len(WEBSITES)} сайтов")
        
        # Бесконечный цикл
        await asyncio.Future()
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        await user_client.disconnect()
        await bot_client.disconnect()
        db_conn.close()

if __name__ == '__main__':
    # Создаем файлы если их нет
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'w') as f:
            pass
    
    # Запускаем бота
    asyncio.run(main())
