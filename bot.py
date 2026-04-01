import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone

# --- КОНФИГ ИЗ ГИТХАБА ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001

# Координаты Кстово
LAT, LON = 56.1611, 44.2182

# Ручные флаги из GitHub Actions
MANUAL = {
    "weather": os.getenv('MANUAL_WEATHER') == 'true',
    "birthdays": os.getenv('MANUAL_BIRTHDAYS') == 'true',
    "reminders": os.getenv('MANUAL_REMINDERS') == 'true',
    "report": os.getenv('MANUAL_REPORT') == 'true',
    "debug": os.getenv('MANUAL_DEBUG') == 'true'
}

try:
    CHAT_IDS = [int(i.strip()) for i in CHAT_IDS_RAW.split(',') if i.strip()]
except:
    CHAT_IDS = []

def get_moscow_now():
    return datetime.now(timezone(timedelta(hours=3)))

def send_vk(peer_id, text):
    if not text: return
    # Если ID < 0 — это стена группы (Канал), если > 0 — это чат
    method = "wall.post" if int(peer_id) < 0 else "messages.send"
    url = f"https://api.vk.com/method/{method}"
    
    params = {"access_token": VK_TOKEN, "message": text, "v": "5.131"}
    if method == "wall.post":
        params["owner_id"] = peer_id
        params["from_group"] = 1
    else:
        params["peer_id"] = peer_id
        params["random_id"] = random.randint(1, 999999)
    
    r = requests.post(url, data=params).json()
    if "error" in r:
        print(f"!!! Ошибка при отправке в {peer_id}: {r['error']['error_msg']}")
    else:
        print(f"Успешно отправлено в {peer_id}")

# 1. ДИАГНОСТИКА ID (Чтобы ты увидел реальные ID чатов)
def debug_all_ids():
    print("\n=== ДИАГНОСТИКА ДИАЛОГОВ БОТА ===")
    url = "https://api.vk.com/method/messages.getConversations"
    params = {"access_token": VK_TOKEN, "count": 20, "v": "5.131"}
    res = requests.get(url, params=params).json()
    
    if "response" in res:
        for item in res['response']['items']:
            peer = item['conversation']['peer']
            title = "Личка"
            if peer['type'] == 'chat':
                title = item['conversation']['chat_settings']['title']
            print(f"Название: {title} | ID: {peer['id']}")
    else:
        print(f"Ошибка получения списка: {res}")

# 2. ПОГОДА
def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    try:
        r = requests.get(url, timeout=10).json()
        temp = r['hourly']['temperature_2m'][9]
        status = {0:"Ясно ☀️", 1:"Ясно 🌤", 2:"Облачно ⛅", 3:"Пасмурно ☁️"}.get(r['hourly']['weathercode'][9], "Облачно")
        return f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n🌡 Температура: {temp}°C\n☁ На улице: {status}\n☔ Осадки: {r['hourly']['precipitation_probability'][9]}%\n\nОдевайтесь по погоде! 🧡"
    except: return "Ошибка получения погоды"

# 3. ДНИ РОЖДЕНИЯ
def check_birthdays():
    now = get_moscow_now()
    today_str = now.strftime("%d.%m")
    try:
        res = requests.get("https://api.vk.com/method/groups.getMembers", params={
            "group_id": VK_GROUP_ID, "fields": "bdate", "access_token": VK_TOKEN, "v": "5.131"
        }).json()
        members = res.get('response', {}).get('items', [])
        celebrants = []
        for m in members:
            bdate = m.get('bdate', '')
            if not bdate or len(bdate.split('.')) < 2: continue
            if f"{int(bdate.split('.')[0]):02d}.{int(bdate.split('.')[1]):02d}" == today_str:
                celebrants.append(f"[id{m['id']}|{m['first_name']} {m['last_name']}]")
        if celebrants:
            send_vk(FLUD_CHAT_ID, f"🥳 <b>С ДНЁМ РОЖДЕНИЯ!</b> 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉🧡")
        else: print("Именинников сегодня нет.")
    except Exception as e: print(f"Ошибка ДР: {e}")

# 4. НАПОМИНАЛКИ
def send_reminders(force_day=None):
    now = get_moscow_now()
    day = force_day or now.strftime("%A").lower()
    
    reminders = {
        "sunday": "📹 Воскресенье: Пора выложить видео организатора! 🎬",
        "tuesday": "🙋‍♂️ Вторник: Время для поста-зазыва волонтеров! 🧡",
        "thursday": "👋 Напоминание о волонтерстве!\n\nЗаписывайтесь через приложение: vk.com/app54498352 📝\n\n📸 Фото: (ссылка)\n📖 Инструкции: (ссылка)\n📍 Карта: (ссылка)\n📜 Правила: (ссылка)\n\n📱 Приложение 5 вёрст:\n🤖 [Android] — Скоро в RuStore!"
    }
    if day in reminders:
        target = ORGS_CHAT_ID if day != "thursday" else FLUD_CHAT_ID
        send_vk(target, reminders[day])

# 5. ОТЧЕТ (23:00)
def send_daily_report():
    try:
        g = requests.get("https://api.vk.com/method/groups.getById", params={"group_id": VK_GROUP_ID, "fields": "members_count", "access_token": VK_TOKEN, "v": "5.131"}).json()
        count = g['response'][0]['members_count']
        send_vk(ORGS_CHAT_ID, f"📊 Итоги дня:\n👥 Всего участников в группе: {count}")
    except: pass

if __name__ == "__main__":
    if not VK_TOKEN: sys.exit(1)
    now = get_moscow_now()

    # --- ЛОГИКА РУЧНОГО ЗАПУСКА ---
    if any(MANUAL.values()):
        print(">>> ЗАПУЩЕН РУЧНОЙ РЕЖИМ <<<")
        if MANUAL["debug"]: debug_all_ids()
        if MANUAL["weather"]: 
            w = get_weather()
            for c in CHAT_IDS: send_vk(c, w)
        if MANUAL["birthdays"]: check_birthdays()
        if MANUAL["reminders"]: send_reminders(force_day="thursday") # Тестим четверг
        if MANUAL["report"]: send_daily_report()
    
    # --- ЛОГИКА АВТОМАТИКИ (ПО ЧАСАМ) ---
    else:
        # Погода (Суббота 07:00)
        if now.weekday() == 5 and now.hour == 7:
            w = get_weather()
            for c in CHAT_IDS: send_vk(c, w)
        
        # Напоминалки (10:00)
        if now.hour == 10: send_reminders()

        # Дни рождения (09:00)
        if now.hour == 9: check_birthdays()

        # Отчет (23:00)
        if now.hour == 23: send_daily_report()
