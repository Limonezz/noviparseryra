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

# ===== КОНФИГУРАЦИЯ =====
API_ID = '24826804'
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

CHANNELS = [
    'gubernator_46', 'kursk_info46', 'Alekhin_Telega', 'rian_ru',
    'kursk_ak46', 'zhest_kursk_146', 'novosti_efir', 'kursk_tipich',
    'seymkursk', 'kursk_smi', 'kursk_russia', 'belgorod01', 'kurskadm',
    'incident46', 'kurskbomond', 'prigranichie_radar1', 'grohot_pgr',
    'kursk_nasv', 'mchs_46', 'patriot046', 'kursk_now', 'Hinshtein',
    'incidentkursk', 'zhest_belgorod', 'RVvoenkor', 'pb_032',
    'tipicl32', 'bryansk_smi', 'Ria_novosti_rossiya','criminalru','bra_32','br_gorod','br_zhest', 'pravdas', 'wargonzo', 'ploschadmedia', 
    'belgorod_smi','ssigny','rucriminalinfo','kurskiy_harakter','dva_majors','ENews112','mash','NewsRussias7',
]

SUBSCRIBERS_FILE = 'subscribers.txt'

# Фильтр спама и скама
SPAM_DOMAINS = [
    'ordershunter.ru', 'premium_gift', 'telegram-premium', 'free-telegram',
    'nakrutka', 'followers', 'likes', 'diplom', 'kursovaya', 'zarabotok'
]

SPAM_PHRASES = [
    'get free', 'бесплатно', 'получите бесплатно', 'закажите сейчас',
    'скидка', 'акция', 'промокод', 'купить', 'продать', 'заказать',
    'перейдите по ссылке', 'нажмите здесь', 'подпишитесь', 'кликните',
    'диплом', 'курсовая', 'накрутка', 'подписчиков', 'лайков',
    'заработок', 'инвестиции', 'криптовалюта', 'бинарные опционы',
    'гарантия', 'результат', 'быстро', 'легко', 'выгодно', 'ракетная опасность', 'отбой', 'ракетной опасности', 'ОПАСНОСТЬ АТАКИ БПЛА', 'опасность атаки БПЛА', 'опасность атаки', 'отбой ракетной опасности', 'отбой опасности атаки БПЛА', 'ОТБОЙ опасности атаки БПЛА', 'доброе утро','спокойной ночи', 'ночной чат', 'устренний чат',
    'ржать','угарные','ракетную опасность','отзыв', 'родительский чат', 'чат',
    # НОВЫЕ ФИЛЬТРЫ на основе анализа:
    # Бытовые и местные новости
    'изрисовали', 'неизвестные возле', 'элеваторы для оплаты',
    'автобусах появились', 'пишут:', 'предложить новость',
    'прислать новость', 'техосмотр', 'как выбрать генератор',
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
]

# Важные ключевые слова, которые должны ПРОПУСКАТЬСЯ
IMPORTANT_KEYWORDS = [
    'беспилотник', 'сбил', 'уничтожил',
    'разминировал', 'задержал', 'арест', 'террорист', 'экстремист',
    'минобороны', 'военкор', 'спецоперация', 'губернатор', 'президент',
    'правительство', 'министр', 'встреча', 'переговоры', 'заявление',
    'пожар', 'сгорел', 'мчс', 'полиция', 'суд', 'обстрел', 'катастрофа',
    'авария', 'взрыв', 'нападение', 'жертв', 'пострадал', 'оперштаб',
    'опасность', 'безопасность', 'наступление', 'оборона', 'военные',
    'силовики', 'уголовное дело', 'возбудили', 'запрещено', 'санкции'
]

SPAM_URL_THRESHOLD = 2
UNIQUE_WORDS_THRESHOLD = 5
MAX_MESSAGE_AGE_HOURS = 6  # Новости за последние 6 часов
MAX_POSTS_PER_CHANNEL = 4  # Максимум 4 новости от одного канала
MESSAGES_PER_CHANNEL = 4   # Берем 4 последних сообщения

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sent_messages_words = set()

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
def clean_text(text):
    """Очистка текста"""
    text = re.sub(r'http\S+|@\w+|#\w+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

def get_text_words(text):
    """Получаем значимые слова"""
    cleaned = clean_text(text)
    words = cleaned.split()
    stop_words = {'и', 'в', 'на', 'с', 'по', 'за', 'к', 'у', 'о', 'от', 'для', 'это', 'как', 'что', 'из', 'не'}
    return {word for word in words if len(word) > 2 and word not in stop_words}

def is_important_news(text):
    """Проверяет, содержит ли текст важные ключевые слова"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in IMPORTANT_KEYWORDS)

def is_spam_message(text):
    """Проверка на спам и скам"""
    text_lower = text.lower()
    
    # ВАЖНО: сообщения с важными ключевыми словами всегда пропускаем
    if is_important_news(text):
        logger.info("✅ Важное сообщение, пропускаем")
        return False
    
    # Проверка спам-фраз
    for phrase in SPAM_PHRASES:
        if phrase in text_lower:
            logger.info(f"🚫 Спам-фраза: {phrase}")
            return True
    
    # Проверка спам-доменов
    for domain in SPAM_DOMAINS:
        if domain in text_lower:
            logger.info(f"🚫 Спам-домен: {domain}")
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
    action_words = ['перейдите', 'нажмите', 'кликните', 'закажите', 'купить', 'подпишитесь']
    has_action = any(word in text_lower for word in action_words)
    has_non_telegram_url = len(non_telegram_urls) > 0
    
    if has_action and has_non_telegram_url:
        logger.info("🚫 Рекламное сообщение с призывом и нетематическими ссылками")
        return True
    
    return False

def is_relevant_topic(text):
    """Проверка тематики - теперь принимаем все сообщения кроме спама"""
    logger.info("✅ Сообщение прошло фильтр тематики")
    return True, ['новости']

def is_message_unique(message_text):
    """Проверка уникальности"""
    global sent_messages_words
    
    new_words = get_text_words(message_text)
    if not new_words:
        return True
    
    common_words = new_words & sent_messages_words
    common_count = len(common_words)
    
    if common_count >= UNIQUE_WORDS_THRESHOLD:
        logger.info(f"🚫 Дубликат: {common_count} общих слов")
        return False
    
    sent_messages_words.update(new_words)
    return True

def is_recent_message(message_date):
    """Проверка свежести сообщения"""
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    message_age = utc_now - message_date
    
    if message_age > timedelta(hours=MAX_MESSAGE_AGE_HOURS):
        logger.info(f"🚫 Слишком старое сообщение: {message_age}")
        return False
    
    return True

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

def generate_message_url(channel_username, message_id):
    """Генерация ссылки на оригинальное сообщение"""
    return f"https://t.me/{channel_username}/{message_id}"

def generate_channel_url(channel_username):
    """Генерация ссылки на канал"""
    return f"https://t.me/{channel_username}"

def should_send_news():
    """Проверка времени рассылки"""
    try:
        utc_now = datetime.utcnow()
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = moscow_tz.fromutc(utc_now)
        
        current_hour = moscow_time.hour
        current_minute = moscow_time.minute
        
        send_times = [(9, 0), (13, 0), (19, 0)]
        
        logger.info(f"🕒 Время МСК: {current_hour:02d}:{current_minute:02d}")
        return (current_hour, current_minute) in send_times
        
    except Exception as e:
        logger.error(f"Ошибка времени: {e}")
        return False

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
        'mash': 'Mash',
        'NewsRussias7': 'Новости России'
    }
    return name_map.get(channel_name, f'📢 {channel_name}')

def format_message_text(text):
    """Форматирование текста сообщения"""
    # Очищаем от лишних пробелов и переносов
    text = re.sub(r'\n\s*\n', '\n\n', text.strip())
    
    # Обрезаем слишком длинные сообщения
    if len(text) > 3800:
        text = text[:3800] + "..."
    
    return text

async def parse_channel(user_client, channel_name, conn):
    """Парсинг канала с фильтрацией - берем 4 последних сообщения"""
    try:
        logger.info(f"🔍 Парсим: {channel_name}")
        messages = await user_client.get_messages(channel_name, limit=MESSAGES_PER_CHANNEL)
        new_posts = []
        posts_count = 0
        
        for message in messages:
            if not message.text or not message.text.strip():
                continue
            
            post_text = message.text.strip()
            
            # Фильтр спама
            if is_spam_message(post_text):
                continue
            
            # Фильтр свежести
            if not is_recent_message(message.date):
                continue
            
            post_id = generate_post_id(channel_name, message.id)
            
            if not is_post_sent(conn, post_id):
                # Фильтр тематики
                is_relevant, categories = is_relevant_topic(post_text)
                if not is_relevant:
                    continue
                
                # Фильтр уникальности
                if not is_message_unique(post_text):
                    continue
                
                # Форматируем текст
                formatted_text = format_message_text(post_text)
                
                # Генерируем ссылки
                message_url = generate_message_url(channel_name, message.id)
                channel_url = generate_channel_url(channel_name)
                
                # Красивое оформление сообщения с кликабельными ссылками
                formatted_channel = format_channel_name(channel_name)
                message_time = message.date.astimezone(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')
                
                # Форматируем с кликабельными ссылками на канал и сообщение
                formatted_post = (
                    f"✨ **[{formatted_channel}]({channel_url})**\n"
                    f"🕒 {message_time}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{formatted_text}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔗 [Открыть сообщение]({message_url}) | 📢 [Перейти в канал]({channel_url})"
                )
                
                new_posts.append({
                    'text': formatted_post,
                    'post_id': post_id,
                    'channel': channel_name,
                    'categories': categories,
                    'message_url': message_url
                })
                
                mark_post_as_sent(conn, post_id, channel_name, message.text, categories, message_url)
                posts_count += 1
                
                # Ограничиваем количество постов от одного канала
                if posts_count >= MAX_POSTS_PER_CHANNEL:
                    break
        
        return new_posts
        
    except Exception as e:
        logger.error(f"❌ Ошибка {channel_name}: {e}")
        return []

async def send_news_to_user(bot_client, user_id, posts):
    """Отправка новостей с красивым оформлением"""
    if not posts:
        return
    
    moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')
    
    try:
        # Красивое приветственное сообщение
        await bot_client.send_message(
            user_id,
            f"📰 **ДАЙДЖЕСТ НОВОСТЕЙ**\n"
            f"⏰ Актуально на: {moscow_time} (МСК)\n"
            f"📊 Всего новостей: {len(posts)}\n"
            f"✅ Проверено антиспам-фильтром\n"
            f"────────────────",
            parse_mode='md',
            link_preview=False
        )
        
        await asyncio.sleep(1)
        
        # Отправляем каждую новость с задержкой
        for i, post in enumerate(posts, 1):
            await bot_client.send_message(
                user_id, 
                post['text'], 
                parse_mode='md',
                link_preview=False
            )
            
            # Добавляем разделитель между новостями, кроме последней
            if i < len(posts):
                await bot_client.send_message(
                    user_id,
                    "⬇️ **Следующая новость** ⬇️",
                    parse_mode='md',
                    link_preview=False
                )
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(1)
        
        # Футер с итогами
        await bot_client.send_message(
            user_id,
            f"✅ **РАССЫЛКА ЗАВЕРШЕНА**\n"
            f"📅 Следующий выпуск в 9:00, 13:00 или 19:00 по МСК\n"
            f"👥 Каналов отслеживается: {len(CHANNELS)}\n"
            f"📝 Сообщений проверено: {len(CHANNELS) * MESSAGES_PER_CHANNEL}\n"
            f"🛡️ Фильтры: спам, дубликаты, скам\n"
            f"────────────────",
            parse_mode='md',
            link_preview=False
        )
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки {user_id}: {e}")

async def collect_news(user_client):
    """Сбор новостей"""
    global sent_messages_words
    sent_messages_words = set()
    
    db_conn = init_db()
    all_news = []
    
    for channel in CHANNELS:
        try:
            channel_news = await parse_channel(user_client, channel, db_conn)
            all_news.extend(channel_news)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"❌ Ошибка канала {channel}: {e}")
    
    db_conn.close()
    
    logger.info(f"📊 Собрано уникальных новостей: {len(all_news)}")
    return all_news

async def send_news_to_all_subscribers(user_client, bot_client):
    """Рассылка"""
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("📭 Нет подписчиков")
        return
    
    logger.info(f"📨 Отправка для {len(subscribers)} подписчиков")
    
    all_news = await collect_news(user_client)
    
    if not all_news:
        logger.info("📭 Нет новых новостей")
        # Отправляем уведомление подписчикам, что новостей нет
        for user_id in subscribers:
            try:
                await bot_client.send_message(
                    user_id,
                    f"📰 **СВЕЖИХ НОВОСТЕЙ НЕТ**\n"
                    f"⏰ *Время проверки:* {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')}\n"
                    f"ℹ️ За последние 6 часов новостей не обнаружено\n"
                    f"✅ Антиспам-фильтр работает\n"
                    f"────────────────",
                    parse_mode='md',
                    link_preview=False
                )
            except Exception as e:
                logger.error(f"❌ Ошибка отправки {user_id}: {e}")
        return
    
    for user_id in subscribers:
        try:
            await send_news_to_user(bot_client, user_id, all_news)
            logger.info(f"✅ Отправлено {user_id}")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки {user_id}: {e}")
    
    logger.info(f"✅ Рассылка завершена")

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
async def main():
    user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    bot_client = TelegramClient('bot_session', API_ID, API_HASH)
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        if event.message.out:
            return
            
        user_id = event.chat_id
        add_subscriber(user_id)
        await event.reply(
            "🎉 **Добро пожаловать в новостной дайджест!**\n\n"
            "✅ Вы успешно подписались на рассылку\n"
            "⏰ Время рассылки: 9:00, 13:00, 19:00 (МСК)\n"
            f"📰 Отслеживаем каналов: {len(CHANNELS)}\n"
            f"📝 Проверяем по {MESSAGES_PER_CHANNEL} сообщения с каждого канала\n"
            "🛡️ *Фильтры:* антиспам, антискам, проверка дубликатов\n\n"
            "✨ Команды:\n"
            "/news - получить свежие новости сейчас\n"
            "/stats - статистика подписчиков\n"
            "/stop - отписаться от рассылки",
            parse_mode='md',
            link_preview=False
        )
    
    @bot_client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        if event.message.out:
            return
            
        user_id = event.chat_id
        remove_subscriber(user_id)
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
        await event.reply(
            f"📊 **СТАТИСТИКА СИСТЕМЫ**\n\n"
            f"👥 *Подписчиков:* {len(subscribers)}\n"
            f"📰 *Отслеживаемых каналов:* {len(CHANNELS)}\n"
            f"📝 *Сообщений проверяется за раз:* {len(CHANNELS) * MESSAGES_PER_CHANNEL}\n"
            f"⏰ *Следующая рассылка:* 9:00, 13:00 или 19:00 МСК\n"
            f"🛡️ *Фильтры активны:* да",
            parse_mode='md',
            link_preview=False
        )
    
    @bot_client.on(events.NewMessage(pattern='/news'))
    async def news_handler(event):
        if event.message.out:
            return
            
        user_id = event.chat_id
        await event.reply(
            "⏳ **Ищем свежие новости...**\n"
            f"Проверяем последние {MESSAGES_PER_CHANNEL} сообщения с каждого канала за 6 часов",
            parse_mode='md',
            link_preview=False
        )
        all_news = await collect_news(user_client)
        await send_news_to_user(bot_client, user_id, all_news)
    
    try:
        await user_client.start()
        await bot_client.start(bot_token=BOT_TOKEN)
        
        logger.info("✅ Бот запущен")
        logger.info(f"📝 Проверяем по {MESSAGES_PER_CHANNEL} сообщения с канала")
        logger.info(f"🛡️ Фильтры: спам, уникальность, свежесть (последние {MAX_MESSAGE_AGE_HOURS} часов)")
        logger.info(f"📰 Максимум {MAX_POSTS_PER_CHANNEL} новости от одного канала")
        logger.info(f"🔍 Важные ключевые слова: {len(IMPORTANT_KEYWORDS)} фраз")
        
        while True:
            if should_send_news():
                logger.info("🕒 Время рассылки!")
                await send_news_to_all_subscribers(user_client, bot_client)
                await asyncio.sleep(120)
            
            await asyncio.sleep(30)
            
    except Exception as e:
        logger.error(f"💥 Ошибка: {e}")
    finally:
        await user_client.disconnect()
        await bot_client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
