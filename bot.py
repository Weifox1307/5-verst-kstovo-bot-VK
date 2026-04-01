import os, requests, random, sys, json
from datetime import datetime, timedelta, timezone

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
# Если нужно принудительно отправить погоду для теста
FORCE_WEATHER = os.getenv('FORCE_WEATHER', 'false').lower() == 'true'

try:
    CHAT_IDS = [int(i.strip()) for i in CHAT_IDS_RAW.split(',') if i.strip()]
    print(f"DEBUG: Распознано чатов: {CHAT_IDS}")
except:
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
    
    # Считаем дни до субботы (5)
    days_ahead = (5 - now.weekday() + 7) % 7
    if days_ahead == 0 and now.hour >= 9: days_ahead = 7
    
    next_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    diff = next_start - now
    
    days, hours = diff.days, diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    if days > 0:
        time_text = f"{days} дн. {hours} час."
    else:
        time_text = f"{hours} час. {minutes} мин."

    # Дизайн виджета "Текст"
    widget_data = {
        "title": "До следующего старта 5 вёрст:",
        "text": f"⏳ {time_text}\n\nЖдём вас в субботу к 08:45 в парке Юбилейный! 🏃‍♂️🧡",
        "descr": "Место встречи: центр парка"
    }

    url = "https://api.vk.com/method/appWidgets.update"
    payload = {
        "access_token": VK_TOKEN,
        "type": "text",
        "code": f"return {json.dumps(widget_data, ensure_ascii=False)};",
        "v": "5.131"
    }
    
    r = requests.post(url, data=payload).json()
    if "error" in r: 
        print(f"Widget Error: {r['error']['error_msg']}")
        if r['error']['error_code'] == 15:
            print("СОВЕТ: Убедитесь, что в группе установлено приложение 'Виджеты' и токен имеет права 'manage'.")
    else: 
        print("Виджет таймера успешно обновлен!")

def send_vk_message(peer_id, text):
    params = {"access_token": VK_TOKEN, "peer_id": peer_id, "message": text, "random_id": random.randint(1, 2**31), "v": "5.131"}
    try: 
        res = requests.post("https://api.vk.com/method/messages.send", data=params, timeout=10).json()
        if "error" in res: print(f"Msg Error ({peer_id}): {res['error']['error_msg']}")
        else: print(f"Погода отправлена в чат {peer_id}")
    except: pass

if __name__ == "__main__":
    if not VK_TOKEN:
        print("Ошибка: VK_TOKEN не найден!")
        sys.exit(1)
    
    # 1. Всегда обновляем виджет
    update_vk_widget()
    
    # 2. Шлем погоду если суббота 7 утра ИЛИ если запуск ручной (FORCE)
    now = get_moscow_now()
    if (now.weekday() == 5 and now.hour == 7) or FORCE_WEATHER:
        if not CHAT_IDS:
            print("Ошибка: Список чатов пуст, погода не отправлена.")
        else:
            weather_text = get_weather()
            if weather_text:
                for chat in CHAT_IDS: send_vk_message(chat, weather_text)
            else:
                print("Не удалось получить данные о погоде.")
