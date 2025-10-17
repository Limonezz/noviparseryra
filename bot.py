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
    }
]

# ===== ВЕЧНЫЕ ПОДПИСЧИКИ =====
# ЗАМЕНИТЕ ЭТИ ID НА РЕАЛЬНЫЕ ID ПОЛЬЗОВАТЕЛЕЙ ТЕЛЕГРАМ!
PERMANENT_SUBSCRIBERS = [
    1175795428,   # ПРИМЕР: замените на реальный ID
    8019965642,   # ПРИМЕР: замените на реальный ID
]

# ===== СУПЕР-ФИЛЬТР: ТОЛЬКО ВОЙНА, ПОЛИТИКА, СЕРЬЕЗНЫЕ СОБЫТИЯ =====
WAR_KEYWORDS = [
    # Военные действия и оружие
    'обстрел', 'атака', 'прилет', 'диверсант', 'ДРГ', 'боеприпас', 'взрывчатка', 'ракета', 'Искандер',
    'пленный', 'плен', 'РЭБ', 'радиоэлектронная борьба', 'приграничье', 'наступление', 'контрнаступление',
    'окружение', 'штурм', 'артобстрел', 'миномет', 'артиллерия', 'танк', 'БМП', 'БТР', 'САУ',
    'беспилотник', 'дрон', 'FPV-дрон', 'Герань', 'Шахед', 'Ланцет', 'Куб', 'Бук', 'Панцирь', 'Тор',
    'С-300', 'С-400', 'Искандер', 'Калибр', 'Кинжал', 'Циркон', 'Х-101', 'Х-32', 'Х-59',
    'фортификация', 'укрепление', 'траншея', 'бункер', 'дот', 'дзот', 'заграждение', 'мина', 'фугас',
    
    # Военные формирования и операции
    'ВСУ', 'ВС РФ', 'ЧВК', 'Вагнер', 'Ахмат', 'Кадыров', 'ССО', 'разведка', 'диверсия', 'спецоперация',
    'наемник', 'контрактник', 'мобилизация', 'мобилизованный', 'призыв', 'военкомат',
    
    # Геополитика и конфликты
    'НАТО', 'альянс', 'США', 'Пентагон', 'Вашингтон', 'Байден', 'ЕС', 'Евросоюз', 'санкция', 'эмбарго',
    'военная помощь', 'вооружение', 'оружие', 'F-16', 'Абрамс', 'Леопард', 'Челленджер', 'ПАТРИОТ',
    'Хаймарс', 'арта', 'САУ', 'Брадли', 'Страйкер', 'Железный купол', 'ПВО', 'ПРО',
    
    # Территории и фронты
    'Донбасс', 'ДНР', 'ЛНР', 'Крым', 'Севастополь', 'Херсон', 'Запорожье', 'Мариуполь', 'Бахмут',
    'Авдеевка', 'Угледар', 'Волноваха', 'Лиман', 'Изюм', 'Купянск', 'Харьков', 'Суммы', 'Чернигов',
    'Луганск', 'Донецк', 'Мелитополь', 'Бердянск', 'Энергодар', 'Николаев', 'Одесса',
    
    # Российские регионы (приграничные)
    'Курск', 'Курская область', 'Белгород', 'Белгородская область', 'Брянск', 'Брянская область',
    'Воронеж', 'Воронежская область', 'Ростов', 'Ростовская область', 'Краснодар', 'Краснодарский край',
    'Крым', 'Севастополь', 'поныровский район', 'рыльский район', 'шебекинский район', 'валуйский район',
    
    # Политика и власть (только серьезное)
    'Путин', 'президент', 'губернатор', 'правительство', 'администрация', 'Госдума', 'Совет Федерации',
    'законопроект', 'законодательство', 'выборы', 'санкции', 'переговоры', 'дипломатия', 
    'международные отношения', 'саммит', 'встреча', 'партия', 'Единая Россия', 'оппозиция', 'иноагент',
    'Медведев', 'Песков', 'Лавров', 'Шойгу', 'Герасимов', 'Сурков', 'Патрушев', 'Бортников',
    
    # Экономика (только связанная с войной/политикой)
    'бюджет', 'финансирование', 'госконтракт', 'тендер', 'аукцион', 'оборонный заказ',
    'военно-промышленный комплекс', 'Уралвагонзавод', 'Ростех', 'Рособоронэкспорт', 'Алмаз-Антей',
    'Тактическое ракетное вооружение', 'Концерн Калашников', 'Вымпел', 'МиГ', 'Сухой', 'Туполев',
    'импортозамещение', 'субсидия', 'дотация',
    
    # Происшествия (только серьезные)
    'авария', 'катастрофа', 'обрушение', 'разрушение', 'взрыв', 'детонация', 'гибель', 'пострадавший',
    'уголовное дело', 'задержание', 'арест', 'суд', 'приговор', 'колония', 'СИЗО', 'следствие',
    
    # Энергетика и инфраструктура (критическая)
    'АЭС', 'атомная станция', 'Курская АЭС-2', 'Нововоронежская АЭС', 'электроэнергия',
    'газ', 'нефть', 'нефтепереработка', 'транспорт', 'дороги', 'мост', 'тоннель', 'порт', 'аэропорт',
    
    # Общество (только в контексте войны)
    'эвакуация', 'беженец', 'переселенец', 'гуманитарная помощь', 'мобилизация', 'военное положение'
]

# ===== СТОП-СЛОВА: ВСЕ НЕСЕРЬЕЗНЫЕ ТЕМЫ =====
STOP_WORDS = [
    # Спорт и развлечения
    'футбол', 'хоккей', 'теннис', 'баскетбол', 'волейбол', 'UFC', 'бокс', 'чемпионат', 'матч', 'гол',
    'спорт', 'олимпиада', 'спортсмен', 'тренер', 'сборная', 'лига', 'нхл', 'нба', 'клуб', 'игрок',
    'кино', 'сериал', 'актер', 'актриса', 'режиссер', 'премия', 'оскар', 'музыка', 'песня', 'альбом',
    'концерт', 'фестиваль', 'артист', 'группа', 'клип', 'чарт', 'номинация', 'кинофестиваль',
    
    # Наука и космос (не связанные с военными технологиями)
    'космос', 'астроном', 'планета', 'марс', 'луна', 'спутник', 'черная дыра', 'вспышка', 'солнц',
    'галактик', 'звезда', 'телескоп', 'научное открытие', 'исследование', 'эксперимент', 'лаборатория',
    'ученый', 'физик', 'химик', 'биолог', 'археолог', 'палеонтолог', 'динозавр', 'ископаемое',
    
    # Технологии (бытовые)
    'смартфон', 'iphone', 'android', 'гаджет', 'приложение', 'соцсеть', 'instagram', 'facebook',
    'twitter', 'tiktok', 'социальная сеть', 'мессенджер', 'программа', 'софт', 'апдейт', 'обновление',
    'ноутбук', 'компьютер', 'процессор', 'видеокарта', 'игровой', 'девайс',
    
    # Игры
    'игра', 'геймер', 'игровой', 'playstation', 'xbox', 'nintendo', 'киберспорт', 'стрим', 'твич',
    'steam', 'консоль', 'приставка', 'рpg', 'шутер', 'инди-игра', 'dlc', 'мод',
    
    # Еда, кулинария, мода
    'рецепт', 'кулинар', 'еда', 'бургер', 'пицца', 'ресторан', 'кафе', 'шеф-повар', 'меню', 'блюдо',
    'кухня', 'продукт', 'ингредиент', 'готовка', 'кулинария', 'десерт', 'выпечка', 'торт', 'пирог',
    'мода', 'дизайнер', 'показ', 'коллекция', 'модель', 'подиум', 'неделя моды', 'бренд', 'одежда',
    'наряд', 'костюм', 'платье', 'аксессуар', 'ювелирный', 'украшение',
    
    # Животные и природа
    'котик', 'кот', 'кошка', 'собака', 'питомец', 'животное', 'зоопарк', 'погода', 'гороскоп',
    'астролог', 'природа', 'заповедник', 'национальный парк', 'флора', 'фауна',
    
    # Культура и искусство (неполитические)
    'театр', 'спектакль', 'опера', 'балет', 'хор', 'оркестр', 'дирижер', 'выставка', 'музей',
    'галерея', 'художник', 'скульптор', 'картина', 'искусство', 'арт-',
    
    # Туризм и отдых
    'туризм', 'путешествие', 'отдых', 'курорт', 'отель', 'гостиница', 'авиабилет', 'тур', 'путевка',
    'экскурсия', 'достопримечательность', 'пляж', 'море', 'горы', 'горнолыжный',
    
    # Автомобили (бытовые)
    'автомобиль', 'машина', 'бмв', 'мерседес', 'тойота', 'хундай', 'киа', 'форд', 'шевроле', 'тесла',
    'двигатель', 'тюнинг', 'автоспорт', 'формула-1', 'драг-рейсинг',
    
    # Дом и быт
    'дом', 'квартира', 'ремонт', 'интерьер', 'дизайн интерьера', 'мебель', 'сантехника', 'стройматериалы',
    'сад', 'огород', 'растение', 'цветок', 'дача', 'огород',
    
    # Здоровье (бытовое)
    'диета', 'похудение', 'фитнес', 'тренажерный зал', 'йога', 'медитация', 'витамин', 'биодобавка',
    'бад', 'здоровое питание', 'суперфуд',
    
    # Развлекательные события
    'юмор', 'анекдот', 'мем', 'прикол', 'розыгрыш', 'пранк', 'событие дня', 'утренний выпуск'
]

SUBSCRIBERS_FILE = 'subscribers.txt'

# Фильтр спама
SPAM_PHRASES = [
    'бесплатно', 'купить', 'продать', 'заказать', 'скидка', 'акция', 'реклама',
    'коммерция', 'озон', 'wildberries', 'накрутка', 'подписчиков', 'лайков',
    'диплом', 'курсовая', 'утренняя зарядка', 'рецидивист', 'маркетплейс',
    'платим за ваш эксклюзив', 'трамп вернулся в tiktok'
]

SPAM_URL_THRESHOLD = 3

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

# ===== СИСТЕМА ПОДПИСЧИКОВ С ВЕЧНЫМИ ПОЛЬЗОВАТЕЛЯМИ =====
def load_subscribers():
    """Загрузка всех подписчиков (вечные + обычные)"""
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            file_subs = [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        file_subs = []
    
    # Объединяем вечных и обычных подписчиков, убираем дубли
    all_subs = list(set(PERMANENT_SUBSCRIBERS + file_subs))
    return all_subs

def save_subscribers(subscribers):
    """Сохранение только обычных подписчиков (без вечных)"""
    # Фильтруем вечных подписчиков
    regular_subs = [sub for sub in subscribers if sub not in PERMANENT_SUBSCRIBERS]
    
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            for user_id in regular_subs:
                f.write(f"{user_id}\n")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения подписчиков: {e}")

def add_subscriber(user_id):
    """Добавление обычного подписчика"""
    subscribers = load_subscribers()
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        logger.info(f"✅ Новый подписчик: {user_id}")
    return load_subscribers()

def remove_subscriber(user_id):
    """Удаление обычного подписчика (вечных нельзя удалить)"""
    if user_id in PERMANENT_SUBSCRIBERS:
        logger.info(f"⚠️ Нельзя удалить вечного подписчика: {user_id}")
        return load_subscribers()
        
    subscribers = load_subscribers()
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        logger.info(f"❌ Отписался: {user_id}")
    return load_subscribers()

# ===== СУПЕР-ФИЛЬТР ДЛЯ ВОЙНЫ И ПОЛИТИКИ =====
def contains_war_keywords(text):
    """Проверяет, содержит ли текст ключевые слова войны и политики"""
    if not text:
        return False
        
    text_lower = text.lower()
    
    # Сначала проверяем стоп-слова - если есть, сразу отбрасываем
    for stop_word in STOP_WORDS:
        if stop_word in text_lower:
            logger.info(f"🚫 Отброшено из-за стоп-слова: {stop_word}")
            return False
    
    # Затем проверяем военные ключевые слова
    for keyword in WAR_KEYWORDS:
        if keyword.lower() in text_lower:
            logger.info(f"✅ Одобрено по ключевому слову: {keyword}")
            return True
    
    return False

def is_spam_message(text):
    """Проверка на спам"""
    if not text:
        return True
        
    text_lower = text.lower()
    
    # Проверка спам-фраз
    for phrase in SPAM_PHRASES:
        if phrase in text_lower:
            return True
    
    # Проверка количества ссылок
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    if len(urls) > SPAM_URL_THRESHOLD:
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

# ===== ПАРСИНГ RSS С СУПЕР-ФИЛЬТРОМ =====
async def parse_rss_feed(website_config):
    """Парсинг RSS ленты с жесткой фильтрацией"""
    try:
        feed = feedparser.parse(website_config['url'])
        articles = []
        
        for entry in feed.entries[:15]:  # Берем 15 последних статей
            try:
                title = entry.title
                link = entry.link
                summary = entry.get('summary', '') or entry.get('description', '') or title
                
                # Объединяем для проверки
                full_text = f"{title} {summary}"
                
                # ЖЕСТКАЯ ФИЛЬТРАЦИЯ: только война и политика
                if contains_war_keywords(full_text) and not is_spam_message(full_text):
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'source': website_config['name'],
                        'text': full_text
                    })
                    
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга элемента RSS: {e}")
                continue
                
        return articles
        
    except Exception as e:
        logger.error(f"❌ Ошибка RSS {website_config['name']}: {e}")
        return []

async def check_all_feeds(conn, bot):
    """Проверка всех RSS лент"""
    try:
        all_articles = []
        
        for website in WEBSITES:
            logger.info(f"🌐 Проверяем {website['name']}")
            
            articles = await parse_rss_feed(website)
            all_articles.extend(articles)
            logger.info(f"📄 Найдено ВОЕННЫХ статей на {website['name']}: {len(articles)}")
            
            await asyncio.sleep(1)
        
        # Отправка новых статей
        sent_count = 0
        for article in all_articles:
            # Создаем ID на основе ссылки
            article_id = f"rss_{hash(article['link']) % 100000000}"
            
            if not is_post_sent(conn, article_id):
                # Отправляем всем подписчикам
                subscribers = load_subscribers()
                message = format_website_message(article)
                
                success_count = 0
                for user_id in subscribers:
                    try:
                        await bot.send_message(
                            user_id, 
                            message, 
                            parse_mode='Markdown',
                            link_preview=True
                        )
                        success_count += 1
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
                
                if success_count > 0:
                    mark_post_sent(conn, article_id, article['source'], article['title'])
                    sent_count += 1
                    logger.info(f"✅ Отправлено ВОЕННАЯ новость {success_count} подписчикам с {article['source']}")
        
        if sent_count > 0:
            logger.info(f"📨 Всего отправлено ВОЕННЫХ статей: {sent_count}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки лент: {e}")

def format_website_message(article):
    """Форматирование статьи для отправки"""
    title = article['title']
    if len(title) > 200:
        title = title[:200] + "..."
    
    return (
        f"🎯 **ВОЕННАЯ СВОДКА**\n"
        f"📰 **{article['source']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Читать на сайте]({article['link']})"
    )

# ===== ОБРАБОТКА TELEGRAM КАНАЛОВ С СУПЕР-ФИЛЬТРОМ =====
async def handle_channel_message(event, conn, bot):
    """Обработка сообщения из канала с жесткой фильтрацией"""
    try:
        message = event.message
        if not message.text:
            return
            
        text = message.text
        chat = await event.get_chat()
        channel_name = chat.username or chat.title or "Unknown"
        
        logger.info(f"📨 Сообщение из {channel_name}: {text[:100]}...")
        
        # СУПЕР-ФИЛЬТР: сначала спам, потом военные ключевые слова
        if is_spam_message(text) or not contains_war_keywords(text):
            return
        
        # Создаем ID сообщения
        message_id = f"tg_{channel_name}_{message.id}"
        
        # Проверяем, не отправляли ли уже
        if is_post_sent(conn, message_id):
            return
        
        # Форматируем и отправляем ВСЕМ подписчикам (вечным и обычным)
        subscribers = load_subscribers()
        message_text = format_telegram_message(text, channel_name, message.id)
        
        success_count = 0
        for user_id in subscribers:
            try:
                await bot.send_message(
                    user_id, 
                    message_text, 
                    parse_mode='Markdown',
                    link_preview=False
                )
                success_count += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
        
        if success_count > 0:
            mark_post_sent(conn, message_id, channel_name, text)
            logger.info(f"✅ Переслано ВОЕННОЕ сообщение из {channel_name} для {success_count} подписчиков")
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")

def format_telegram_message(text, channel_name, message_id):
    """Форматирование сообщения из Telegram канала"""
    # Обрезаем текст если слишком длинный
    if len(text) > 3500:
        text = text[:3500] + "..."
    
    # Форматируем время
    message_time = datetime.now().astimezone(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')
    
    # Создаем ссылку на сообщение
    message_url = f"https://t.me/{channel_name}/{message_id}" if not channel_name.startswith('@') else f"https://t.me/{channel_name[1:]}/{message_id}"
    
    return (
        f"🎯 **ВОЕННАЯ СВОДКА**\n"
        f"📢 **{channel_name}**\n"
        f"🕒 {message_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Открыть сообщение]({message_url})"
    )

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
async def main():
    """Главная функция бота"""
    # Инициализация клиентов
    user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    bot_client = TelegramClient('bot', API_ID, API_HASH)
    
    # Инициализация БД
    db_conn = init_db()
    
    # Создаем aiohttp сессию для RSS
    aiohttp_session = aiohttp.ClientSession()
    
    # Загружаем подписчиков при старте
    subscribers = load_subscribers()
    logger.info(f"👥 Загружено подписчиков: {len(subscribers)}")
    logger.info(f"🌟 Вечных подписчиков: {len(PERMANENT_SUBSCRIBERS)}")
    logger.info(f"📝 Обычных подписчиков: {len(subscribers) - len(PERMANENT_SUBSCRIBERS)}")
    logger.info(f"🎯 Военных ключевых слов: {len(WAR_KEYWORDS)}")
    logger.info(f"🚫 Стоп-слов: {len(STOP_WORDS)}")
    
    # ===== ОБРАБОТЧИКИ КОМАНД БОТА =====
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        subscribers = add_subscriber(user_id)
        await event.reply(
            "🎯 **Добро пожаловать в систему ВОЕННЫХ сводок!**\n\n"
            "✅ Вы подписались на получение ВОЕННЫХ новостей\n"
            "⚡ Теперь вы будете получать только важные военные и политические сводки\n\n"
            "🎯 **Фильтрация:** только война, политика, серьезные события\n"
            "🚫 **Исключено:** спорт, развлечения, наука, бытовые темы\n\n"
            "✨ Команды:\n"
            "/stop - отписаться\n"
            "/stats - статистика\n"
            "/id - узнать свой ID\n"
            "/filter - информация о фильтрах"
        )
        logger.info(f"👤 Новый подписчик ВОЕННЫХ сводок: {user_id}")
    
    @bot_client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        user_id = event.sender_id
        subscribers = remove_subscriber(user_id)
        await event.reply("❌ Вы отписались от военных сводок")
        logger.info(f"👤 Отписался от ВОЕННЫХ сводок: {user_id}")
    
    @bot_client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        subscribers = load_subscribers()
        permanent_count = len([s for s in subscribers if s in PERMANENT_SUBSCRIBERS])
        regular_count = len(subscribers) - permanent_count
        
        await event.reply(
            f"📊 **Статистика ВОЕННОЙ системы:**\n\n"
            f"👥 Всего подписчиков: {len(subscribers)}\n"
            f"🌟 Вечных подписчиков: {permanent_count}\n"
            f"📝 Обычных подписчиков: {regular_count}\n"
            f"📰 Отслеживается каналов: {len(CHANNELS)}\n"
            f"🌐 Отслеживается сайтов: {len(WEBSITES)}\n"
            f"🎯 Военных ключевых слов: {len(WAR_KEYWORDS)}\n"
            f"🚫 Стоп-слов: {len(STOP_WORDS)}\n\n"
            f"⚡ Режим: только ВОЕННЫЕ и ПОЛИТИЧЕСКИЕ новости"
        )
    
    @bot_client.on(events.NewMessage(pattern='/id'))
    async def id_handler(event):
        user_id = event.sender_id
        await event.reply(f"🆔 Ваш ID: `{user_id}`")
    
    @bot_client.on(events.NewMessage(pattern='/filter'))
    async def filter_handler(event):
        await event.reply(
            "🎯 **Система фильтрации ВОЕННЫХ новостей:**\n\n"
            "✅ **ПРОПУСКАЕТ:**\n"
            "• Военные действия и оружие\n"
            "• Геополитика и конфликты\n"
            "• Территории и фронты\n"
            "• Политика и власть\n"
            "• Серьезные происшествия\n\n"
            "🚫 **БЛОКИРУЕТ:**\n"
            "• Спорт и развлечения\n"
            "• Наука и космос\n"
            "• Технологии (бытовые)\n"
            "• Игры и хобби\n"
            "• Еда, мода, животные\n"
            "• И многое другое..."
        )
    
    @bot_client.on(events.NewMessage(pattern='/test'))
    async def test_handler(event):
        """Тестовая команда для проверки работы"""
        await event.reply("🎯 Система ВОЕННЫХ сводок работает! Ожидайте важные новости...")
    
    # ===== ОБРАБОТЧИКИ СООБЩЕНИЙ ИЗ КАНАЛОВ =====
    @user_client.on(events.NewMessage(chats=CHANNELS))
    async def channel_message_handler(event):
        """Мгновенная обработка ВОЕННЫХ сообщений из каналов"""
        await handle_channel_message(event, db_conn, bot_client)
    
    # ===== ФОНОВЫЕ ЗАДАЧИ =====
    async def rss_checker():
        """Фоновая задача для проверки RSS"""
        while True:
            try:
                logger.info("🔄 Проверка ВОЕННЫХ RSS лент...")
                await check_all_feeds(db_conn, bot_client)
                logger.info("💤 Следующая проверка через 10 минут")
                await asyncio.sleep(600)  # 10 минут
            except Exception as e:
                logger.error(f"❌ Ошибка в RSS чекере: {e}")
                await asyncio.sleep(60)
    
    async def status_logger():
        """Периодическое логирование статуса"""
        while True:
            try:
                subscribers = load_subscribers()
                logger.info(f"📊 Статус ВОЕННОЙ системы: {len(subscribers)} подписчиков")
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"❌ Ошибка в статус логгере: {e}")
                await asyncio.sleep(300)
    
    # ===== ЗАПУСК БОТА =====
    try:
        logger.info("🎯 Запуск системы ВОЕННЫХ сводок...")
        
        # Запускаем клиенты
        await bot_client.start(bot_token=BOT_TOKEN)
        await user_client.start()
        
        # Финальная проверка подписчиков
        subscribers = load_subscribers()
        logger.info("✅ Система ВОЕННЫХ сводок успешно запущена!")
        logger.info(f"📊 Итоговые данные:")
        logger.info(f"   👥 Всего подписчиков: {len(subscribers)}")
        logger.info(f"   🌟 Вечных подписчиков: {len(PERMANENT_SUBSCRIBERS)}")
        logger.info(f"   🎯 Военных ключевых слов: {len(WAR_KEYWORDS)}")
        logger.info(f"   🚫 Стоп-слов: {len(STOP_WORDS)}")
        logger.info("⚡ Режим: только ВОЕННЫЕ и ПОЛИТИЧЕСКИЕ новости")
        
        if len(subscribers) == 0:
            logger.warning("⚠️ ВНИМАНИЕ: Нет подписчиков! Отправьте боту /start")
        
        # Запускаем фоновые задачи
        asyncio.create_task(rss_checker())
        asyncio.create_task(status_logger())
        
        # Бесконечный цикл
        await asyncio.Future()
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске: {e}")
    finally:
        # Корректное завершение
        await user_client.disconnect()
        await bot_client.disconnect()
        await aiohttp_session.close()
        db_conn.close()
        logger.info("🛑 Система ВОЕННЫХ сводок остановлена")

if __name__ == '__main__':
    # Создаем необходимые файлы если их нет
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            pass
    
    # Запускаем бота
    asyncio.run(main())
