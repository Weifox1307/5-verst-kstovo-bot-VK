import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone

# --- КОНФИГ ИЗ ГИТХАБА (Secrets) ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435

# ID ЧАТОВ
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
CHANNEL_ID = -231155212 

# Координаты Кстово
LAT, LON = 56.1611, 44.2182

# Ручные флаги для тестов через GitHub Actions
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
    """Универсальная отправка сообщений"""
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

def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,precipitation_probability,weathercode&timezone=Europe%2FMoscow&forecast_days=1"
    try:
        r = requests.get(url).json()
        temp = r['hourly']['temperature_2m'][9]
        status = {0:"Ясно ☀️", 1:"Ясно 🌤", 2:"Облачно ⛅", 3:"Пасмурно ☁️"}.get(r['hourly']['weathercode'][9], "Облачно")
        return f"🌳 ПОГОДА НА СТАРТЕ В 09:00:\n\n🌡 Температура: {temp}°C\n☁ На улице: {status}\n☔ Осадки: {r['hourly']['precipitation_probability'][9]}%\n\nОдевайтесь по погоде! 🧡"
    except: return None

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

def send_reminders():
    now = get_moscow_now()
    day = now.weekday() # 0-Mon, 1-Tue, 2-Wed, 3-Thu, 4-Fri, 5-Sat, 6-Sun
    hour = now.hour

    # --- 10:00 УТРА: Служебные задачи оргам ---
    if hour == 10:
        if day == 6: # Воскресенье
            send_vk(ORGS_CHAT_ID, "📹 Воскресенье: Пора записать и выложить видео организатора в ВК! 🎬")
        elif day == 1: # Вторник
            send_vk(ORGS_CHAT_ID, "🙋‍♂️ Вторник: Время для поста-зазыва волонтеров и объявления тематики! 🧡")
        elif day == 3: # Четверг
            send_vk(ORGS_CHAT_ID, "✅ Четверг: Постим о готовности старта (разметка, инвентарь, команда)!")

    # --- 19:00 ВЕЧЕРА: Призыв волонтеров (Четверг) ---
    if hour == 19 and day == 3:
        vol_text = (
            "👋 Напоминание о волонтерстве!\n\n"
            "Друзья, не забудьте заглянуть в наше приложение Вк для записи: vk.com/app54498352 📝\n\n"
            "Полезные разделы нашего парка:\n"
            "📸 Фото и видео: https://vk.com/albums-231094435\n"
            "📍 Как нас найти: https://vk.com/5verstkstovoyubileyniy?w=address-231094435%3FcloseBack%3D1\n"
            "📜 Правила: https://vk.com/@5verstkstovoyubileyniy-pravila-5-verst\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Приложение 5 вёрст:\n"
            "🤖 [Android] — Скоро в RuStore!\n\n"
            "Ваша помощь делает 5 вёрст возможными! ❤️"
        )
        send_vk(FLUD_CHAT_ID, vol_text)

    # --- 20:00 ВЕЧЕРА: Итоги субботы ---
    if hour == 20 and day == 5:
        send_vk(ORGS_CHAT_ID, "📊 Суббота вечер: Не забудьте подвести итоги недели! ✅")

def get_results():
    now = get_moscow_now()
    date_str = (now - timedelta(days=(now.weekday() - 5) % 7)).strftime("%d.%m.%Y")
    url = f"https://5verst.ru/kstovoyubileyniy/results/{date_str}/"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            finishers = len(soup.select("table.sortable tbody tr"))
            msg = f"🌳 Результаты старта {date_str}\n━━━━━━━━━━━━━━━━━━━━\n\n🏁 Финишировало: {finishers} чел.\n\n📊 Протокол: {url}"
            send_vk(FLUD_CHAT_ID, msg)
            send_vk(CHANNEL_ID, msg)
    except: pass

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
        print(">>> ЗАПУСК В РУЧНОМ РЕЖИМЕ <<<")
        if os.getenv('MANUAL_DEBUG') == 'true':
            res = requests.get("https://api.vk.com/method/messages.getConversations", params={"access_token": VK_TOKEN, "v": "5.131"}).json()
            print(json.dumps(res, indent=2, ensure_ascii=False))
        if MANUAL["weather"]: 
            w = get_weather()
            for c in [FLUD_CHAT_ID, ORGS_CHAT_ID, CHANNEL_ID]: send_vk(c, w)
        if MANUAL["birthdays"]: check_birthdays()
        if MANUAL["reminders"]: 
            # Для теста шлем всё сразу
            send_vk(FLUD_CHAT_ID, "🔔 ТЕСТ: Напоминание о волонтерстве (обычно по четв в 19:00)")
            send_vk(ORGS_CHAT_ID, "🔔 ТЕСТ: Напоминалка оргам")
        if MANUAL["report"]: send_daily_report()
    else:
        # АВТОМАТИКА
        if now.weekday() == 5 and now.hour == 7: # Погода суббота 07:00
            w = get_weather()
            for c in [FLUD_CHAT_ID, ORGS_CHAT_ID, CHANNEL_ID]: send_vk(c, w)
        if now.weekday() == 5 and now.hour == 12: get_results() # Результаты суббота 12:00
        if now.hour == 9: check_birthdays() # ДР ежедневно 09:00
        if now.hour == 23: send_daily_report() # Отчет ежедневно 23:00
        
        # Напоминалки (бот сам выберет нужную по времени внутри функции)
        send_reminders()
