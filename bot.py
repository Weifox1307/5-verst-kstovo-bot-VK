import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone

# --- КОНФИГ ИЗ ГИТХАБА (Secrets) ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435
# ID ЧАТОВ (Берем жестко из твоих ссылок)
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
CHANNEL_ID = -231155212 # Канал сообщества (отрицательный ID)

# Координаты Кстово
LAT, LON = 56.1611, 44.2182

# Ручные флаги для тестов
MANUAL = {
    "weather": os.getenv('MANUAL_WEATHER') == 'true',
    "birthdays": os.getenv('MANUAL_BIRTHDAYS') == 'true',
    "reminders": os.getenv('MANUAL_REMINDERS') == 'true',
    "report": os.getenv('MANUAL_REPORT') == 'true',
    "debug": os.getenv('MANUAL_DEBUG') == 'true'
}

def get_moscow_now():
    return datetime.now(timezone(timedelta(hours=3)))

def send_vk(peer_id, text):
    """Универсальная отправка сообщений (в чаты, личку и каналы мессенджера)"""
    if not text: return
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "peer_id": peer_id,
        "message": text,
        "random_id": random.randint(1, 999999),
        "v": "5.131"
    }
    r = requests.post(url, data=params).json()
    if "error" in r:
        print(f"!!! Ошибка отправки в {peer_id}: {r['error']['error_msg']} (Код: {r['error']['error_code']})")
    else:
        print(f"Успешно отправлено в {peer_id}")

# 1. ДИАГНОСТИКА
def debug_all_ids():
    print("\n=== ДИАГНОСТИКА ДИАЛОГОВ ===")
    res = requests.get("https://api.vk.com/method/messages.getConversations", params={"access_token": VK_TOKEN, "v": "5.131"}).json()
    print(json.dumps(res, indent=2, ensure_ascii=False))

# 2. ПОГОДА
def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    try:
        r = requests.get(url).json()
        temp = r['hourly']['temperature_2m'][9]
        status = {0:"Ясно ☀️", 1:"Ясно 🌤", 2:"Облачно ⛅", 3:"Пасмурно ☁️"}.get(r['hourly']['weathercode'][9], "Облачно")
        return f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n🌡 Температура: {temp}°C\n☁ На улице: {status}\n☔ Осадки: {r['hourly']['precipitation_probability'][9]}%\n\nОдевайтесь по погоде! 🧡"
    except: return None

# 3. ДНИ РОЖДЕНИЯ (ТОЛЬКО ИЗ ВК)
def check_birthdays():
    now = get_moscow_now()
    today_str = now.strftime("%d.%m")
    try:
        res = requests.get("https://api.vk.com/method/groups.getMembers", params={
            "group_id": VK_GROUP_ID, "fields": "bdate", "access_token": VK_TOKEN, "v": "5.131"
        }).json()
        members = res.get('response', {}).get('items', [])
        celebrants = []
        monthly = []
        for m in members:
            bdate = m.get('bdate', '')
            if not bdate or len(bdate.split('.')) < 2: continue
            day_month = f"{int(bdate.split('.')[0]):02d}.{int(bdate.split('.')[1]):02d}"
            mention = f"[id{m['id']}|{m['first_name']} {m['last_name']}]"
            if day_month == today_str: celebrants.append(mention)
            if int(bdate.split('.')[1]) == now.month: monthly.append(f"• {day_month} — {mention}")
        
        if celebrants:
            send_vk(FLUD_CHAT_ID, f"🥳 С ДНЁМ РОЖДЕНИЯ! 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉\nЖелаем легких ног и бодрого настроения! 🧡")
        
        if now.day == 1 and monthly:
            send_vk(FLUD_CHAT_ID, f"🎂 Именинники месяца:\n\n" + "\n".join(sorted(monthly)))
    except: pass

# 4. НАПОМИНАЛКИ
def send_reminders(force=False):
    now = get_moscow_now()
    day = now.strftime("%A").lower()
    
    # Служебные напоминалки (Оргам)
    org_reminders = {
        "sunday": "📹 Воскресенье: Пора записать и выложить видео организатора в ВК! 🎬",
        "tuesday": "🙋‍♂️ Вторник: Время для поста-зазыва волонтеров! 🧡",
        "saturday": "📊 Суббота вечер: Не забудьте подвести итоги недели! ✅"
    }
    
    # Четверговая напоминалка (Волонтерам во флудилку)
    if day == "thursday" or force:
        vol_text = (
            "👋 Напоминание о волонтерстве!\n\n"
            "Друзья, не забудьте заглянуть в наше приложение Вк для записи: vk.com/app54498352 📝\n\n"
            "Полезные ссылки:\n"
            "📸 Фото и видео: https://vk.com/albums-231094435\n"
            "📖 Инструкции: (ссылка)\n"
            "📍 Как нас найти: (ссылка)\n"
            "📜 Правила: (ссылка)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Приложение 5 вёрст:\n"
            "🤖 [Android] — RuStore (ссылка)\n\n"
            "Ваша помощь делает 5 вёрст возможными! ❤️"
        )
        send_vk(FLUD_CHAT_ID, vol_text)
        send_vk(ORGS_CHAT_ID, "✅ Четверг: Постим о готовности старта (разметка, инвентарь, команда)!")
    
    if day in org_reminders:
        send_vk(ORGS_CHAT_ID, org_reminders[day])

# 5. РЕЗУЛЬТАТЫ (Парсинг сайта)
def get_results():
    now = get_moscow_now()
    offset = (now.weekday() - 5) % 7
    last_sat = (now - timedelta(days=offset)).strftime("%d.%m.%Y")
    url = f"https://5verst.ru/kstovoyubileyniy/results/{last_sat}/"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            finishers = len(soup.select("table.sortable tbody tr"))
            msg = f"🌳 Результаты старта {last_sat}\n━━━━━━━━━━━━━━━━━━━━\n\n🏁 Финишировало: {finishers} чел.\n\n📊 Протокол: {url}"
            send_vk(FLUD_CHAT_ID, msg)
            send_vk(CHANNEL_ID, msg)
    except: pass

# 6. ОТЧЕТ ПО УЧАСТНИКАМ
def send_daily_report():
    try:
        res = requests.get("https://api.vk.com/method/groups.getById", params={"group_id": VK_GROUP_ID, "fields": "members_count", "access_token": VK_TOKEN, "v": "5.131"}).json()
        count = res['response'][0]['members_count']
        send_vk(ORGS_CHAT_ID, f"📊 Итоги дня:\n👥 Всего участников в группе: {count}")
    except: pass

if __name__ == "__main__":
    if not VK_TOKEN: sys.exit(1)
    now = get_moscow_now()

    if any(MANUAL.values()):
        if MANUAL["debug"]: debug_all_ids()
        if MANUAL["weather"]: 
            w = get_weather()
            for c in [FLUD_CHAT_ID, ORGS_CHAT_ID, CHANNEL_ID]: send_vk(c, w)
        if MANUAL["birthdays"]: check_birthdays()
        if MANUAL["reminders"]: send_reminders(force=True)
        if MANUAL["report"]: send_daily_report()
    else:
        # Автоматика по расписанию
        if now.weekday() == 5 and now.hour == 7: # Погода
            w = get_weather()
            for c in [FLUD_CHAT_ID, ORGS_CHAT_ID, CHANNEL_ID]: send_vk(c, w)
        if now.weekday() == 5 and now.hour == 12: get_results() # Результаты
        if now.hour == 9: check_birthdays() # ДР
        if now.hour == 10: send_reminders() # Напоминалки
        if now.hour == 23: send_daily_report() # Отчет в 23:00
