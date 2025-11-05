import asyncio
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import logging
import re
import aiohttp
import feedparser

# ===== КОНФИГУРАЦИЯ =====
API_ID = 24826804
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

# Telegram каналы для мониторинга
CHANNELS = [
    'gubernator_46', 'kursk_info46', 'Alekhin_Telega', 'rian_ru',
    'kursk_ak46', 'zhest_kursk_146', 'novosti_efir', 'kursk_tipich',
    'seymkursk', 'kursk_smi', 'kursk_russia', 'belgorod01', 'kurskadm',
    'incident46', 'kurskbomond', 'prigranichie_radar1', 'grohot_pgr',
    'kursk_nasv', 'mchs_46', 'patriot046', 'kursk_now', 'Hinshtein',
    'incidentkursk', 'zhest_belgorod', 'RVvoenkor', 'pb_032',
    'tipicl32', 'bryansk_smi', 'Ria_novosti_rossiya','criminalru','bra_32','br_gorod','br_zhest', 
    'pravdas', 'wargonzo', 'ploschadmedia', 'belgorod_smi','ssigny','rucriminalinfo',
    'kurskiy_harakter','dva_majors','ENews112', 'rt_russian', 'bbbreaking', 'readovkanews'
]

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
    },
    {
        'name': 'RuCriminal',
        'url': 'https://www.rucriminal.info/rss.xml',
        'type': 'rss'
    },
    {
        'name': 'Фонарь',
        'url': 'https://fonar.tv/rss',
        'type': 'rss'
    },
    {
        'name': 'Генеральная прокуратура ДВФО',
        'url': 'https://epp.genproc.gov.ru/ru/proc_dvfo/rss/',
        'type': 'rss'
    },
    {
        'name': 'ФедералПресс',
        'url': 'https://fedpress.ru/rss/news',
        'type': 'rss'
    },
    {
        'name': 'Бел.ру',
        'url': 'https://bel.ru/rss/news',
        'type': 'rss'
    }
]

# ===== ВЕЧНЫЕ ПОДПИСЧИКИ =====
PERMANENT_SUBSCRIBERS = [
    1175795428,
    8019965642,
]

# ===== СУПЕР-ФИЛЬТР: ТОЛЬКО ВОЙНА, ПОЛИТИКА, СЕРЬЕЗНЫЕ СОБЫТИЯ =====
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
    'эвакуация', 'беженец', 'переселенец', 'гуманитарная помощь', 'военное положение',
    'коррупция', 'взятка', 'растрата', 'мошенничество', 'уголовное', 'следствие',
    'прокуратура', 'суд', 'арест', 'обыск', 'задержание', 'приговор',
    'Бурков', 'Уралвагонзавод', 'губернатор', 'теневой', 'империя'
]

# ===== СТОП-СЛОВА =====
STOP_WORDS = [
    'футбол', 'хоккей', 'теннис', 'баскетбол', 'волейбол', 'UFC', 'бокс', 'чемпионат', 'матч',
    'кино', 'сериал', 'актер', 'актриса', 'режиссер', 'премия', 'музыка', 'песня', 'альбом',
    'концерт', 'фестиваль', 'артист',
    'космос', 'астроном', 'планета', 'марс', 'луна', 'спутник',
    'смартфон', 'iphone', 'android', 'гаджет', 'приложение', 'соцсеть',
    'игра', 'геймер', 'playstation', 'xbox', 'steam',
    'рецепт', 'кулинар', 'еда', 'бургер', 'пицца', 'ресторан', 'кафе',
    'мода', 'дизайнер', 'показ', 'коллекция', 'модель',
    'котик', 'кот', 'кошка', 'собака', 'питомец', 'животное',
    'театр', 'спектакль', 'опера', 'балет',
    'туризм', 'путешествие', 'отдых', 'курорт', 'отель',
    'автомобиль', 'машина', 'бмв', 'мерседес', 'тойота',
    'дом', 'квартира', 'ремонт', 'интерьер',
    'диета', 'похудение', 'фитнес', 'тренажерный зал', 'йога',
    'юмор', 'анекдот', 'мем', 'прикол', 'розыгрыш',
    'спокойной ночи', 'доброй ночи', 'доброе утро', 'с добрым утром',
    'ночные чаты', 'утренние чаты', 'ночной чат', 'утренний чат',
    'отличного дня', 'хорошего дня', 'удачного дня',
    'красота осени', 'осенние краски', 'осенний лес',
    'зимняя сказка', 'зимние пейзажи', 'снегопад',
    'весеннее настроение', 'весна пришла',
    'летний вечер', 'летняя ночь', 'летний закат',
    'красивые фото', 'красивый вид', 'пейзаж',
    'фотография дня', 'фото дня', 'картинка дня',
    'моё мнение', 'личное мнение', 'хочу рассказать',
    'уютный вечер', 'домашний уют', 'семейный вечер',
    'поздравляю', 'поздравления', 'с праздником', 'с днем рождения',
    'рецепт', 'кулинария', 'готовим', 'блюдо',
    'совет', 'рекомендация', 'лайфхак'
]

SUBSCRIBERS_FILE = 'subscribers.txt'

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== СИСТЕМА ПОДПИСЧИКОВ =====
def load_subscribers():
    """Загрузка всех подписчиков"""
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            file_subs = [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        file_subs = []
    
    all_subs = list(set(PERMANENT_SUBSCRIBERS + file_subs))
    return all_subs

def save_subscribers(subscribers):
    """Сохранение подписчиков"""
    regular_subs = [sub for sub in subscribers if sub not in PERMANENT_SUBSCRIBERS]
    
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            for user_id in regular_subs:
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
    return load_subscribers()

def remove_subscriber(user_id):
    """Удаление подписчика"""
    if user_id in PERMANENT_SUBSCRIBERS:
        logger.info(f"⚠️ Нельзя удалить вечного подписчика: {user_id}")
        return load_subscribers()
        
    subscribers = load_subscribers()
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        logger.info(f"❌ Отписался: {user_id}")
    return load_subscribers()

# ===== ФИЛЬТРЫ =====
def contains_war_keywords(text):
    """Проверяет, содержит ли текст ключевые слова войны"""
    if not text:
        return False
        
    text_lower = text.lower()
    
    # Проверяем стоп-слова
    for stop_word in STOP_WORDS:
        if stop_word.lower() in text_lower:
            logger.info(f"⏭️ Отфильтровано стоп-словом: {stop_word}")
            return False
    
    # Проверка на капс (только для очень длинных капс-сообщений)
    if len(text) > 50:
        caps_count = sum(1 for char in text if char.isupper())
        caps_ratio = caps_count / len(text)
        if caps_ratio > 0.7:  # Только очень высокий процент капса
            logger.info(f"⏭️ Отфильтровано из-за капса: {caps_ratio:.2f}")
            return False
    
    # Проверяем военные ключевые слова
    for keyword in WAR_KEYWORDS:
        if keyword.lower() in text_lower:
            logger.info(f"🎯 Найдено ключевое слово: {keyword}")
            return True
    
    return False

# ===== БАЗА ДАННЫХ =====
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('news.db', check_same_thread=False)
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
    """Проверка, отправлялся ли пост"""
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM sent_posts WHERE post_id = ?", (post_id,))
    return cursor.fetchone() is not None

def mark_post_sent(conn, post_id, channel, text):
    """Пометить пост как отправленный"""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO sent_posts (post_id, channel, text) VALUES (?, ?, ?)",
        (post_id, channel, text[:500] if text else "")
    )
    conn.commit()

# ===== RSS ПАРСИНГ =====
async def parse_rss_feed(website_config):
    """Парсинг RSS ленты"""
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
                            
                    except Exception as e:
                        continue
                        
                return articles
        
    except Exception as e:
        logger.error(f"❌ Ошибка RSS {website_config['name']}: {e}")
        return []

async def check_all_feeds(conn, client):
    """Проверка всех RSS лент"""
    try:
        logger.info("🌐 Проверка RSS лент...")
        
        for website in WEBSITES:
            try:
                articles = await parse_rss_feed(website)
                logger.info(f"📄 {website['name']}: {len(articles)} военных статей")
                
                for article in articles:
                    article_id = f"rss_{hash(article['link']) % 100000000}"
                    
                    if not is_post_sent(conn, article_id):
                        subscribers = load_subscribers()
                        message = format_website_message(article)
                        
                        success_count = 0
                        for user_id in subscribers:
                            try:
                                await client.send_message(
                                    user_id, 
                                    message, 
                                    parse_mode='Markdown',
                                    link_preview=True
                                )
                                success_count += 1
                                await asyncio.sleep(0.1)
                            except Exception as e:
                                logger.error(f"❌ Ошибка отправки {user_id}: {e}")
                        
                        if success_count > 0:
                            mark_post_sent(conn, article_id, article['source'], article['title'])
                            logger.info(f"✅ Отправлено {article['source']} для {success_count} подписчиков")
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ Ошибка при обработке {website['name']}: {e}")
                continue
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки лент: {e}")

def format_website_message(article):
    """Форматирование статьи"""
    title = article['title']
    if len(title) > 200:
        title = title[:200] + "..."
    
    return (
        f"🎯 **Сводка новостей**\n"
        f"📰 **{article['source']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Читать на сайте]({article['link']})"
    )

# ===== ОБРАБОТКА ТЕЛЕГРАМ КАНАЛОВ =====
async def send_to_subscribers(client, message_text, post_id, channel_name, conn):
    """Отправка сообщения всем подписчикам"""
    if is_post_sent(conn, post_id):
        logger.info(f"⏭️ Пост {post_id} уже был отправлен ранее")
        return 0
    
    subscribers = load_subscribers()
    success_count = 0
    
    logger.info(f"📤 Отправка сообщения из {channel_name} для {len(subscribers)} подписчиков")
    
    for user_id in subscribers:
        try:
            await client.send_message(
                user_id,
                message_text,
                parse_mode='Markdown',
                link_preview=False
            )
            success_count += 1
            await asyncio.sleep(0.1)  # Задержка между отправками
        except Exception as e:
            logger.error(f"❌ Ошибка отправки {user_id}: {e}")
    
    if success_count > 0:
        mark_post_sent(conn, post_id, channel_name, message_text[:100])
        logger.info(f"✅ УСПЕХ: Отправлено из {channel_name} для {success_count} подписчиков")
    
    return success_count

def format_telegram_message(text, channel_name):
    """Форматирование сообщения из Telegram канала"""
    # Обрезаем текст если слишком длинный
    if len(text) > 800:
        text = text[:800] + "..."
    
    return (
        f"🎯 **Экстренная сводка**\n"
        f"📢 **{channel_name}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"#сводка"
    )

# ===== ОСНОВНОЙ БОТ =====
async def main():
    """Главная функция бота"""
    # Инициализация
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    db_conn = init_db()
    
    # Загружаем подписчиков
    subscribers = load_subscribers()
    logger.info(f"👥 Загружено подписчиков: {len(subscribers)}")
    
    # Список для хранения entity каналов
    channel_entities = []
    
    # ===== ОБРАБОТЧИК ТЕЛЕГРАМ КАНАЛОВ =====
    @client.on(events.NewMessage)
    async def universal_handler(event):
        """Универсальный обработчик сообщений"""
        try:
            # Пропускаем сообщения от самого бота
            if event.message.out:
                return
                
            # Получаем информацию о чате
            chat = await event.get_chat()
            chat_id = chat.id
            chat_username = getattr(chat, 'username', None)
            chat_title = getattr(chat, 'title', None)
            
            # Проверяем, является ли чат одним из отслеживаемых каналов
            is_tracked_channel = False
            channel_identifier = None
            
            if chat_username and chat_username in CHANNELS:
                is_tracked_channel = True
                channel_identifier = chat_username
            elif chat_title and any(channel.lower() in chat_title.lower() for channel in CHANNELS):
                is_tracked_channel = True
                channel_identifier = chat_title
            elif str(chat_id) in [str(e.id) for e in channel_entities if hasattr(e, 'id')]:
                is_tracked_channel = True
                channel_identifier = f"id_{chat_id}"
            
            if not is_tracked_channel:
                return
            
            logger.info(f"📨 СООБЩЕНИЕ ИЗ КАНАЛА: {channel_identifier}")
            
            # Получаем текст сообщения
            message_text = event.message.text or event.message.caption or ""
            
            if not message_text.strip():
                logger.info("⏭️ Пустое сообщение, пропускаем")
                return
            
            logger.info(f"📝 Текст сообщения: {message_text[:200]}...")
            
            # Проверяем на военные ключевые слова
            if contains_war_keywords(message_text):
                logger.info(f"🎯 НАЙДЕНЫ КЛЮЧЕВЫЕ СЛОВА в сообщении из {channel_identifier}")
                
                # Создаем ID поста
                post_id = f"tg_{chat_id}_{event.message.id}"
                
                # Форматируем сообщение
                formatted_message = format_telegram_message(message_text, channel_identifier)
                
                # Отправляем подписчикам
                success_count = await send_to_subscribers(
                    client, formatted_message, post_id, channel_identifier, db_conn
                )
                
                if success_count > 0:
                    logger.info(f"📢 УСПЕХ: Обработано сообщение из {channel_identifier} для {success_count} подписчиков")
                else:
                    logger.info(f"ℹ️ Сообщение из {channel_identifier} уже было отправлено ранее")
            else:
                logger.info(f"⏭️ Сообщение из {channel_identifier} не содержит ключевых слов, пропускаем")
        
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")

    # ===== КОМАНДЫ БОТА =====
    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        subscribers = add_subscriber(user_id)
        await event.reply(
            "🎯 **Добро пожаловать в систему ВОЕННЫХ сводок!**\n\n"
            "✅ Вы подписались на получение ВОЕННЫХ новостей\n"
            "📰 Источники: Telegram каналы и новостные сайты\n"
            "⚡ Теперь вы будете получать только важные военные и политические сводки\n\n"
            "✨ Команды:\n"
            "/stop - отписаться\n"
            "/stats - статистика\n"
            "/id - узнать свой ID\n"
            "/test - тестовая отправка\n"
            "/channels - список отслеживаемых каналов\n"
            "/debug - отладочная информация\n"
            "/force_check - принудительная проверка"
        )
        logger.info(f"👤 Новый подписчик: {user_id}")
    
    @client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        user_id = event.sender_id
        subscribers = remove_subscriber(user_id)
        await event.reply("❌ Вы отписались от военных сводок")
        logger.info(f"👤 Отписался: {user_id}")
    
    @client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        subscribers = load_subscribers()
        await event.reply(
            f"📊 **Статистика:**\n\n"
            f"👥 Подписчиков: {len(subscribers)}\n"
            f"📰 Каналов: {len(CHANNELS)}\n"
            f"🌐 Сайтов: {len(WEBSITES)}\n"
            f"🎯 Ключевых слов: {len(WAR_KEYWORDS)}"
        )
    
    @client.on(events.NewMessage(pattern='/id'))
    async def id_handler(event):
        user_id = event.sender_id
        await event.reply(f"🆔 Ваш ID: `{user_id}`")
    
    @client.on(events.NewMessage(pattern='/test'))
    async def test_handler(event):
        """Тестовая команда"""
        try:
            await event.reply(
                "🎯 **Тестовое сообщение от системы военных сводок!**\n\n"
                "✅ Бот работает корректно!\n"
                "📡 Мониторинг каналов и сайтов активен\n"
                "⚡ Вы будете получать важные военные сводки"
            )
            logger.info("✅ Тестовое сообщение отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка тестовой отправки: {e}")
    
    @client.on(events.NewMessage(pattern='/channels'))
    async def channels_handler(event):
        """Показать список отслеживаемых каналов"""
        channels_list = "\n".join([f"• {channel}" for channel in CHANNELS[:20]])
        if len(CHANNELS) > 20:
            channels_list += f"\n• ... и еще {len(CHANNELS) - 20} каналов"
        
        await event.reply(
            f"📢 **Отслеживаемые каналы:**\n\n"
            f"{channels_list}\n\n"
            f"🌐 **Новостные сайты:** {len(WEBSITES)} источников"
        )
    
    @client.on(events.NewMessage(pattern='/debug'))
    async def debug_handler(event):
        """Отладочная информация"""
        try:
            # Проверяем подключение к каналам
            connected_channels = []
            for channel in CHANNELS[:15]:  # Проверяем первые 15 каналов
                try:
                    entity = await client.get_entity(channel)
                    channel_entities.append(entity)
                    connected_channels.append(f"✅ {channel}")
                except Exception as e:
                    connected_channels.append(f"❌ {channel}: {str(e)[:50]}")
            
            channels_status = "\n".join(connected_channels)
            
            await event.reply(
                f"🔧 **Отладочная информация:**\n\n"
                f"👥 Подписчиков: {len(load_subscribers())}\n"
                f"📡 Подключено каналов: {len(channel_entities)}\n"
                f"📊 Статус каналов:\n{channels_status}\n\n"
                f"🔄 Бот активен и работает"
            )
        except Exception as e:
            await event.reply(f"❌ Ошибка отладки: {e}")
    
    @client.on(events.NewMessage(pattern='/force_check'))
    async def force_check_handler(event):
        """Принудительная проверка"""
        try:
            await event.reply("🔄 Запускаю принудительную проверку...")
            await check_all_feeds(db_conn, client)
            await event.reply("✅ Проверка завершена!")
        except Exception as e:
            await event.reply(f"❌ Ошибка проверки: {e}")

    # ===== ФОНОВЫЕ ЗАДАЧИ =====
    async def periodic_checker():
        """Периодическая проверка RSS"""
        while True:
            try:
                await check_all_feeds(db_conn, client)
                logger.info("💤 Следующая проверка RSS через 5 минут")
                await asyncio.sleep(300)  # 5 минут
            except Exception as e:
                logger.error(f"❌ Ошибка в проверке RSS: {e}")
                await asyncio.sleep(60)
    
    async def status_logger():
        """Логирование статуса"""
        while True:
            subscribers = load_subscribers()
            logger.info(f"📊 Статус: {len(subscribers)} подписчиков, мониторинг {len(CHANNELS)} каналов и {len(WEBSITES)} сайтов")
            await asyncio.sleep(3600)  # 1 час

    # ===== ЗАПУСК =====
    try:
        logger.info("🎯 Запуск системы военных сводок...")
        
        await client.start(bot_token=BOT_TOKEN)
        
        logger.info("⏳ Подключаемся к Telegram каналам...")
        
        # Подключаемся к каналам и сохраняем entity
        connected_count = 0
        for channel in CHANNELS:
            try:
                entity = await client.get_entity(channel)
                channel_entities.append(entity)
                connected_count += 1
                logger.info(f"✅ Канал подключен: {channel}")
                await asyncio.sleep(0.5)  # Задержка между подключениями
            except Exception as e:
                logger.error(f"❌ Ошибка подключения к каналу {channel}: {e}")
        
        logger.info(f"✅ Бот успешно запущен!")
        logger.info(f"📊 Подписчиков: {len(subscribers)}")
        logger.info(f"📰 Каналов подключено: {connected_count}/{len(CHANNELS)}")
        logger.info(f"🌐 Сайтов: {len(WEBSITES)}")
        logger.info(f"🎯 Ожидаю сообщения из каналов...")
        
        # Запускаем фоновые задачи
        asyncio.create_task(periodic_checker())
        asyncio.create_task(status_logger())
        
        # Отправляем сообщение о запуске вечным подписчикам
        for user_id in PERMANENT_SUBSCRIBERS:
            try:
                await client.send_message(
                    user_id,
                    "🟢 **Система военных сводок запущена!**\n\n"
                    "✅ Бот активен и начал мониторинг:\n"
                    f"📰 {connected_count}/{len(CHANNELS)} Telegram каналов\n"
                    f"🌐 {len(WEBSITES)} новостных сайтов\n\n"
                    "⚡ Ожидайте важные военные сводки\n"
                    "🔧 Для отладки используйте /debug"
                )
            except Exception as e:
                logger.error(f"❌ Не удалось уведомить {user_id}: {e}")
        
        # Бесконечный цикл
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        await client.disconnect()
        db_conn.close()
        logger.info("🛑 Система остановлена")

if __name__ == '__main__':
    # Создаем файлы если их нет
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            pass
    
    # Запускаем бота
    asyncio.run(main())
