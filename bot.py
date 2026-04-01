import os, requests, random, sys, json
from datetime import datetime, timedelta, timezone

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')
VK_CHAT_IDS = os.getenv('VK_CHAT_IDS', '')
FORCE_WEATHER = os.getenv('FORCE_WEATHER', 'false').lower() == 'true'

# Координаты и ID
LAT, LON = 56.1611, 44.2182
VK_APP_ID = "54498352" # ID твоего Mini App Кстово

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
    """Обновляет виджет в группе: Тип 'Tiles' (Плитки) - выглядит дорого и современно"""
    if not VK_TOKEN: return
    now = get_moscow_now()
    
    # Считаем время до субботы 09:00
    days_ahead = (5 - now.weekday() + 7) % 7
    if days_ahead == 0 and now.hour >= 9: days_ahead = 7
    
    next_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    diff = next_start - now
    
    d, h, m = diff.days, diff.seconds // 3600, (diff.seconds % 3600) // 60
    time_str = f"{d}д. {h}ч." if d > 0 else f"{h}ч. {m}м."

    # СТРУКТУРА ВИДЖЕТА (TILES)
    widget_data = {
        "title": "5 вёрст Парк Юбилейный • Кстово",
        "tiles": [
            {
                "title": time_str,
                "descr": "До старта",
                "url": f"https://vk.com/app{VK_APP_ID}",
                "link_target": "Успею!"
            },
            {
                "title": "09:00",
                "descr": "Каждую субботу",
                "url": "https://yandex.ru/maps/-/CDu6Y6Z-", # Ссылка на точку сбора в Юбилейном
                "link_target": "На карту"
            },
            {
                "title": "Запись",
                "descr": "Нужны волонтеры",
                "url": f"https://vk.com/app{VK_APP_ID}",
                "link_target": "Выбрать роль"
            }
        ]
    }

    url = "https://api.vk.com/method/appWidgets.update"
    payload = {
        "access_token": VK_TOKEN,
        "type": "tiles", # МЕНЯЕМ ТИП НА ПЛИТКИ
        "code": f"return {json.dumps(widget_data, ensure_ascii=False)};",
        "v": "5.131"
    }
    
    try:
        r = requests.post(url, data=payload).json()
        if "error" in r:
            print(f"Widget Error: {r['error']['error_msg']}")
        else:
            print("Премиум-виджет успешно обновлен!")
    except Exception as e:
        print(f"Widget Error: {e}")

def send_to_vk(peer_id, text):
    if not text: return
    url = "https://api.vk.com/method/wall.post" if peer_id < 0 else "https://api.vk.com/method/messages.send"
    params = {"access_token": VK_TOKEN, "v": "5.131", "message": text}
    if peer_id < 0: params["owner_id"] = peer_id
    else: params["peer_id"] = peer_id; params["random_id"] = random.randint(1, 2**31)
    
    try: requests.post(url, data=params, timeout=10)
    except: pass

if __name__ == "__main__":
    if not VK_TOKEN: sys.exit(1)
    
    update_vk_widget()
    
    now = get_moscow_now()
    if (now.weekday() == 5 and now.hour == 7) or FORCE_WEATHER:
        try:
            ids = [int(i.strip()) for i in VK_CHAT_IDS.split(',') if i.strip()]
            weather = get_weather()
            for chat in ids: send_to_vk(chat, weather)
        except: pass
