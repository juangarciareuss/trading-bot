# /notifications.py

import telegram
import asyncio
import config

async def send_telegram_alert(message):
    """
    Envía un mensaje de alerta a través del bot de Telegram de forma asíncrona.
    """
    try:
        bot = telegram.Bot(token=config.TELEGRAM_TOKEN)
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )
        print("✅ Alerta de Telegram enviada exitosamente.")
        return True
    except Exception as e:
        print(f"❌ Error al enviar alerta de Telegram: {e}")
        return False