# Telegram News Bots

Два Telegram бота для мониторинга новостей:

1. **Telegram Monitor Bot** - мониторит Telegram каналы и отправляет новости с ключевыми словами
2. **RSS News Bot** - парсит RSS ленты сайтов и отправляет релевантные новости

## Установка на Railway

1. Создайте новый проект на Railway
2. Подключите GitHub репозиторий
3. Добавьте переменные окружения в настройках Railway:
   - `API_ID` - ваш Telegram API ID
   - `API_HASH` - ваш Telegram API Hash  
   - `BOT_TOKEN` - токен вашего Telegram бота
   - `SESSION_STRING` - сессия для Telethon

4. Railway автоматически запустит оба бота

## Локальная установка

```bash
pip install -r requirements.txt

# Запуск бота для мониторинга Telegram каналов
python telegram_monitor_bot.py

# Запуск бота для RSS новостей  
python rss_news_bot.py
