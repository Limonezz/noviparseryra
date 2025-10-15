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
API_ID = '24826804'
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

# Telegram каналы
CHANNELS = [
    'gubernator_46', 'kursk_info46', 'Alekhin_Telega', 'rian_ru',
    'kursk_ak46', 'zhest_kursk_146', 'novosti_efir', 'kursk_tipich',
    'seymkursk', 'kursk_smi', 'kursk_russia', 'belgorod01', 'kurskadm',
    'incident46', 'kurskbomond', 'prigranichie_radar1', 'grohot_pgr',
    'kursk_nasv', 'mchs_46', 'patriot046', 'kursk_now', 'Hinshtein',
    'incidentkursk', 'zhest_belgorod', 'RVvoenkor', 'pb_032',
    'tipicl32', 'bryansk_smi', 'Ria_novosti_rossiya','criminalru','bra_32','br_gorod','br_zhest', 'pravdas', 'wargonzo', 'ploschadmedia', 
    'belgorod_smi','ssigny','rucriminalinfo','kurskiy_harakter','dva_majors','ENews112',
]

# Веб-сайты для парсинга
WEBSITES = [
    # RSS-ленты (более надежные)
    {
        'name': 'Московский Комсомолец',
        'url': 'https://www.mk.ru/rss/index.xml',
        'type': 'rss',
        'base_url': 'https://www.mk.ru'
    },
    {
        'name': 'RT на русском',
        'url': 'https://russian.rt.com/rss/',
        'type': 'rss', 
        'base_url': 'https://russian.rt.com'
    },
    {
        'name': 'Аргументы и Факты',
        'url': 'https://aif.ru/rss/news.php',
        'type': 'rss',
        'base_url': 'https://aif.ru'
    },
]

# ===== КЛЮЧЕВЫЕ СЛОВА ДЛЯ ФИЛЬТРАЦИИ =====
KEYWORDS = [
    # Военная тематика
    'FPV-дрон', 'Герань', 'обстрел', 'атака', 'прилет', 'диверсанты', 'ДРГ',
    'фортификации', 'укрепления', 'боеприпасы', 'взрывчатка', 'ракета', 'Искандер',
    'пленные', 'плен', 'гуманитарная помощь', 'РЭБ', 'радиоэлектронная борьба',
    'приграничье',
    
    # Политика и власть
    'Путин', 'президент', 'губернатор', 'врио губернатора', 'правительство',
    'администрация', 'Госдума', 'Совет Федерации', 'законопроект', 'законодательство',
    'выборы', 'мэр', 'санкции', 'переговоры', 'дипломатия', 'международные отношения',
    'саммит', 'встречи', 'партия', 'Единая Россия', 'оппозиция', 'иноагент',
    
    # Экономика и коррупция
    'бюджет', 'финансирование', 'контракт', 'госконтракт', 'тендер', 'аукцион',
    'корпорация развития', 'инвестиции', 'субсидия', 'дотация', 'налог', 'НДС',
    'уклонение от налогов', 'штраф', 'пеня', 'банкротство', 'ликвидация',
    'имущество', 'арест имущества', 'конфискация', 'отмывание денег', 'схема',
    'махинации', 'хищение', 'растрата', 'взятка', 'откат', 'коррупция',
    'злоупотребление полномочиями', 'служебный подлог', 'мошенничество',
    
    # Строительство и инфраструктура
    'строительство', 'реконструкция', 'благоустройство', 'инфраструктура',
    'транспорт', 'дороги', 'энергетика', 'капремонт', 'объект', 'сооружение',
    'подрядчик', 'заказчик', 'смета', 'стоимость', 'сроки строительства',
    
    # Происшествия
    'авария', 'катастрофа', 'обрушение', 'разрушение', 'взрыв', 'детонация',
    'несчастный случай', 'травма', 'гибель', 'пострадавшие', 'больница', 'госпиталь',
    'полиция', 'правоохранители', 'уголовное дело', 'задержание', 'арест', 'суд',
    'судебное заседание', 'приговор', 'колония', 'СИЗО', 'следствие', 'дознание',
    
    # География
    'Курск', 'Курская область', 'Брянск', 'Брянская область', 'Белгород',
    'Белгородская область', 'Воронеж', 'Воронежская область', 'Москва',
    'Московская область', 'Санкт-Петербург', 'Краснодарский край', 'Крым',
    'Севастополь', 'Донбасс', 'ДНР', 'ЛНР', 'приграничные районы', 'Сумская область',
    'Поныровский район', 'Рыльский район', 'Шебекинский район', 'Валуйский район',
    
    # Международные отношения
    'США', 'Вашингтон', 'Китай', 'Пекин', 'Украина', 'Киев', 'НАТО', 'альянс',
    'ЕС', 'Европейский союз', 'ШОС', 'БРИКС', 'ООН', 'Совет Безопасности',
    'Турция', 'Германия', 'Франция', 'Польша', 'страны Балтии', 'санкции',
    
    # Общество
    'образование', 'школы', 'здравоохранение', 'больницы', 'общественные организации',
    'СМИ', 'журналисты', 'телеграм-каналы', 'блогеры', 'информационная безопасность',
    
    # Энергетика и промышленность
    'АЭС', 'атомная станция', 'Курская АЭС-2', 'Нововоронежская АЭС', 'электроэнергия',
    'газ', 'нефть', 'нефтепереработка', 'промышленность', 'оборонный заказ',
    'военно-промышленный комплекс', 'импортозамещение', 'технологии', 'инновации',
]

SUBSCRIBERS_FILE = 'subscribers.txt'

# Фильтр спама и скама
SPAM_PHRASES = [
    'get free', 'бесплатно', 'получите бесплатно', 'закажите сейчас',
    'скидка', 'акция', 'промокод', 'купить', 'продать', 'заказать',
    'перейдите по ссылке', 'нажмите здесь', 'подпишитесь', 'кликните',
    'диплом', 'курсовая', 'накрутка', 'подписчиков', 'лайков',
    'заработок', 'инвестиции', 'криптовалюта', 'бинарные опционы',
    'гарантия', 'результат', 'быстро', 'легко', 'выгодно', 
    'ракетная опасность', 'отбой', 'ракетной опасности', 
    'ОПАСНОСТЬ АТАКИ БПЛА', 'опасность атаки БПЛА', 'опасность атаки', 
    'отбой ракетной опасности', 'отбой опасности атаки БПЛА', 
    'ОТБОЙ опасности атаки БПЛА', 'доброе утро', 'спокойной ночи', 
    'ночной чат', 'устренний чат', 'ржать', 'угарные', 'ракетную опасность',
    'отзыв', 'родительский чат', 'чат',
    # Бытовые и местные новости
    'изрисовали', 'неизвестные возле', 'элеваторы для оплаты',
    'автобусах появились', 'техосмотр', 'как выбрать генератор',
    'инструкция по выбору', 'утренняя зарядка', 'рецидивист',
    'сразу видно рецидивист', 'обсуждают уличных музыкантов',
    'утренняя зарядка в vk', 'vk.com/video',
    # Рекламные призывы
    'подписаться на канал', 'подписаться на нас', 'подписаться на риа',
    'курсовая программа', 'бесплатная программа', 'заявки принимаются',
    'количество мест ограничено', 'шапка', 'маркетплейс',
    'утренняя зарядка', 'ссылка на видео', 'платим за ваш эксклюзив',
    'реклама', 'коммерция', 'озон', 'wildberries', 'накрутка',
    # Развлекательный контент
    'трамп вернулся в tiktok', 'утренняя зарядка',
    # Коммерческие предложения
    'платим за ваш эксклюзив', 'реклама', 'коммерция',
    'маркетплейс', 'озон', 'wildberries',
    # Убраны упоминания опасностей
    'авиационная опасность', 'воздушная опасность', 'авиационная', 
    'воздушная', 'бпла опасность', 'опасность бпла', 'оперштаб',
    'сирена', 'тревога', 'воздушная тревога', 'отбой тревоги'
]

SPAM_URL_THRESHOLD = 3

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

# ===== ФУНКЦИИ ФИЛЬТРАЦИИ =====
def contains_keywords(text):
    """Проверяет, содержит ли текст ключевые слова"""
    if not text:
        return False
        
    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False

def is_spam_message(text):
    """Проверка на спам и скам"""
    if not text:
        return True
        
    text_lower = text.lower()
    
    # Проверка спам-фраз
    for phrase in SPAM_PHRASES:
        if phrase in text_lower:
            logger.info(f"🚫 Спам-фраза: {phrase}")
            return True
    
    # Проверка количества ссылок (кроме telegram ссылок)
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    
    # Фильтруем telegram ссылки
    non_telegram_urls = [url for url in urls if 't.me' not in url and 'telegram' not in url]
    
    if len(non_telegram_urls) > SPAM_URL_THRESHOLD:
        logger.info(f"🚫 Слишком много нетематических ссылок: {len(non_telegram_urls)}")
        return True
    
    # Проверка призывов к действию с нетематическими ссылками
    action_words = ['перейдите', 'нажмите', 'кликните', 'закажите', 'купить']
    has_action = any(word in text_lower for word in action_words)
    has_non_telegram_url = len(non_telegram_urls) > 0
    
    if has_action and has_non_telegram_url:
        logger.info("🚫 Рекламное сообщение с призывом и нетематическими ссылками")
        return True
    
    return False

def is_relevant_topic(text):
    """Проверка тематики по ключевым словам"""
    if not text:
        return False, []
        
    if contains_keywords(text):
        logger.info("✅ Сообщение содержит ключевые слова")
        return True, ['новости']
    else:
        logger.info("🚫 Сообщение не содержит ключевые слова")
        return False, []

# ===== ФУНКЦИИ РАССЫЛКИ =====
def init_db():
    conn = sqlite3.connect('news.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parsed_posts (
            post_id TEXT PRIMARY KEY,
            channel TEXT,
            text TEXT,
            categories TEXT,
            message_url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    return conn

def is_post_sent(conn, post_id):
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM parsed_posts WHERE post_id = ?", (post_id,))
    return cursor.fetchone() is not None

def mark_post_as_sent(conn, post_id, channel, text, categories, message_url):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO parsed_posts (post_id, channel, text, categories, message_url) VALUES (?, ?, ?, ?, ?)",
        (post_id, channel, text, ','.join(categories) if categories else '', message_url)
    )
    conn.commit()

def generate_post_id(channel_name, message_id):
    return f"{channel_name}_{message_id}"

def generate_website_post_id(source, link):
    """Генерация ID для статей с сайтов"""
    import hashlib
    unique_string = f"{source}_{link}"
    return f"website_{hashlib.md5(unique_string.encode()).hexdigest()}"

def format_channel_name(channel_name):
    """Форматирование названия канала"""
    name_map = {
        'gubernator_46': 'Оперштаб Курской области 🇷🇺',
        'kursk_info46': 'Твой Курский край | Новости Курского приграничья',
        'Alekhin_Telega': 'Роман Алехин',
        'rian_ru': 'РИА Новости',
        'kursk_ak46': '🇷🇺 Актуальный Курск',
        'zhest_kursk_146': 'Жесть Курск',
        'novosti_efir': 'Прямой Эфир • Новости',
        'kursk_tipich': 'Типичный Курск',
        'seymkursk': 'Сейм: новости Курской области🇷🇺',
        'kursk_smi': 'Новости Курска и Области',
        'kursk_russia': 'Курск №1',
        'belgorod01': 'Белгород №1',
        'kurskadm': 'Курская область',
        'incident46': 'Инцидент Курск',
        'kurskbomond': 'КУРСКИЙ БОМОНДЪ',
        'prigranichie_radar1': 'Приграничный Радар',
        'grohot_pgr': '💥Грохот приграничья🇷🇺',
        'kursk_nasv': 'Курск на связи ©',
        'mchs_46': 'МЧС Курской области',
        'patriot046': 'ПАТРИОТ КУРСК',
        'kursk_now': '⚡️Курск сейчас',
        'Hinshtein': 'Александр Хинштейн',
        'incidentkursk': '🚨 ЧП, Курское приграничье',
        'zhest_belgorod': 'Жесть Белгород',
        'RVvoenkor': 'Операция Z: Военкоры Русской Весны',
        'pb_032': 'ПОДСЛУШАНО БРЯНСК',
        'tipicl32': 'ТИПИЧНЫЙ БРЯНСК | НОВОСТИ',
        'bryansk_smi': 'Новости Брянска и Области',
        'Ria_novosti_rossiya': 'Россия сейчас • Новости',
        'criminalru': 'Компромат Групп',
        'bra_32': 'НОВОСТИ БРЯНСКА',
        'br_gorod': 'Город Брянск',
        'br_zhest': 'Жесть | Брянск',
        'pravdas': '«ПС-Расследования»',
        'wargonzo': 'WarGonzo',
        'ploschadmedia': 'Площадь',
        'belgorod_smi': 'Новости Белгорода и Области',
        'ssigny': 'СИГНАЛ',
        'rucriminalinfo': 'ВЧК-ОГПУ',
        'kurskiy_harakter': 'Курский характер',
        'dva_majors': 'Два майора',
        'ENews112': '112',
    }
    return name_map.get(channel_name, f'📢 {channel_name}')

def format_message_text(text):
    """Форматирование текста сообщения"""
    if not text:
        return ""
        
    # Очищаем от лишних пробелов и переносов
    text = re.sub(r'\n\s*\n', '\n\n', text.strip())
    
    # Обрезаем слишком длинные сообщения
    if len(text) > 3800:
        text = text[:3800] + "..."
    
    return text

# ===== ФУНКЦИИ ДЛЯ ПАРСИНГА САЙТОВ =====

async def parse_rss_feed(website_config):
    """Парсинг RSS-ленты"""
    try:
        feed = feedparser.parse(website_config['url'])
        articles = []
        
        for entry in feed.entries[:10]:  # Берем 10 последних записей
            try:
                title = entry.title
                link = entry.link
                
                # Проверяем наличие описания
                description = entry.get('description', '')
                if not description:
                    description = title
                
                # Проверяем дату
                published = entry.get('published', '')
                if not published:
                    published = entry.get('updated', 'Сегодня')
                
                # Проверяем релевантность по ключевым словам
                if contains_keywords(title) or contains_keywords(description):
                    articles.append({
                        'title': title,
                        'link': link,
                        'date': published,
                        'source': website_config['name'],
                        'text': f"{title}\n\n{description}",
                        'type': 'rss'
                    })
                    
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга RSS элемента: {e}")
                continue
                
        return articles
        
    except Exception as e:
        logger.error(f"❌ Ошибка RSS {website_config['name']}: {e}")
        return []

async def check_websites(session, conn, bot_client):
    """Проверка всех веб-сайтов на новые статьи"""
    try:
        all_articles = []
        
        for website in WEBSITES:
            logger.info(f"🌐 Проверяем сайт: {website['name']}")
            
            try:
                if website.get('type') == 'rss':
                    articles = await parse_rss_feed(website)
                    all_articles.extend(articles)
                    logger.info(f"✅ Найдено статей на {website['name']}: {len(articles)}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке {website['name']}: {e}")
                continue
                
            await asyncio.sleep(1)  # Задержка между запросами
        
        # Фильтруем и отправляем новые статьи
        await process_website_articles(conn, bot_client, all_articles)
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки сайтов: {e}")

async def process_website_articles(conn, bot_client, articles):
    """Обработка и отправка статей с сайтов"""
    sent_count = 0
    
    for article in articles:
        try:
            # Генерируем уникальный ID для статьи
            article_id = generate_website_post_id(article['source'], article['link'])
            
            # Проверяем, не отправляли ли уже эту статью
            if is_post_sent(conn, article_id):
                continue
            
            # Дополнительная проверка на спам для статей с сайтов
            if is_spam_message(article['title']) or is_spam_message(article['text']):
                logger.info(f"🚫 Статья с сайта отфильтрована как спам: {article['title'][:50]}...")
                continue
            
            # Форматируем сообщение для отправки
            formatted_message = format_website_article(article)
            
            # Отправляем подписчикам
            subscribers = load_subscribers()
            success_count = 0
            
            for user_id in subscribers:
                try:
                    await bot_client.send_message(
                        user_id,
                        formatted_message,
                        parse_mode='md',
                        link_preview=True
                    )
                    success_count += 1
                    await asyncio.sleep(0.1)  # Задержка против флуда
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки {user_id}: {e}")
            
            # Помечаем как отправленную
            mark_post_as_sent(conn, article_id, article['source'], article['text'], ['веб-сайт'], article['link'])
            sent_count += 1
            logger.info(f"✅ Переслано с {article['source']} для {success_count}/{len(subscribers)} подписчиков")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки статьи: {e}")
    
    if sent_count > 0:
        logger.info(f"📨 Всего отправлено новых статей с сайтов: {sent_count}")

def format_website_article(article):
    """Форматирование статьи с сайта для отправки"""
    # Обрезаем слишком длинные заголовки
    title = article['title']
    if len(title) > 200:
        title = title[:200] + "..."
    
    return (
        f"🌐 **НОВОСТЬ С САЙТА**\n"
        f"📰 **{article['source']}**\n"
        f"🕒 {article['date']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Читать на сайте]({article['link']})"
    )

# ===== ОБРАБОТКА TELEGRAM СООБЩЕНИЙ =====

async def process_new_message(event, bot_client, conn):
    """Обработка нового сообщения и мгновенная рассылка"""
    try:
        message = event.message
        if not message.text or not message.text.strip():
            return False
            
        post_text = message.text.strip()
        channel_name = message.chat.username if message.chat.username else message.chat.title
        
        logger.info(f"📨 Новое сообщение из {channel_name}: {post_text[:100]}...")
        
        # Фильтр спама
        if is_spam_message(post_text):
            logger.info(f"🚫 Сообщение из {channel_name} отфильтровано как спам")
            return False
        
        # Фильтр тематики по ключевым словам
        is_relevant, categories = is_relevant_topic(post_text)
        if not is_relevant:
            return False
        
        post_id = generate_post_id(channel_name, message.id)
        
        # Проверяем, не отправляли ли уже это сообщение
        if is_post_sent(conn, post_id):
            logger.info(f"ℹ️ Сообщение из {channel_name} уже было отправлено")
            return False
        
        # Форматируем текст
        formatted_text = format_message_text(post_text)
        
        # Генерируем ссылки
        message_url = f"https://t.me/{channel_name}/{message.id}"
        channel_url = f"https://t.me/{channel_name}"
        
        # Красивое оформление сообщения с кликабельными ссылками
        formatted_channel = format_channel_name(channel_name)
        message_time = message.date.astimezone(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')
        
        # Форматируем с кликабельными ссылками на канал и сообщение
        formatted_post = (
            f"🚨 **НОВАЯ НОВОСТЬ**\n"
            f"✨ **[{formatted_channel}]({channel_url})**\n"
            f"🕒 {message_time}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{formatted_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 [Открыть сообщение]({message_url}) | 📢 [Перейти в канал]({channel_url})"
        )
        
        # Отправляем всем подписчикам
        subscribers = load_subscribers()
        success_count = 0
        
        for user_id in subscribers:
            try:
                await bot_client.send_message(
                    user_id, 
                    formatted_post, 
                    parse_mode='md',
                    link_preview=False
                )
                success_count += 1
                await asyncio.sleep(0.1)  # Небольшая задержка против флуда
            except Exception as e:
                logger.error(f"❌ Ошибка отправки {user_id}: {e}")
        
        # Помечаем как отправленное
        mark_post_as_sent(conn, post_id, channel_name, message.text, categories, message_url)
        logger.info(f"✅ Переслано новое сообщение из {channel_name} для {success_count}/{len(subscribers)} подписчиков")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        return False

# ===== ОСНОВНАЯ ФУНКЦИЯ =====

async def main():
    user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    bot_client = TelegramClient('bot_session', API_ID, API_HASH)
    
    # Инициализация базы данных
    db_conn = init_db()
    
    # Создаем aiohttp сессию для парсинга сайтов
    aiohttp_session = aiohttp.ClientSession()
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        if event.message.out:
            return
            
        user_id = event.chat_id
        subscribers_before = len(load_subscribers())
        add_subscriber(user_id)
        subscribers_after = len(load_subscribers())
        
        logger.info(f"👤 Новый подписчик: {user_id}. Было: {subscribers_before}, стало: {subscribers_after}")
        
        await event.reply(
            "🎉 **Добро пожаловать в систему мгновенных новостей!**\n\n"
            "✅ Вы успешно подписались на рассылку\n"
            "⚡ Режим работы: мгновенные уведомления\n"
            f"📰 Отслеживаем Telegram каналов: {len(CHANNELS)}\n"
            f"🌐 Отслеживаем веб-сайтов: {len(WEBSITES)}\n"
            f"🔍 Ключевых слов для фильтрации: {len(KEYWORDS)}\n"
            "🛡️ *Фильтры:* антиспам, ключевые слова\n\n"
            "✨ Команды:\n"
            "/stats - статистика системы\n"
            "/channels - список отслеживаемых каналов\n" 
            "/stop - отписаться от рассылки",
            parse_mode='md',
            link_preview=False
        )
    
    @bot_client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        if event.message.out:
            return
            
        user_id = event.chat_id
        subscribers_before = len(load_subscribers())
        remove_subscriber(user_id)
        subscribers_after = len(load_subscribers())
        
        logger.info(f"👤 Отписался: {user_id}. Было: {subscribers_before}, стало: {subscribers_after}")
        
        await event.reply(
            "❌ **Вы отписались от рассылки**\n\n"
            "Если передумаете - просто напишите /start",
            parse_mode='md',
            link_preview=False
        )
    
    @bot_client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        if event.message.out:
            return
            
        subscribers = load_subscribers()
        website_count = len([w for w in WEBSITES if w.get('type') == 'rss'])
        
        await event.reply(
            f"📊 **СТАТИСТИКА СИСТЕМЫ**\n\n"
            f"👥 *Подписчиков:* {len(subscribers)}\n"
            f"📰 *Telegram каналов:* {len(CHANNELS)}\n"
            f"🌐 *Веб-сайтов:* {website_count}\n"
            f"🔍 *Ключевых слов:* {len(KEYWORDS)}\n"
            f"⚡ *Режим:* мгновенные уведомления\n"
            f"🛡️ *Фильтры активны:* да\n"
            f"✅ *Антиспам:* включен",
            parse_mode='md',
            link_preview=False
        )
    
    @bot_client.on(events.NewMessage(pattern='/channels'))
    async def channels_handler(event):
        if event.message.out:
            return
            
        channels_list = "\n".join([f"• {channel}" for channel in CHANNELS])
        await event.reply(
            f"📰 **Отслеживаемые каналы:**\n\n{channels_list}\n\n"
            f"Всего: {len(CHANNELS)} каналов",
            parse_mode='md',
            link_preview=False
        )
    
    # Обработчик для Telegram каналов
    @user_client.on(events.NewMessage(chats=CHANNELS))
    async def telegram_channel_handler(event):
        """Обработчик новых сообщений из отслеживаемых каналов"""
        await process_new_message(event, bot_client, db_conn)
    
    async def website_checker():
        """Фоновая задача для проверки сайтов"""
        while True:
            try:
                logger.info("🔍 Начинаем проверку веб-сайтов...")
                await check_websites(aiohttp_session, db_conn, bot_client)
                # Проверяем сайты каждые 30 минут
                logger.info("⏰ Следующая проверка сайтов через 30 минут")
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"❌ Ошибка в website_checker: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    try:
        await user_client.start()
        await bot_client.start(bot_token=BOT_TOKEN)
        
        subscribers_count = len(load_subscribers())
        logger.info("✅ Бот запущен в режиме мгновенных уведомлений")
        logger.info(f"📰 Отслеживается Telegram каналов: {len(CHANNELS)}")
        logger.info(f"🌐 Отслеживается веб-сайтов: {len(WEBSITES)}")
        logger.info(f"🔍 Ключевых слов для фильтрации: {len(KEYWORDS)}")
        logger.info(f"👥 Текущее количество подписчиков: {subscribers_count}")
        logger.info("⚡ Режим: мгновенная пересылка новых сообщений")
        
        if subscribers_count == 0:
            logger.warning("⚠️ ВНИМАНИЕ: Нет подписчиков! Отправьте боту /start")
        
        # Запускаем фоновую задачу для проверки сайтов
        asyncio.create_task(website_checker())
        
        # Бесконечный цикл для поддержания работы бота
        await user_client.run_until_disconnected()

    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        await user_client.disconnect()
        await bot_client.disconnect()
        await aiohttp_session.close()
        db_conn.close()

if __name__ == '__main__':
    asyncio.run(main())
