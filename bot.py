import os
import requests
import random
import sys
from datetime import datetime, timedelta, timezone

# --- НАСТРОЙКИ (Secrets) ---
VK_TOKEN = os.getenv('VK_TOKEN')
VK_CHAT_IDS = os.getenv('VK_CHAT_IDS', '')
FORCE_WEATHER = os.getenv('FORCE_WEATHER', 'false').lower() == 'true'

# Координаты парка Юбилейный (Кстово)
LAT = 56.1611
LON = 44.2182

def get_moscow_now():
    """Возвращает текущее время в Москве (UTC+3)"""
    return datetime.now(timezone(timedelta(hours=3)))

def get_weather():
    """Получает прогноз погоды через Open-Meteo API именно на 09:00 субботы"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Индекс 9 соответствует 09:00 утра
        temp = data['hourly']['temperature_2m'][9]
        prob = data['hourly']['precipitation_probability'][9]
        code = data['hourly']['weathercode'][9]

        weather_map = {
            0: "Ясно ☀️", 1: "Преимущественно ясно 🌤", 2: "Переменная облачность ⛅", 3: "Пасмурно ☁️",
            45: "Туман 🌫️", 51: "Морось 🌧️", 61: "Небольшой дождь 🌦️", 63: "Дождь ☔",
            71: "Небольшой снег ❄️", 73: "Снегопад 🌨️", 80: "Ливневый дождь ⛈️"
        }
        status = weather_map.get(code, "Облачно ☁️")

        return (
            f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n"
            f"🌡 Температура: {temp}°C\n"
            f"☁ На улице: {status}\n"
            f"☔ Вероятность осадков: {prob}%\n\n"
            f"Одевайтесь по погоде и до встречи в Юбилейном! 🧡"
        )
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
        return None

def send_to_vk(peer_id, text):
    """Универсальная отправка: в чат или на стену группы"""
    if not text: return
    
    if peer_id < 0:
        # ЭТО КАНАЛ (ГРУППА) - делаем пост на стену
        url = "https://api.vk.com/method/wall.post"
        params = {
            "access_token": VK_TOKEN,
            "owner_id": peer_id,
            "message": text,
            "from_group": 1,
            "v": "5.131"
        }
    else:
        # ЭТО ЧАТ - шлем сообщение
        url = "https://api.vk.com/method/messages.send"
        params = {
            "access_token": VK_TOKEN,
            "peer_id": peer_id,
            "message": text,
            "random_id": random.randint(1, 2**31),
            "v": "5.131"
        }

    try:
        res = requests.post(url, data=params, timeout=10).json()
        if "error" in res:
            print(f"Ошибка ВК ({peer_id}): {res['error']['error_msg']}")
        else:
            print(f"Успешно отправлено: {peer_id}")
    except Exception as e:
        print(f"Ошибка сети для {peer_id}: {e}")

if __name__ == "__main__":
    if not VK_TOKEN:
        print("Ошибка: VK_TOKEN не найден!")
        sys.exit(1)

    now = get_moscow_now()
    
    # Запуск только если суббота 07:00 МСК или включен FORCE_WEATHER
    if (now.weekday() == 5 and now.hour == 7) or FORCE_WEATHER:
        print(f"Запуск рассылки... (Force: {FORCE_WEATHER})")
        weather_text = get_weather()
        
        if weather_text and VK_CHAT_IDS:
            ids = [int(i.strip()) for i in VK_CHAT_IDS.split(',') if i.strip()]
            for chat_id in ids:
                send_to_vk(chat_id, weather_text)
        else:
            print("Рассылка отменена: нет текста погоды или списка чатов.")
    else:
        print(f"Сегодня не суббота утро (сейчас {now.strftime('%A %H:%M')}). Спим.")
