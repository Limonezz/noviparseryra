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
PERMANENT_SUBSCRIBERS = [
    1175795428,
    8019965642,
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
    'туризм', 'путешествие', 'отдых', 'курорт', 'отель', 'гостиница', 'авиабилет', ' тур', 'путевка',
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
    'юмор', 'анекдот', 'мем', 'прикол', 'розыгрыш', 'пранк', 'событие дня', 'утренний выпуск',
    
    # ===== НОВЫЕ СТОП-СЛОВА: ОПОВЕЩЕНИЯ И БЫТОВУХА =====
    
    # Ракетные, авиационные, БПЛА оповещения (часто капсом)
    'ракетная опасность', 'авиационная опасность', 'опасность бпла', 'бпла в воздухе',
    'воздушная опасность', 'воздушная тревога', 'пво сработало', 'пво работает',
    'обнаружены бпла', 'бпла над', 'дрон над', 'беспилотник над',
    'ракетная атака', 'авиаудар', 'воздушная атака', 'угроза с воздуха',
    'сирена', 'сирены', 'тревога', 'воздушная тревога',
    
    # Ночные/утренние чаты и пожелания
    'спокойной ночи', 'доброй ночи', 'доброе утро', 'с добрым утром',
    'ночные чаты', 'утренние чаты', 'ночной чат', 'утренний чат',
    'всем спокойной ночи', 'всем доброго утра', 'приветствую всех',
    'отличного дня', 'хорошего дня', 'удачного дня', 'прекрасного дня',
    'начался новый день', 'наступило утро', 'наступила ночь',
    
    # Сезонные красоты и природа
    'красота осени', 'осенние краски', 'осенний лес', 'осенняя природа',
    'зимняя сказка', 'зимние пейзажи', 'снегопад', 'первый снег',
    'весеннее настроение', 'весна пришла', 'весенние цветы',
    'летний вечер', 'летняя ночь', 'летний закат', 'летний рассвет',
    'красивые фото', 'красивый вид', 'пейзаж', 'природа',
    'фотография дня', 'фото дня', 'картинка дня',
    
    # Бытовые и личные темы
    'моё мнение', 'личное мнение', 'хочу рассказать', 'делюсь с вами',
    'уютный вечер', 'домашний уют', 'семейный вечер', 'личное',
    'мое творчество', 'творческий вечер', 'вдохновение',
    
    # Праздники и поздравления
    'поздравляю', 'поздравления', 'с праздником', 'с днем рождения',
    'новогодние', 'рождественские', 'пасхальные', 'международный день',
    
    # Капс и полукапс
    'ВНИМАНИЕ', 'ВСЕМ', 'СРОЧНО', 'ВАЖНО', 'ОПАСНОСТЬ', 'ТРЕВОГА',
    'УГРОЗА', 'ПРЕДУПРЕЖДЕНИЕ', 'ВОЗДУШНАЯ', 'РАКЕТНАЯ', 'АВИАЦИОННАЯ',
    
    # Общие бытовые темы
    'рецепт', 'кулинария', 'готовим', 'блюдо', 'еда',
    'совет', 'рекомендация', 'лайфхак', 'полезный совет',
    'интересный факт', 'факт дня', 'цитата дня', 'мудрость',
    
    # ===== ПРИГРАНИЧНЫЕ РЕГИОНЫ (ОТСИРАЮТСЯ) =====
    'Курск', 'Курская область', 'Белгород', 'Белгородская область', 'Брянск', 'Брянская область',
    'Воронеж', 'Воронежская область', 'Ростов', 'Ростовская область', 'Краснодар', 'Краснодарский край',
    'Крым', 'Севастополь', 'поныровский район', 'рыльский район', 'шебекинский район', 'валуйский район',
    'сумская область', 'харьковская область', 'луганская область', 'донецкая область',
    'запорожская область', 'херсонская область', 'николаевская область',
    'приграничье', 'приграничный', 'приграничная', 'приграничные',
    'курский', 'белгородский', 'брянский', 'воронежский', 'ростовский', 'краснодарский',
    'крымский', 'севастопольский'
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

# ===== УЛУЧШЕННЫЙ СУПЕР-ФИЛЬТР ДЛЯ ВОЙНЫ И ПОЛИТИКИ =====
def contains_war_keywords(text):
    """Проверяет, содержит ли текст ключевые слова войны и политики"""
    if not text:
        return False
        
    text_lower = text.lower()
    
    # Сначала проверяем стоп-слова - если есть, сразу отбрасываем
    for stop_word in STOP_WORDS:
        if stop_word.lower() in text_lower:
            logger.info(f"🚫 Отброшено из-за стоп-слова: {stop_word}")
            return False
    
    # Проверка на капс (слишком много заглавных букв)
    if has_too_many_caps(text):
        logger.info(f"🚫 Отброшено из-за избытка капса")
        return False
    
    # Затем проверяем военные ключевые слова
    for keyword in WAR_KEYWORDS:
        if keyword.lower() in text_lower:
            logger.info(f"✅ Одобрено по ключевому слову: {keyword}")
            return True
    
    return False

def has_too_many_caps(text):
    """Проверяет, не слишком ли много заглавных букв в тексте"""
    if len(text) < 10:
        return False
    
    # Считаем количество заглавных букв
    caps_count = sum(1 for char in text if char.isupper())
    caps_ratio = caps_count / len(text)
    
    # Если больше 30% текста - капс, отбрасываем
    return caps_ratio > 0.3

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
        async with aiohttp.ClientSession() as session:
            async with session.get(website_config['url']) as response:
                content = await response.text()
                feed = feedparser.parse(content)
                
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
        f"🎯 **Сводка новостей**\n"
        f"📰 **{article['source']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Читать на сайте]({article['link']})"
    )

# ===== ПЕРИОДИЧЕСКАЯ ПРОВЕРКА TELEGRAM КАНАЛОВ С СУПЕР-ФИЛЬТРОМ =====
async def check_telegram_channels(conn, bot):
    """Периодическая проверка Telegram каналов на новые сообщения"""
    try:
        logger.info("🔍 Начинаем проверку Telegram каналов...")
        
        for channel in CHANNELS:
            try:
                logger.info(f"📢 Проверяем канал: {channel}")
                
                # Получаем последние сообщения из канала
                messages = []
                async for message in bot.iter_messages(channel, limit=20):
                    if message.text and not message.is_group:  # Только текстовые сообщения
                        messages.append(message)
                
                logger.info(f"📄 Найдено сообщений в {channel}: {len(messages)}")
                
                # Обрабатываем сообщения в обратном порядке (от старых к новым)
                for message in reversed(messages):
                    await process_telegram_message(message, conn, bot, channel)
                
                await asyncio.sleep(2)  # Пауза между каналами
                
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке канала {channel}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки Telegram каналов: {e}")

async def process_telegram_message(message, conn, bot, channel_name):
    """Обработка сообщения из Telegram канала с жесткой фильтрацией"""
    try:
        text = message.text
        if not text:
            return
            
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
    message_url = f"https://t.me/{channel_name}/{message_id}"
