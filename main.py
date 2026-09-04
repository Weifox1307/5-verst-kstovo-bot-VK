import os
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')
# Чаты Кстово
CHAT_IDS = ["2000000001", "2000000002", "2000000263", "-231155212"]
VK_API_VERSION = "5.131"

def get_holidays():
    url = "https://my-calend.ru/holidays"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        holidays = []
        # Ищем элементы списка праздников на странице
        items = soup.select('.holidays-items li')
        
        for item in items:
            title = item.text.strip()
            # Убираем лишний мусор и слишком длинные описания
            if title and len(title) < 100:
                holidays.append(title)
                
            # Берем топ-7 праздников, чтобы не делать сообщение слишком огромным
            if len(holidays) >= 7:
                break
                
        if not holidays:
            return ["День отличного настроения (праздников не найдено, но мы не унываем!)"]
            
        return holidays
        
    except Exception as e:
        print(f"Ошибка при парсинге праздников: {e}")
        # Фолбэк на случай, если сайт лежит, чтобы воркфлоу не упал
        return ["День бега", "День хорошего настроения", "День подготовки к 5 вёрст"]

def format_message(holidays):
    # Набор праздничных эмодзи
    emojis = ["✨", "🎉", "🎈", "🥳", "🎊", "🔥", "🚀", "🌟", "💫", "🧡", "🍰", "🙌"]
    
    # Получаем текущую дату по МСК (GitHub Actions работает в UTC, поэтому +3 часа)
    now_msk = datetime.utcnow() + timedelta(hours=3)
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", 
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    
    date_str = f"{now_msk.day} {months[now_msk.month - 1]}"

    msg = f"🌅 Доброе утро, Кстово! 🧡\n\n📅 Сегодня, {date_str}, отмечаются:\n\n"
    
    for holiday in holidays:
        emoji = random.choice(emojis)
        msg += f"{emoji} {holiday}\n"
        
    msg += "\n🏃‍♂️ Отличного дня и легких ног! Ждём субботу и 5 вёрст!"
    
    return msg

def send_vk_message(peer_id, message):
    url = "https://api.vk.com/method/messages.send"
    payload = {
        "access_token": VK_TOKEN,
        "peer_id": peer_id,
        "message": message,
        "random_id": random.randint(1, 2147483647),
        "v": VK_API_VERSION
    }
    
    try:
        response = requests.post(url, data=payload)
        result = response.json()
        
        if "error" in result:
            print(f"Ошибка отправки в чат {peer_id}: {result['error']['error_msg']}")
        else:
            print(f"Успешно отправлено в чат {peer_id}")
            
    except Exception as e:
        print(f"Сетевая ошибка при отправке в {peer_id}: {e}")

def main():
    if not VK_TOKEN:
        print("ОШИБКА: Токен ВКонтакте (VK_TOKEN) не найден в переменных окружения!")
        return
        
    print("Собираем праздники...")
    holidays = get_holidays()
    
    message = format_message(holidays)
    print("\nСгенерированное сообщение:\n" + message + "\n")
    
    print("Начинаем рассылку по чатам Кстово...")
    for chat_id in CHAT_IDS:
        send_vk_message(chat_id, message)
        
    print("Готово!")

if __name__ == "__main__":
    main()
