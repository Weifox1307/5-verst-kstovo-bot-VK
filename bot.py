import os
import requests
import random
import sys

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')
# Твои ID чатов (Peer ID)
CHAT_IDS = [
    2000000001,  # Флудилка
    2000000002,  # Набор волонтеров
    2000000263,  # Чат организаторов
    -231155212   # Канал сообщества
]

# Координаты парка Юбилейный (Кстово)
LAT = 56.1611
LON = 44.2182

def get_weather():
    """Получает прогноз погоды через Open-Meteo API"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Индекс 9 соответствует 09:00 утра
        temp = data['hourly']['temperature_2m'][9]
        prob = data['hourly']['precipitation_probability'][9]
        code = data['hourly']['weathercode'][9]

        # Расшифровка кодов погоды WMO
        weather_map = {
            0: "Ясно ☀️",
            1: "Преимущественно ясно 🌤",
            2: "Переменная облачность ⛅",
            3: "Пасмурно ☁️",
            45: "Туман 🌫️",
            51: "Морось 🌧️",
            61: "Небольшой дождь 🌦️",
            63: "Дождь ☔",
            71: "Небольшой снег ❄️",
            73: "Снегопад 🌨️",
            80: "Ливневый дождь ⛈️"
        }
        status = weather_map.get(code, "Облачно ☁️")

        msg = (
            f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n"
            f"🌡 Температура: {temp}°C\n"
            f"☁ На улице: {status}\n"
            f"☔ Вероятность осадков: {prob}%\n\n"
            f"Одевайтесь по погоде и до встречи в Юбилейном! 🧡"
        )
        return msg
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
        return None

def send_vk_message(peer_id, text):
    """Отправляет сообщение в ВК"""
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
            print(f"Успешно отправлено в чат {peer_id}")
    except Exception as e:
        print(f"Ошибка сети: {e}")

if __name__ == "__main__":
    if not VK_TOKEN:
        print("Ошибка: VK_TOKEN не найден!")
        sys.exit(1)

    weather_text = get_weather()
    if weather_text:
        for chat in CHAT_IDS:
            send_vk_message(chat, weather_text)
    else:
        print("Не удалось сформировать прогноз.")
