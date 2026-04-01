import os, requests, random, sys, json
from datetime import datetime, timedelta, timezone

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435 

# ОТЛАДКА: Печатаем длину строки, чтобы понять, видит ли GitHub секрет
if not CHAT_IDS_RAW:
    print("!!! КРИТИЧЕСКАЯ ОШИБКА: Секрет VK_CHAT_IDS пуст или не найден!")
else:
    print(f"DEBUG: Получена строка секретов длиной {len(CHAT_IDS_RAW)} символов.")

try:
    CHAT_IDS = [int(i.strip()) for i in CHAT_IDS_RAW.split(',') if i.strip()]
    print(f"DEBUG: Успешно распознано ID чатов: {CHAT_IDS}")
except Exception as e:
    print(f"Ошибка парсинга секретов: {e}")
    CHAT_IDS = []

LAT, LON = 56.1611, 44.2182

def get_moscow_now():
    return datetime.now(timezone(timedelta(hours=3)))

def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        temp = data['hourly']['temperature_2m'][9]
        prob = data['hourly']['precipitation_probability'][9]
        code = data['hourly']['weathercode'][9]
        weather_map = {0: "Ясно ☀️", 1: "Ясно 🌤", 2: "Облачно ⛅", 3: "Пасмурно ☁️", 45: "Туман 🌫️", 51: "Морось 🌧️", 61: "Дождь 🌦️", 63: "Дождь ☔", 71: "Снег ❄️", 73: "Снегопад 🌨️", 80: "Ливень ⛈️"}
        status = weather_map.get(code, "Облачно ☁️")
        return f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n🌡 Температура: {temp}°C\n☁ На улице: {status}\n☔ Вероятность осадков: {prob}%\n\nОдевайтесь по погоде и до встречи в Юбилейном! 🧡"
    except: return None

def update_vk_widget():
    """Обновляет текстовый виджет в группе с таймером"""
    if not VK_TOKEN: return
    now = get_moscow_now()
    days_ahead = (5 - now.weekday() + 7) % 7
    if days_ahead == 0 and now.hour >= 9: days_ahead = 7
    
    next_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    diff = next_start - now
    
    days, hours = diff.days, diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    time_text = f"{days} дн. {hours} час." if days > 0 else f"{hours} час. {minutes} мин."

    widget_data = {
        "title": "До следующего старта:",
        "text": f"⏳ Осталось: {time_text}\n\nЖдем тебя в субботу в 08:40 в парке Юбилейный! 🌳",
        "descr": "Место встречи: центр парка Юбилейный"
    }

    url = "https://api.vk.com/method/appWidgets.update"
    payload = {
        "access_token": VK_TOKEN,
        "type": "text",
        "code": f"return {json.dumps(widget_data, ensure_ascii=False)};",
        "v": "5.131"
    }
    
    try:
        r = requests.post(url, data=payload).json()
        if "error" in r: print(f"Widget Error: {r['error']['error_msg']}")
        else: print("Виджет таймера успешно обновлен!")
    except Exception as e: print(f"Widget Network Error: {e}")

def send_vk_message(peer_id, text):
    params = {"access_token": VK_TOKEN, "peer_id": peer_id, "message": text, "random_id": random.randint(1, 2**31), "v": "5.131"}
    try: requests.post("https://api.vk.com/method/messages.send", data=params, timeout=10)
    except: pass

if __name__ == "__main__":
    if not VK_TOKEN:
        print("Ошибка: VK_TOKEN не найден!")
        sys.exit(1)
    
    # 1. ОБНОВЛЯЕМ ВИДЖЕТ (каждый час по расписанию)
    update_vk_widget()
    
    # 2. ШЛЕМ ПОГОДУ (только если суббота и 7 утра)
    now = get_moscow_now()
    if now.weekday() == 5 and now.hour == 7:
        if not CHAT_IDS:
            print("Ошибка: Список чатов пуст, погода не отправлена.")
        else:
            weather_text = get_weather()
            if weather_text:
                for chat in CHAT_IDS: send_vk_message(chat, weather_text)
