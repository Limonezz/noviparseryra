# ===== КОНФИГУРАЦИЯ =====
API_ID = '24826804'
API_HASH = '048e59c243cce6ff788a7da214bf8119'
SESSION_STRING = "1ApWapzMBuy-exPfF7z634N4Gos8qEwxZ92Nj1r4PWBEd55yqbaP_jcaTT6RiRwd5N4k2snlw_NaVLZ_2C4AvxvB_UG_exIrWgIOj6wsZrHlvBKt92xsGsEbZeo3l95d_6Vr5KKgWaxw531DwOrtWH-lerhkJ7XlDWtt_c225I7W0lIAk8P_k6gzm5oGvRFXqe0ivHxU7q4sJz6V61Ca0jyA_Sv-74OxB9l07HmIbOAC66oCtekxj4G5MTKKudofzmu2IqjqTgfFHwnKzE6hA3qik1SqSWdtWvmXHGb_44qPSk2dWGdW7vsN8inFuByDQLCF1_VLdGe0aFohbN0TXKKi7k0C8g2I="
BOT_TOKEN = '7597923417:AAEyZvTyyrPFQDz1o1qURDeCEoBFc0fMWaY'

# Telegram каналы (убрал проблемный канал)
CHANNELS = [
    'gubernator_46', 'kursk_info46', 'Alekhin_Telega', 'rian_ru',
    'kursk_ak46', 'zhest_kursk_146', 'novosti_efir', 'kursk_tipich',
    'seymkursk', 'kursk_smi', 'kursk_russia', 'belgorod01', 'kurskadm',
    'incident46', 'kurskbomond', 'prigranichie_radar1', 'grohot_pgr',
    'kursk_nasv', 'mchs_46', 'patriot046', 'kursk_now', 'Hinshtein',
    'incidentkursk', 'zhest_belgorod', 'RVvoenkor', 'pb_032',
    'tipicl32', 'bryansk_smi', 'Ria_novosti_rossiya','criminalru','bra_32','br_gorod','br_zhest', 'pravdas', 'wargonzo', 'ploschadmedia', 
    'belgorod_smi','ssigny','rucriminalinfo','kurskiy_harakter','dva_majors','ENews112',
    # Убрал 'mash' из-за ошибок
]

# Остальной код без изменений...

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
        website_count = len([w for w in WEBSITES if w.get('type') == 'rss']) + len([w for w in WEBSITES if w.get('type') == 'html'])
        
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
    
    # Функция для безопасной обработки каналов
    async def safe_get_entity(client, channel_name):
        try:
            entity = await client.get_entity(channel_name)
            return entity
        except Exception as e:
            logger.error(f"❌ Ошибка доступа к каналу {channel_name}: {e}")
            return None
    
    async def setup_channels():
        """Настройка каналов с обработкой ошибок"""
        valid_channels = []
        for channel in CHANNELS:
            entity = await safe_get_entity(user_client, channel)
            if entity:
                valid_channels.append(entity)
                logger.info(f"✅ Канал {channel} доступен")
            else:
                logger.warning(f"⚠️ Канал {channel} недоступен, пропускаем")
        
        return valid_channels
    
    # Устанавливаем обработчики для валидных каналов
    valid_channels = await setup_channels()
    
    @user_client.on(events.NewMessage(chats=valid_channels))
    async def instant_news_handler(event):
        """Обработчик новых сообщений из отслеживаемых каналов"""
        await process_new_message(user_client, bot_client, db_conn, event.message)
    
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
        logger.info(f"📰 Отслеживается Telegram каналов: {len(valid_channels)}/{len(CHANNELS)}")
        logger.info(f"🌐 Отслеживается веб-сайтов: {len(WEBSITES)}")
        logger.info(f"🔍 Ключевых слов для фильтрации: {len(KEYWORDS)}")
        logger.info(f"👥 Текущее количество подписчиков: {subscribers_count}")
        logger.info("⚡ Режим: мгновенная пересылка новых сообщений")
        
        if subscribers_count == 0:
            logger.warning("⚠️ ВНИМАНИЕ: Нет подписчиков! Отправьте боту /start")
        
        # Запускаем фоновую задачу для проверки сайтов
        asyncio.create_task(website_checker())
        
        # Бесконечный цикл для поддержания работы бота
        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        await user_client.disconnect()
        await bot_client.disconnect()
        await aiohttp_session.close()
        db_conn.close()

if __name__ == '__main__':
    asyncio.run(main())
