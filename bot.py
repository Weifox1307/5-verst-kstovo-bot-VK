import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone

# --- КОНФИГ ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
CHANNEL_ID = -231155212 

LOG_RESULTS = "last_results_sent.txt"
LAT, LON = 56.1611, 44.2182

# Ручные флаги
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
    if not text: return
    url = "https://api.vk.com/method/messages.send"
    params = {"access_token": VK_TOKEN, "peer_id": peer_id, "message": text, "random_id": random.randint(1, 999999), "v": "5.131"}
    try:
        r = requests.post(url, data=params).json()
        if "error" in r: print(f"!!! Ошибка ВК ({peer_id}): {r['error']['error_msg']}")
        else: print(f">>> Сообщение отправлено в {peer_id}")
    except: print(f"!!! Ошибка сети при отправке в {peer_id}")

def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    try:
        r = requests.get(url).json()
        temp = r['hourly']['temperature_2m'][9]
        status = {0:"Ясно ☀️", 1:"Ясно 🌤", 2:"Облачно ⛅", 3:"Пасмурно ☁️"}.get(r['hourly']['weathercode'][9], "Облачно")
        return f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n🌡 Температура: {temp}°C\n☁ На улице: {status}\n☔ Осадки: {r['hourly']['precipitation_probability'][9]}%\n\nОдевайтесь по погоде! 🧡"
    except: return None

def get_latest_results(is_manual=False):
    now = get_moscow_now()
    # Находим дату последней субботы
    offset = (now.weekday() - 5) % 7
    last_sat = (now - timedelta(days=offset)).strftime("%d.%m.%Y")
    
    print(f"Проверка результатов за субботу: {last_sat}")
    
    if not is_manual and os.path.exists(LOG_RESULTS):
        with open(LOG_RESULTS, "r") as f:
            if f.read().strip() == last_sat:
                print("Результаты за эту дату уже отправлялись ранее.")
                return None

    url = f"https://5verst.ru/kstovoyubileyniy/results/{last_sat}/"
    print(f"Запрос к сайту: {url}")
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15)
        if r.status_code != 200:
            print(f"Сайт вернул код {r.status_code}. Возможно, страница еще не создана.")
            return None
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Считаем строки в таблице результатов
        rows = soup.select("table.sortable tbody tr")
        finishers = 0
        for row in rows:
            cells = row.find_all("td")
            if cells and cells[0].text.strip().isdigit():
                finishers += 1
        
        print(f"Найдено финишеров в протоколе: {finishers}")

        if finishers > 0:
            msg = (f"🌳 <b>Результаты старта {last_sat}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n\n"
                   f"🏁 Финишировало: <b>{finishers}</b> чел.\n\n"
                   f"📊 Полный протокол: {url}\n"
                   f"🧡 Спасибо всем участникам и волонтерам!")
            
            if not is_manual:
                with open(LOG_RESULTS, "w") as f: f.write(last_sat)
            return msg
        else:
            print("Таблица пуста. Протокол еще не опубликован.")
            return None
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return None

def check_birthdays():
    now = get_moscow_now()
    today_str = now.strftime("%d.%m")
    print(f"Проверка ДР на {today_str}...")
    try:
        res = requests.get("https://api.vk.com/method/groups.getMembers", params={"group_id": VK_GROUP_ID, "fields": "bdate", "access_token": VK_TOKEN, "v": "5.131"}).json()
        members = res.get('response', {}).get('items', [])
        celebrants = []
        for m in members:
            bdate = m.get('bdate', '')
            if not bdate or len(bdate.split('.')) < 2: continue
            if f"{int(bdate.split('.')[0]):02d}.{int(bdate.split('.')[1]):02d}" == today_str:
                celebrants.append(f"[id{m['id']}|{m['first_name']} {m['last_name']}]")
        if celebrants:
            send_vk(FLUD_CHAT_ID, f"🥳 <b>С ДНЁМ РОЖДЕНИЯ!</b> 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉🧡")
        else: print("Именинников нет.")
    except: print("Ошибка запроса ДР.")

def send_reminders():
    now = get_moscow_now()
    day = now.weekday()
    print(f"Проверка напоминалок. День: {day}, Час: {now.hour}")
    if now.hour == 10:
        if day == 6: send_vk(ORGS_CHAT_ID, "📹 Воскресенье: Пора выложить видео организатора в ВК! 🎬")
        if day == 1: send_vk(ORGS_CHAT_ID, "🙋‍♂️ Вторник: Время для поста-зазыва волонтеров! 🧡")
        if day == 3: send_vk(ORGS_CHAT_ID, "✅ Четверг: Постим о готовности старта!")
    if now.hour == 19 and day == 3:
        send_vk(FLUD_CHAT_ID, "👋 Напоминание о волонтерстве! Записывайтесь: vk.com/app54498352 📝")

def send_daily_report():
    print("Отправка отчета по группе...")
    try:
        res = requests.get("https://api.vk.com/method/groups.getById", params={"group_id": VK_GROUP_ID, "fields": "members_count", "access_token": VK_TOKEN, "v": "5.131"}).json()
        count = res['response'][0]['members_count']
        send_vk(ORGS_CHAT_ID, f"📊 Итоги дня:\n👥 Всего участников в группе: {count}")
    except: print("Ошибка отчета.")

if __name__ == "__main__":
    if not VK_TOKEN: 
        print("Ошибка: VK_TOKEN не найден!")
        sys.exit(1)
    
    now = get_moscow_now()
    print(f"--- ЗАПУСК (МСК {now.strftime('%H:%M')}) ---")

    if any(MANUAL.values()):
        print(">>> РУЧНОЙ РЕЖИМ <<<")
        if MANUAL["debug"]:
            msg = get_latest_results(is_manual=True)
            if msg: 
                send_vk(FLUD_CHAT_ID, msg)
                send_vk(CHANNEL_ID, msg)
            else: print("Результаты не найдены или не готовы.")
        if MANUAL["weather"]: 
            w = get_weather()
            for c in [FLUD_CHAT_ID, ORGS_CHAT_ID]: send_vk(c, w)
        if MANUAL["report"]: send_daily_report()
        if MANUAL["birthdays"]: check_birthdays()
    else:
        # Автоматика
        if now.weekday() == 5 and now.hour == 7:
            w = get_weather()
            for c in [FLUD_CHAT_ID, ORGS_CHAT_ID]: send_vk(c, w)
        
        if now.weekday() == 5 and now.hour in [12, 13, 14]:
            msg = get_latest_results()
            if msg: 
                send_vk(FLUD_CHAT_ID, msg)
                send_vk(CHANNEL_ID, msg)

        if now.hour == 9: check_birthdays()
        if now.hour == 10 or now.hour == 19: send_reminders()
        if now.hour == 23: send_daily_report()
