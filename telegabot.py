import asyncio
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import logging
import re

# ===== КОНФИГУРАЦИЯ ДЛЯ ТЕЛЕГРАМ МОНИТОРИНГА =====
API_ID = os.environ.get('API_ID', '24826804')
API_HASH = os.environ.get('API_HASH', '048e59c243cce6ff788a7da214bf8119')
SESSION_STRING = os.environ.get('SESSION_STRING_TELEGRAM', "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I=")
BOT_TOKEN = os.environ.get('BOT_TOKEN_TELEGRAM', '8306634056:AAEXAd3P6TnH7OgpVoYCoI1FezacXtJuei8')

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

SUBSCRIBERS_FILE = 'subscribers_telegram.txt'

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TelegramMonitorBot')

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
    conn = sqlite3.connect('telegram_news.db', check_same_thread=False)
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

# ===== ТЕЛЕГРАМ КАНАЛЫ =====
async def send_to_subscribers(client, message_text, post_id, channel_name, conn):
    if is_post_sent(conn, post_id):
        return 0
    
    subscribers = load_subscribers()
    success_count = 0
    
    for user_id in subscribers:
        try:
            await client.send_message(user_id, message_text, parse_mode='Markdown')
            success_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка отправки {user_id}: {e}")
    
    if success_count > 0:
        mark_post_sent(conn, post_id, channel_name, message_text[:100])
        logger.info(f"ОТПРАВЛЕНО ИЗ {channel_name} для {success_count} подписчиков")
    
    return success_count

# ===== ОСНОВНОЙ БОТ =====
async def main():
    logger.info("Запуск Telegram Monitor Bot...")
    
    # Инициализация клиента для мониторинга каналов (С СЕССИЕЙ)
    client = TelegramClient(
        StringSession(SESSION_STRING), 
        API_ID, 
        API_HASH
    )
    
    db_conn = init_db()
    subscribers = load_subscribers()
    logger.info(f"Telegram Monitor Bot запущен! Подписчиков: {len(subscribers)}")

    # Храним ID каналов
    channel_ids = {}

    # Получаем ID всех каналов при запуске
    async def get_channel_ids():
        logger.info("Получение ID каналов...")
        for channel in CHANNELS:
            try:
                entity = await client.get_entity(channel)
                channel_ids[entity.id] = channel
                logger.info(f"Канал {channel} -> ID: {entity.id}")
            except Exception as e:
                logger.error(f"Ошибка получения ID для {channel}: {e}")

    # Обработчик ВСЕХ сообщений
    @client.on(events.NewMessage)
    async def handler(event):
        try:
            # Пропускаем свои сообщения
            if event.message.out:
                return
            
            chat_id = event.chat_id
            
            # Если это известный канал
            if chat_id in channel_ids:
                channel_name = channel_ids[chat_id]
                message_text = event.message.text or event.message.caption or ""
                
                if message_text.strip():
                    logger.info(f"СООБЩЕНИЕ ИЗ {channel_name}: {message_text[:100]}...")
                    
                    if contains_war_keywords(message_text):
                        logger.info(f"НАЙДЕНЫ КЛЮЧЕВЫЕ СЛОВА В {channel_name}!")
                        
                        post_id = f"tg_{chat_id}_{event.message.id}"
                        formatted_message = f"🎯 **{channel_name}**\n\n{message_text}"
                        
                        success_count = await send_to_subscribers(client, formatted_message, post_id, channel_name, db_conn)
                        if success_count > 0:
                            logger.info(f"УСПЕХ! Отправлено {success_count} подписчикам")
            
            # Дополнительно: логируем ВСЕ сообщения для отладки
            else:
                try:
                    chat = await event.get_chat()
                    chat_name = getattr(chat, 'username', None) or getattr(chat, 'title', f"ID_{chat_id}")
                    message_text = event.message.text or event.message.caption or ""
                    if message_text.strip() and len(message_text) > 10:
                        logger.debug(f"ДРУГОЙ ЧАТ {chat_name}: {message_text[:50]}...")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")

    # Команды бота
    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        subscribers = add_subscriber(user_id)
        await event.reply("✅ Подписан на новости из Telegram каналов!")
        logger.info(f"Новый подписчик: {user_id}")

    @client.on(events.NewMessage(pattern='/stop'))
    async def stop_handler(event):
        user_id = event.sender_id
        subscribers = remove_subscriber(user_id)
        await event.reply("❌ Отписан от новостей из Telegram каналов")

    @client.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        subscribers = load_subscribers()
        await event.reply(f"📊 Статистика Telegram Monitor Bot:\n\nПодписчиков: {len(subscribers)}\nМониторим каналов: {len(CHANNELS)}\nЗагружено каналов: {len(channel_ids)}")

    @client.on(events.NewMessage(pattern='/test'))
    async def test_handler(event):
        await event.reply("🟢 Telegram Monitor Bot работает! Ожидаю сообщения из каналов...")

    @client.on(events.NewMessage(pattern='/debug'))
    async def debug_handler(event):
        await event.reply(f"🔧 Отладка:\nКаналов в мониторинге: {len(channel_ids)}\nПодписчиков: {len(load_subscribers())}")

    # Запуск
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("Telegram Monitor Bot успешно запущен!")
        
        # Получаем ID каналов
        await get_channel_ids()
        logger.info(f"Загружено {len(channel_ids)} каналов из {len(CHANNELS)}")
        
        # Уведомляем вечных подписчиков
        for user_id in PERMANENT_SUBSCRIBERS:
            try:
                await client.send_message(
                    user_id, 
                    f"🟢 Telegram Monitor Bot запущен!\n"
                    f"Мониторим {len(channel_ids)} каналов\n"
                    f"Используем токен: {BOT_TOKEN[:10]}..."
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить {user_id}: {e}")
        
        logger.info("Ожидаю сообщения из каналов...")
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
