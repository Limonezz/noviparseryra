import asyncio
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events
import logging
import aiohttp
import feedparser

# ===== КОНФИГУРАЦИЯ ДЛЯ RSS БОТА =====
API_ID = os.environ.get('API_ID', '24826804')
API_HASH = os.environ.get('API_HASH', '048e59c243cce6ff788a7da214bf8119')
BOT_TOKEN = os.environ.get('BOT_TOKEN_RSS', '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY')

# ID чата для отправки сообщений
GROUP_CHAT_ID = 1003474109106

# Веб-сайты для парсинга
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
    },
    {
        'name': 'Московский Комсомолец',
        'url': 'https://www.mk.ru/rss/index.xml',
        'type': 'rss'
    },
    {
        'name': 'RT на русском',
        'url': 'https://russian.rt.com/rss/',
        'type': 'rss'
    },
    {
        'name': 'Аргументы и Факты', 
        'url': 'https://aif.ru/rss/news.php',
        'type': 'rss'
    }
]

# ===== ВЕЧНЫЕ ПОДПИСЧИКИ =====
PERMANENT_SUBSCRIBERS = [
    1175795428,
    8019965642,
]

# ===== КЛЮЧЕВЫЕ СЛОВА =====
WAR_KEYWORDS = [
    'обстрел', 'атака', 'прилет', 'диверсант', 'ДРГ', 'ракета', 'Искандер',
    'пленный', 'плен', 'РЭБ', 'наступление', 'контрнаступление',
    'окружение', 'штурм', 'артобстрел', 'миномет', 'артиллерия', 'танк', 'БМП', 'БТР',
    'беспилотник', 'дрон', 'FPV-дрон', 'Герань', 'Шахед', 'Ланцет',
    'С-300', 'С-400', 'Искандер', 'Калибр', 'Кинжал',
    'фортификация', 'укрепление', 'траншея', 'бункер',
    'ВСУ', 'ВС РФ', 'ЧВК', 'Вагнер', 'Ахмат', 'Кадыров', 'ССО', 'разведка', 'диверсия', 'спецоперация',
    'наемник', 'контрактник', 'мобилизация', 'мобилизованный',
    'НАТО', 'США', 'Пентагон', 'Байден', 'ЕС', 'санкция', 'эмбарго',
    'военная помощь', 'вооружение', 'оружие', 'F-16', 'Абрамс', 'Леопард', 'ПАТРИОТ',
    'Хаймарс', 'ПВО', 'ПРО',
    'Донбасс', 'ДНР', 'ЛНР', 'Крым', 'Севастополь', 'Херсон', 'Запорожье', 'Мариуполь', 'Бахмут',
    'Авдеевка', 'Лиман', 'Изюм', 'Купянск', 'Харьков',
    'Путин', 'президент', 'губернатор', 'правительство', 'Госдума',
    'законопроект', 'выборы', 'санкции', 'переговоры', 'дипломатия',
    'Медведев', 'Песков', 'Лавров', 'Шойгу', 'Герасимов',
    'бюджет', 'финансирование', 'госконтракт', 'оборонный заказ',
    'военно-промышленный комплекс', 'Ростех',
    'авария', 'катастрофа', 'обрушение', 'разрушение', 'взрыв', 'гибель', 'пострадавший',
    'уголовное дело', 'задержание', 'арест', 'суд', 'приговор',
    'АЭС', 'атомная станция', 'Курская АЭС-2', 'электроэнергия',
    'эвакуация', 'беженец', 'переселенец', 'гуманитарная помощь', 'военное положение'
]

SUBSCRIBERS_FILE = 'subscribers_rss.txt'

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rss_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RSSBot')

# ===== СИСТЕМА ПОДПИСЧИКОВ =====
def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            file_subs = [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        file_subs = []
    
    all_subs = list(set(PERMANENT_SUBSCRIBERS + file_subs))
    return all_subs

def save_subscribers(subscribers):
    regular_subs = [sub for sub in subscribers if sub not in PERMANENT_SUBSCRIBERS]
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            for user_id in regular_subs:
                f.write(f"{user_id}\n")
    except Exception as e:
        logger.error(f"Ошибка сохранения подписчиков: {e}")

def add_subscriber(user_id):
    subscribers = load_subscribers()
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        logger.info(f"Новый подписчик: {user_id}")
    return load_subscribers()

def remove_subscriber(user_id):
    if user_id in PERMANENT_SUBSCRIBERS:
        return load_subscribers()
    subscribers = load_subscribers()
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        logger.info(f"Отписался: {user_id}")
    return load_subscribers()

# ===== ФИЛЬТРЫ =====
def contains_war_keywords(text):
    if not text:
        return False
    text_lower = text.lower()
    for keyword in WAR_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('rss_news.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_posts (
            post_id TEXT PRIMARY KEY,
            channel TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def is_post_sent(conn, post_id):
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM sent_posts WHERE post_id = ?", (post_id,))
    return cursor.fetchone() is not None

def mark_post_sent(conn, post_id, channel, text):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO sent_posts (post_id, channel, text) VALUES (?, ?, ?)",
        (post_id, channel, text[:500] if text else "")
    )
    conn.commit()

# ===== RSS ПАРСИНГ =====
async def parse_rss_feed(website_config):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(website_config['url']) as response:
                content = await response.text()
                feed = feedparser.parse(content)
                articles = []
                for entry in feed.entries[:10]:
                    try:
                        title = entry.title
                        link = entry.link
                        summary = entry.get('summary', '') or entry.get('description', '') or title
                        full_text = f"{title} {summary}"
                        if contains_war_keywords(full_text):
                            articles.append({
                                'title': title,
                                'link': link,
                                'summary': summary,
                                'source': website_config['name'],
                                'text': full_text
                            })
                    except Exception:
                        continue
                return articles
    except Exception as e:
        logger.error(f"Ошибка RSS {website_config['name']}: {e}")
        return []

async def check_all_feeds(conn, client):
    try:
        logger.info("Начинаю проверку RSS лент...")
        for website in WEBSITES:
            articles = await parse_rss_feed(website)
            logger.info(f"{website['name']}: найдено {len(articles)} статей с ключевыми словами")
            for article in articles:
                article_id = f"rss_{hash(article['link']) % 100000000}"
                if not is_post_sent(conn, article_id):
                    # Отправляем в группу вместо подписчиков
                    message = f"📰 **{article['source']}**\n\n{article['title']}\n\n🔗 [Читать]({article['link']})"
                    try:
                        await client.send_message(GROUP_CHAT_ID, message, parse_mode='Markdown')
                        mark_post_sent(conn, article_id, article['source'], article['title'])
                        logger.info(f"📤 Отправлено {article['source']} в группу {GROUP_CHAT_ID}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки в группу: {e}")
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Ошибка проверки лент: {e}")

# ===== ОСНОВНОЙ БОТ =====
async def main():
    logger.info("Запуск RSS News Bot...")
    
    # Инициализация клиента для RSS бота (БЕЗ СЕССИИ - просто бот)
    client = TelegramClient(
        'rss_bot_session',  # Просто имя файла для сессии
        API_ID, 
        API_HASH
    )
    
    db_conn = init_db()
    subscribers = load_subscribers()
    logger.info(f"RSS News Bot запущен! Отправляем в группу: {GROUP_CHAT_ID}")

    # Команды бота
    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        subscribers = add_subscriber(user_id)
        await event.reply("✅ Подписан на RSS новости с сайтов!")
        logger.info(f"Новый подписчик: {user_id}")

    @client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        user_id = event.sender_id
        subscribers = remove_subscriber(user_id)
        await event.reply("❌ Отписан от RSS новостей")

    @client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        subscribers = load_subscribers()
        await event.reply(f"📊 Статистика RSS News Bot:\n\nПодписчиков: {len(subscribers)}\nМониторим сайтов: {len(WEBSITES)}\nГруппа: {GROUP_CHAT_ID}")

    @client.on(events.NewMessage(pattern='/test'))
    async def test_handler(event):
        await event.reply("🟢 RSS News Bot работает! Проверяю новости с сайтов...")

    @client.on(events.NewMessage(pattern='/check'))
    async def check_handler(event):
        await event.reply("🔄 Запускаю проверку RSS лент...")
        await check_all_feeds(db_conn, client)
        await event.reply("✅ Проверка завершена!")

    # Фоновая проверка RSS
    async def periodic_checker():
        while True:
            await check_all_feeds(db_conn, client)
            await asyncio.sleep(300)  # Проверка каждые 5 минут

    # Запуск
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("RSS News Bot успешно запущен!")
        logger.info(f"💬 Отправляем новости в группу: {GROUP_CHAT_ID}")
        
        # Уведомляем вечных подписчиков
        for user_id in PERMANENT_SUBSCRIBERS:
            try:
                await client.send_message(
                    user_id, 
                    f"🟢 RSS News Bot запущен!\n"
                    f"Мониторим {len(WEBSITES)} сайтов\n"
                    f"💬 Отправляем в группу: {GROUP_CHAT_ID}"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить {user_id}: {e}")
        
        # Запускаем задачи
        asyncio.create_task(periodic_checker())
        
        logger.info("Начинаю мониторинг RSS лент...")
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await client.disconnect()
        db_conn.close()

if __name__ == '__main__':
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            pass
    asyncio.run(main())
