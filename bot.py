import asyncio
import sqlite3
import os
import time
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import logging
import re
import aiohttp
import feedparser
import hashlib

# ===== КОНФИГУРАЦИЯ =====
API_ID = 24826804
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

# ===== ВЕЧНЫЕ ПОДПИСЧИКИ =====
PERMANENT_SUBSCRIBERS = [
    1175795428,   # ПРИМЕР: замените на реальный ID
    8019965642,   # ПРИМЕР: замените на реальный ID
]
# ===== ТЕСТОВЫЕ КАНАЛЫ (100% рабочие) =====
TEST_CHANNELS = [
    'rian_ru',           # РИА Новости - точно рабочий
    'rt_russian',        # RT на русском - точно рабочий  
    'meduzalive',        # Медуза - точно рабочий
    'bbbreaking',        # Breaking News - точно рабочий
    'readovkanews',      # Readovka - точно рабочий
]

# ===== РЕАЛЬНЫЕ КАНАЛЫ =====
REAL_CHANNELS = [
    'gubernator_46', 'kursk_info46', 'Alekhin_Telega', 
    'kursk_ak46', 'zhest_kursk_146', 'novosti_efir', 'kursk_tipich',
    'seymkursk', 'kursk_smi', 'kursk_russia', 'belgorod01', 'kurskadm',
    'incident46', 'kurskbomond', 'prigranichie_radar1', 'grohot_pgr',
    'kursk_nasv', 'mchs_46', 'patriot046', 'kursk_now', 'Hinshtein',
    'incidentkursk', 'zhest_belgorod', 'RVvoenkor', 'pb_032',
    'tipicl32', 'bryansk_smi', 'Ria_novosti_rossiya', 'criminalru',
    'bra_32', 'br_gorod', 'br_zhest', 'pravdas', 'wargonzo', 'ploschadmedia', 
    'belgorod_smi', 'ssigny', 'rucriminalinfo', 'kurskiy_harakter',
    'dva_majors', 'ENews112'
]

# Используем тестовые каналы для начала
CHANNELS = TEST_CHANNELS

# ===== САЙТЫ =====
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

# ===== УПРОЩЕННЫЕ ФИЛЬТРЫ ДЛЯ ТЕСТА =====
KEYWORDS = [
    'Курск', 'Белгород', 'Брянск', 'Украина', 'Россия', 'война', 'обстрел',
    'атака', 'Путин', 'Зеленский', 'НАТО', 'США', 'санкции', 'мобилизация',
    'дрон', 'ракета', 'ВСУ', 'ВС РФ', 'спецоперация', 'Донбасс', 'Крым'
]

STOP_WORDS = [
    'футбол', 'хоккей', 'UFC', 'бокс', 'спорт', 'кино', 'сериал', 'музыка',
    'космос', 'смартфон', 'iphone', 'игра', 'рецепт', 'еда', 'мода', 'котик'
]

SUBSCRIBERS_FILE = 'subscribers.txt'

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log', encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== СИСТЕМА ПОДПИСЧИКОВ =====
class SubscriberManager:
    def __init__(self):
        self.permanent_subscribers = PERMANENT_SUBSCRIBERS
        
    def load_subscribers(self):
        try:
            with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                file_subs = [int(line.strip()) for line in f if line.strip().isdigit()]
        except FileNotFoundError:
            file_subs = []
        
        return list(set(self.permanent_subscribers + file_subs))
    
    def save_subscribers(self, subscribers):
        regular_subs = [sub for sub in subscribers if sub not in self.permanent_subscribers]
        try:
            with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
                for user_id in regular_subs:
                    f.write(f"{user_id}\n")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения подписчиков: {e}")
    
    def add_subscriber(self, user_id):
        subscribers = self.load_subscribers()
        if user_id not in subscribers:
            subscribers.append(user_id)
            self.save_subscribers(subscribers)
            logger.info(f"✅ Новый подписчик: {user_id}")
        return self.load_subscribers()
    
    def remove_subscriber(self, user_id):
        if user_id in self.permanent_subscribers:
            logger.info(f"⚠️ Нельзя удалить вечного подписчика: {user_id}")
            return self.load_subscribers()
            
        subscribers = self.load_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            self.save_subscribers(subscribers)
            logger.info(f"❌ Отписался: {user_id}")
        return self.load_subscribers()

# ===== МЕНЕДЖЕР БАЗЫ ДАННЫХ =====
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('news_v2.db', check_same_thread=False)
        self.init_db()
        
    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_posts (
                post_id TEXT PRIMARY KEY,
                source TEXT,
                content_hash TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def is_post_sent(self, post_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT post_id FROM sent_posts WHERE post_id = ?", (post_id,))
        return cursor.fetchone() is not None
    
    def mark_post_sent(self, post_id, source, content):
        cursor = self.conn.cursor()
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cursor.execute(
            "INSERT OR IGNORE INTO sent_posts (post_id, source, content_hash) VALUES (?, ?, ?)",
            (post_id, source, content_hash)
        )
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ===== ФИЛЬТРЫ =====
class ContentFilter:
    def __init__(self):
        self.keywords = KEYWORDS
        self.stop_words = STOP_WORDS
        
    def contains_keywords(self, text):
        if not text:
            return False
            
        text_lower = text.lower()
        
        # Сначала проверяем стоп-слова
        for stop_word in self.stop_words:
            if stop_word.lower() in text_lower:
                logger.debug(f"🚫 Отфильтровано стоп-словом: {stop_word}")
                return False
        
        # Затем ключевые слова
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                logger.debug(f"✅ Прошло по ключевому слову: {keyword}")
                return True
        
        return False
    
    def is_spam(self, text):
        if not text:
            return True
            
        text_lower = text.lower()
        
        spam_indicators = [
            'бесплатно', 'купить', 'продать', 'заказать', 'скидка', 'акция',
            'реклама', 'коммерция', 'озон', 'wildberries'
        ]
        
        for indicator in spam_indicators:
            if indicator in text_lower:
                return True
        
        # Проверка количества ссылок
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        if len(urls) > 3:
            return True
        
        return False

# ===== ПАРСЕР САЙТОВ =====
class WebsiteParser:
    def __init__(self, db_manager, filter_manager):
        self.db = db_manager
        self.filter = filter_manager
        
    async def parse_rss_feed(self, website_config):
        try:
            logger.info(f"🌐 Парсим RSS: {website_config['name']}")
            feed = feedparser.parse(website_config['url'])
            articles = []
            
            for entry in feed.entries[:15]:
                try:
                    title = entry.title.strip()
                    link = entry.link
                    summary = (entry.get('summary', '') or entry.get('description', '') or '').strip()
                    
                    if not title:
                        continue
                        
                    full_text = f"{title} {summary}"
                    
                    # Проверяем фильтры
                    if (self.filter.contains_keywords(full_text) and 
                        not self.filter.is_spam(full_text)):
                        
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
                    
            logger.info(f"📄 Найдено статей на {website_config['name']}: {len(articles)}")
            return articles
            
        except Exception as e:
            logger.error(f"❌ Ошибка RSS {website_config['name']}: {e}")
            return []
    
    async def check_all_feeds(self, bot, subscriber_manager):
        try:
            all_articles = []
            
            for website in WEBSITES:
                articles = await self.parse_rss_feed(website)
                all_articles.extend(articles)
                await asyncio.sleep(1)
            
            # Отправка новых статей
            sent_count = 0
            for article in all_articles:
                article_id = f"rss_{hashlib.md5(article['link'].encode()).hexdigest()}"
                
                if not self.db.is_post_sent(article_id):
                    message = self.format_website_message(article)
                    subscribers = subscriber_manager.load_subscribers()
                    
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
                            await asyncio.sleep(0.05)
                        except Exception as e:
                            logger.error(f"❌ Ошибка отправки {user_id}: {e}")
                    
                    if success_count > 0:
                        self.db.mark_post_sent(article_id, article['source'], article['text'])
                        sent_count += 1
                        logger.info(f"✅ Отправлено статья с {article['source']} для {success_count} подписчиков")
            
            if sent_count > 0:
                logger.info(f"📨 Всего отправлено новых статей: {sent_count}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки лент: {e}")
    
    def format_website_message(self, article):
        title = article['title']
        if len(title) > 200:
            title = title[:200] + "..."
        
        return (
            f"🌐 **НОВОСТЬ С САЙТА**\n"
            f"📰 **{article['source']}**\n"
            f"🕒 {datetime.now().strftime('%H:%M %d.%m.%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**{title}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 [Читать на сайте]({article['link']})"
        )

# ===== ОБРАБОТЧИК TELEGRAM КАНАЛОВ =====
class TelegramChannelHandler:
    def __init__(self, db_manager, filter_manager, subscriber_manager):
        self.db = db_manager
        self.filter = filter_manager
        self.subscriber_manager = subscriber_manager
        self.processed_messages = set()
        
    async def setup_channels(self, user_client):
        """Проверяем доступность каналов"""
        logger.info("🔍 Проверяем доступность каналов...")
        available_channels = []
        
        for channel in CHANNELS:
            try:
                entity = await user_client.get_entity(channel)
                available_channels.append(entity)
                logger.info(f"   ✅ {channel} - ДОСТУПЕН")
            except Exception as e:
                logger.error(f"   ❌ {channel} - НЕДОСТУПЕН: {e}")
        
        return available_channels
    
    async def handle_message(self, event, bot):
        """Обработчик сообщений из каналов"""
        try:
            message = event.message
            if not message.text:
                return
                
            text = message.text.strip()
            if not text:
                return
            
            # Получаем информацию о канале
            try:
                chat = await event.get_chat()
                channel_name = getattr(chat, 'username', None) or getattr(chat, 'title', 'Unknown')
            except:
                channel_name = 'Unknown'
            
            message_id = message.id
            unique_id = f"{channel_name}_{message_id}"
            
            # Защита от дубликатов в памяти
            if unique_id in self.processed_messages:
                return
            self.processed_messages.add(unique_id)
            
            # Очистка старых ID (чтобы не засорять память)
            if len(self.processed_messages) > 1000:
                self.processed_messages.clear()
            
            logger.info(f"📨 ПОЛУЧЕНО СООБЩЕНИЕ из {channel_name}: {text[:100]}...")
            
            # ПРИМЕНЯЕМ ФИЛЬТРЫ
            if self.filter.is_spam(text):
                logger.info(f"🚫 ОТФИЛЬТРОВАНО КАК СПАМ: {channel_name}")
                return
                
            if not self.filter.contains_keywords(text):
                logger.info(f"🚫 НЕТ КЛЮЧЕВЫХ СЛОВ: {channel_name}")
                return
            
            # Проверяем в БД
            post_id = f"tg_{channel_name}_{message_id}"
            if self.db.is_post_sent(post_id):
                logger.info(f"ℹ️ УЖЕ ОТПРАВЛЯЛИ: {channel_name}")
                return
            
            logger.info(f"🎯 ПРОШЛО ФИЛЬТРЫ! Отправляем: {channel_name}")
            
            # Форматируем сообщение
            message_text = self.format_telegram_message(text, channel_name, message_id)
            
            # Отправляем всем подписчикам
            subscribers = self.subscriber_manager.load_subscribers()
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
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки {user_id}: {e}")
            
            if success_count > 0:
                self.db.mark_post_sent(post_id, channel_name, text)
                logger.info(f"✅ УСПЕХ! Отправлено сообщение из {channel_name} для {success_count} подписчиков")
            else:
                logger.warning(f"⚠️ Сообщение из {channel_name} не отправлено никому")
                
        except Exception as e:
            logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА в обработчике: {e}")
    
    def format_telegram_message(self, text, channel_name, message_id):
        if len(text) > 3500:
            text = text[:3500] + "..."
        
        message_time = datetime.now().astimezone(pytz.timezone('Europe/Moscow')).strftime('%H:%M %d.%m.%Y')
        message_url = f"https://t.me/{channel_name}/{message_id}"
        
        return (
            f"🚨 **НОВАЯ НОВОСТЬ**\n"
            f"📢 **{channel_name}**\n"
            f"🕒 {message_time}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{text}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 [Открыть сообщение]({message_url})"
        )

# ===== ГЛАВНЫЙ БОТ =====
class NewsBot:
    def __init__(self):
        self.subscriber_manager = SubscriberManager()
        self.db_manager = DatabaseManager()
        self.content_filter = ContentFilter()
        self.website_parser = WebsiteParser(self.db_manager, self.content_filter)
        self.telegram_handler = TelegramChannelHandler(
            self.db_manager, self.content_filter, self.subscriber_manager
        )
        
        self.user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        self.bot_client = TelegramClient('bot_session', API_ID, API_HASH)
        
        self.is_running = False
        
    async def setup_handlers(self):
        """Настройка обработчиков команд бота"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            user_id = event.sender_id
            self.subscriber_manager.add_subscriber(user_id)
            await event.reply(
                "🎯 **БОТ АКТИВИРОВАН!**\n\n"
                "✅ Вы подписались на военные сводки\n"
                "⚡ Режим: мгновенные уведомления\n\n"
                "📊 Статистика:\n"
                f"• Каналов: {len(CHANNELS)}\n"
                f"• Сайтов: {len(WEBSITES)}\n"
                f"• Фильтров: {len(KEYWORDS)}\n\n"
                "✨ Команды:\n"
                "/stop - отписаться\n"
                "/stats - статистика\n"
                "/test - тест работы\n"
                "/debug - отладочная информация"
            )
            logger.info(f"👤 Новый подписчик: {user_id}")
        
        @self.bot_client.on(events.NewMessage(pattern='/stop'))
        async def stop_handler(event):
            user_id = event.sender_id
            self.subscriber_manager.remove_subscriber(user_id)
            await event.reply("❌ Вы отписались от рассылки")
            logger.info(f"👤 Отписался: {user_id}")
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            subscribers = self.subscriber_manager.load_subscribers()
            await event.reply(
                f"📊 **СТАТИСТИКА СИСТЕМЫ:**\n\n"
                f"👥 Подписчиков: {len(subscribers)}\n"
                f"🌟 Вечных: {len(PERMANENT_SUBSCRIBERS)}\n"
                f"📰 Каналов: {len(CHANNELS)}\n"
                f"🌐 Сайтов: {len(WEBSITES)}\n"
                f"🎯 Ключевых слов: {len(KEYWORDS)}\n"
                f"🚫 Стоп-слов: {len(STOP_WORDS)}\n\n"
                f"⚡ Статус: {'РАБОТАЕТ' if self.is_running else 'ОСТАНОВЛЕН'}"
            )
        
        @self.bot_client.on(events.NewMessage(pattern='/test'))
        async def test_handler(event):
            """Тестовая команда - отправляем тестовое сообщение"""
            user_id = event.sender_id
            test_message = (
                "🧪 **ТЕСТОВОЕ СООБЩЕНИЕ**\n\n"
                "Если вы видите это сообщение, значит:\n"
                "✅ Бот работает\n"
                "✅ Рассылка работает\n"
                "✅ Вы подписаны\n\n"
                f"🕒 Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"
            )
            
            try:
                await self.bot_client.send_message(
                    user_id,
                    test_message,
                    parse_mode='Markdown'
                )
                await event.reply("✅ Тестовое сообщение отправлено!")
                logger.info(f"✅ Тест пройден для пользователя {user_id}")
            except Exception as e:
                await event.reply(f"❌ Ошибка отправки: {e}")
                logger.error(f"❌ Тест не пройден: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/debug'))
        async def debug_handler(event):
            """Отладочная информация"""
            subscribers = self.subscriber_manager.load_subscribers()
            
            debug_info = (
                "🐛 **ОТЛАДОЧНАЯ ИНФОРМАЦИЯ**\n\n"
                f"🏃‍♂️ Статус: {'РАБОТАЕТ' if self.is_running else 'СТОП'}\n"
                f"👥 Подписчиков: {len(subscribers)}\n"
                f"📡 Каналов в мониторинге: {len(CHANNELS)}\n"
                f"🕒 Время запуска: {getattr(self, 'start_time', 'Неизвестно')}\n"
                f"💾 Обработано сообщений: {len(self.telegram_handler.processed_messages)}\n\n"
                "📋 Каналы:\n"
            )
            
            # Показываем первые 10 каналов
            for i, channel in enumerate(CHANNELS[:10]):
                debug_info += f"   {i+1}. {channel}\n"
            
            if len(CHANNELS) > 10:
                debug_info += f"   ... и еще {len(CHANNELS) - 10} каналов\n"
            
            await event.reply(debug_info)
    
    async def setup_telegram_monitoring(self):
        """Настройка мониторинга Telegram каналов"""
        logger.info("📡 Настраиваем мониторинг Telegram каналов...")
        
        # Проверяем доступность каналов
        available_channels = await self.telegram_handler.setup_channels(self.user_client)
        
        if not available_channels:
            logger.error("❌ НЕТ ДОСТУПНЫХ КАНАЛОВ! Проверьте настройки.")
            return False
        
        logger.info(f"✅ Доступно каналов: {len(available_channels)}")
        
        # Регистрируем обработчик для ВСЕХ сообщений
        @self.user_client.on(events.NewMessage)
        async def universal_handler(event):
            """Универсальный обработчик всех сообщений"""
            try:
                # Проверяем, что сообщение из нужного нам канала
                chat = await event.get_chat()
                channel_id = getattr(chat, 'username', None) or getattr(chat, 'id', None)
                
                if channel_id:
                    channel_str = str(channel_id).lower()
                    # Проверяем, есть ли этот канал в нашем списке
                    for channel in CHANNELS:
                        if channel.lower() in channel_str:
                            await self.telegram_handler.handle_message(event, self.bot_client)
                            break
            except Exception as e:
                logger.error(f"❌ Ошибка в универсальном обработчике: {e}")
        
        return True
    
    async def start_periodic_tasks(self):
        """Запуск периодических задач"""
        
        async def rss_checker():
            while self.is_running:
                try:
                    await self.website_parser.check_all_feeds(self.bot_client, self.subscriber_manager)
                    await asyncio.sleep(300)  # 5 минут
                except Exception as e:
                    logger.error(f"❌ Ошибка в RSS чекере: {e}")
                    await asyncio.sleep(60)
        
        async def status_logger():
            while self.is_running:
                try:
                    subscribers = self.subscriber_manager.load_subscribers()
                    logger.info(f"📊 СТАТУС: {len(subscribers)} подписчиков, {len(self.telegram_handler.processed_messages)} сообщений обработано")
                    await asyncio.sleep(1800)  # 30 минут
                except Exception as e:
                    logger.error(f"❌ Ошибка в статус логгере: {e}")
                    await asyncio.sleep(300)
        
        # Запускаем задачи
        asyncio.create_task(rss_checker())
        asyncio.create_task(status_logger())
    
    async def run(self):
        """Главная функция запуска бота"""
        try:
            logger.info("🚀 ЗАПУСКАЕМ БОТА...")
            
            # Запускаем клиенты
            await self.bot_client.start(bot_token=BOT_TOKEN)
            await self.user_client.start()
            
            # Настраиваем обработчики
            await self.setup_handlers()
            
            # Настраиваем мониторинг каналов
            monitoring_ready = await self.setup_telegram_monitoring()
            if not monitoring_ready:
                logger.error("❌ НЕ УДАЛОСЬ НАСТРОИТЬ МОНИТОРИНГ КАНАЛОВ!")
                return
            
            # Запускаем периодические задачи
            self.is_running = True
            self.start_time = datetime.now().strftime('%H:%M:%S %d.%m.%Y')
            await self.start_periodic_tasks()
            
            # Статистика при запуске
            subscribers = self.subscriber_manager.load_subscribers()
            logger.info("✅ БОТ УСПЕШНО ЗАПУЩЕН!")
            logger.info(f"📊 СТАТИСТИКА ПРИ ЗАПУСКЕ:")
            logger.info(f"   👥 Подписчиков: {len(subscribers)}")
            logger.info(f"   📡 Каналов: {len(CHANNELS)}")
            logger.info(f"   🌐 Сайтов: {len(WEBSITES)}")
            logger.info(f"   🎯 Ключевых слов: {len(KEYWORDS)}")
            logger.info("⚡ РЕЖИМ: МГНОВЕННЫЕ УВЕДОМЛЕНИЯ")
            
            # Отправляем тестовое сообщение первому подписчику
            if subscribers:
                try:
                    await self.bot_client.send_message(
                        subscribers[0],
                        "✅ **СИСТЕМА ЗАПУЩЕНА**\n\nБот начал мониторинг каналов и сайтов. Ожидайте новости!",
                        parse_mode='Markdown'
                    )
                except:
                    pass
            
            # Бесконечный цикл
            await asyncio.Future()
            
        except Exception as e:
            logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}")
            self.is_running = False
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Корректное завершение работы"""
        self.is_running = False
        logger.info("🛑 ОСТАНАВЛИВАЕМ БОТА...")
        
        try:
            await self.user_client.disconnect()
            await self.bot_client.disconnect()
            self.db_manager.close()
        except:
            pass
        
        logger.info("✅ БОТ ОСТАНОВЛЕН")

# ===== ЗАПУСК =====
async def main():
    # Создаем необходимые файлы
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            pass
    
    # Запускаем бота
    bot = NewsBot()
    await bot.run()

if __name__ == '__main__':
    # Явно устанавливаем политику событий для Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Запускаем
    asyncio.run(main())
