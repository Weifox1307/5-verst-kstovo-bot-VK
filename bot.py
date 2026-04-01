import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
EVENT_ID = 10079
LAT, LON = 56.1611, 44.2182

try:
    CHAT_IDS = [int(i.strip()) for i in CHAT_IDS_RAW.split(',') if i.strip()]
except:
    CHAT_IDS = []

def get_moscow_now():
    return datetime.now(timezone(timedelta(hours=3)))

# 1. ПОГОДА
def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        temp = data['hourly']['temperature_2m'][9]
        prob = data['hourly']['precipitation_probability'][9]
        status = {0:"Ясно ☀️", 1:"Ясно 🌤", 2:"Облачно ⛅", 3:"Пасмурно ☁️"}.get(data['hourly']['weathercode'][9], "Облачно")
        return f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n🌡 Температура: {temp}°C\n☁ На улице: {status}\n☔ Осадки: {prob}%\n\nОдевайтесь по погоде! 🧡"
    except: return None

# 2. РЕЗУЛЬТАТЫ СТАРТА
def get_latest_results():
    now = get_moscow_now()
    offset = (now.weekday() - 5) % 7
    last_sat = now - timedelta(days=offset)
    date_str = last_sat.strftime("%d.%m.%Y")
    url = f"https://5verst.ru/kstovoyubileyniy/results/{date_str}/"
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200: return None
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        finishers = len(soup.select("table.sortable tbody tr"))
        
        msg = f"🌳 <b>Результаты старта {date_str}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🏁 Финишировало: <b>{finishers}</b> чел.\n\n📊 Полный протокол: {url}\n🧡 Спасибо всем участникам и волонтерам!"
        return msg
    except: return None

# 3. ДНИ РОЖДЕНИЯ (ТОЛЬКО ИЗ ВК)
def check_birthdays():
    now = get_moscow_now()
    today_str = now.strftime("%d.%m")
    
    try:
        # Получаем всех участников (до 1000 чел)
        res = requests.get("https://api.vk.com/method/groups.getMembers", params={
            "group_id": VK_GROUP_ID, "fields": "bdate", "access_token": VK_TOKEN, "v": "5.131"
        }).json()
        
        members = res.get('response', {}).get('items', [])
        celebrants = []
        monthly_list = []

        for m in members:
            bdate = m.get('bdate', '')
            if not bdate: continue
            
            parts = bdate.split('.')
            if len(parts) < 2: continue
            
            m_day = f"{int(parts[0]):02d}.{int(parts[1]):02d}"
            name = f"{m['first_name']} {m['last_name']}"
            mention = f"[id{m['id']}|{name}]"

            if m_day == today_str:
                celebrants.append(mention)
            
            if parts[1] == now.strftime("%m"):
                monthly_list.append(f"• {m_day} — {mention}")

        # Поздравление сегодня
        if celebrants:
            text = f"🥳 <b>С ДНЁМ РОЖДЕНИЯ!</b> 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉\nЖелаем легких ног, бодрости духа и новых личных рекордов! 🧡🏃‍♂️"
            send_vk(FLUD_CHAT_ID, text)

        # Список на месяц (1-го числа)
        if now.day == 1 and monthly_list:
            text = f"🎂 <b>Именинники месяца ({now.strftime('%B')}):</b>\n\n" + "\n".join(sorted(monthly_list))
            send_vk(FLUD_CHAT_ID, text)
    except: pass

# 4. НАПОМИНАЛКИ
def send_reminders():
    now = get_moscow_now()
    day = now.strftime("%A").lower()
    
    reminders = {
        "sunday": "📹 <b>Воскресенье:</b> Пора выложить видео организатора! 🎬",
        "tuesday": "🙋‍♂️ <b>Вторник:</b> Время для поста-зазыва волонтеров! 🧡",
        "thursday": "👋 <b>Напоминание о волонтерстве!</b>\n\nДрузья, не забудьте записаться на старт через наше приложение: vk.com/app54498352 📝\n\nПолезные ссылки:\n📸 Фото: (ссылка)\n📖 Инструкции: (ссылка)\n📍 Как нас найти: (ссылка)\n📜 Правила: (ссылка)\n\n━━━━━━━━━━━━━━━━━━━━\n📱 Приложение 5 вёрст:\n🤖 [Android] — (RuStore)\n\nВаша помощь делает 5 вёрст возможными! ❤️"
    }
    
    if day in reminders:
        send_vk(ORGS_CHAT_ID if day != "thursday" else FLUD_CHAT_ID, reminders[day])

# 5. ОТЧЕТ ПО ИНВАЙТАМ (23:00)
def send_daily_report():
    # Т.к. ВК не дает инфу кто пригласил в ГРУППУ, шлем просто статистику роста
    try:
        g = requests.get("https://api.vk.com/method/groups.getById", params={"group_id": VK_GROUP_ID, "fields": "members_count", "access_token": VK_TOKEN, "v": "5.131"}).json()
        count = g['response'][0]['members_count']
        send_vk(ORGS_CHAT_ID, f"📊 <b>Итоги дня:</b>\n\n👥 Всего участников в группе: <b>{count}</b>")
    except: pass

def send_vk(peer_id, text):
    if not text: return
    url = "https://api.vk.com/method/wall.post" if int(peer_id) < 0 else "https://api.vk.com/method/messages.send"
    params = {"access_token": VK_TOKEN, "message": text, "v": "5.131"}
    if int(peer_id) < 0: params["owner_id"] = peer_id; params["from_group"] = 1
    else: params["peer_id"] = peer_id; params["random_id"] = random.randint(1, 999999)
    requests.post(url, data=params)

if __name__ == "__main__":
    now = get_moscow_now()
    
    # Погода (Суббота 07:00)
    if now.weekday() == 5 and now.hour == 7:
        weather = get_weather()
        for c in CHAT_IDS: send_vk(c, weather)
    
    # Результаты (Суббота 12:00 - когда протокол обычно готов)
    if now.weekday() == 5 and now.hour == 12:
        res_msg = get_latest_results()
        if res_msg: send_vk(FLUD_CHAT_ID, res_msg)

    # Напоминалки (10:00 утра)
    if now.hour == 10:
        send_reminders()

    # Дни рождения (09:00 утра)
    if now.hour == 9:
        check_birthdays()

    # Отчет (23:00)
    if now.hour == 23:
        send_daily_report()
