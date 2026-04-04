import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone

# --- КОНФИГ ИЗ ГИТХАБА (Secrets) ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
CHANNEL_ID = -231155212 

# Файлы для хранения состояния (чтобы не дублировать сообщения)
LOG_RESULTS = "last_results_sent.txt"

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

try:
    CHAT_IDS = [int(i.strip()) for i in CHAT_IDS_RAW.split(',') if i.strip()]
except:
    CHAT_IDS = []

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
        print(f"!!! Ошибка отправки в {peer_id}: {r['error']['error_msg']}")
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
        celebrants, monthly = [], []
        for m in members:
            bdate = m.get('bdate', '')
            if not bdate or len(bdate.split('.')) < 2: continue
            dm = f"{int(bdate.split('.')[0]):02d}.{int(bdate.split('.')[1]):02d}"
            mention = f"[id{m['id']}|{m['first_name']} {m['last_name']}]"
            if dm == today_str: celebrants.append(mention)
            if int(bdate.split('.')[1]) == now.month: monthly.append(f"• {dm} — {mention}")
        
        if celebrants:
            send_vk(FLUD_CHAT_ID, f"🥳 С ДНЁМ РОЖДЕНИЯ! 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉\nЖелаем легких ног и бодрого настроения! 🧡")
        
        if now.day == 1 and monthly:
            send_vk(FLUD_CHAT_ID, f"🎂 Именинники месяца:\n\n" + "\n".join(sorted(monthly)))
    except: pass

def send_reminders():
    now = get_moscow_now()
    day = now.weekday() # 0-Mon, 1-Tue, 2-Wed, 3-Thu...
    
    # 10:00 - Служебные напоминалки оргам
    if now.hour == 10:
        if day == 6: send_vk(ORGS_CHAT_ID, "📹 Воскресенье: Пора выложить видео организатора в ВК! 🎬")
        elif day == 1: send_vk(ORGS_CHAT_ID, "🙋‍♂️ Вторник: Время для поста-зазыва волонтеров! 🧡")
        elif day == 3: send_vk(ORGS_CHAT_ID, "✅ Четверг: Постим о готовности старта!")

    # 19:00 - Призыв волонтеров (Четверг)
    if now.hour == 19 and day == 3:
        msg = (
            "👋 Напоминание о волонтерстве!\n\n"
            "Друзья, не забудьте заглянуть в наше приложение Вк для записи: vk.com/app54498352 📝\n\n"
            "Полезные разделы нашего парка:\n"
            "📸 Фото и видео: https://vk.com/albums-231094435\n"
            "📍 Как нас найти: https://vk.com/5verstkstovoyubileyniy?w=address-231094435\n"
            "📜 Правила: https://vk.com/@5verstkstovoyubileyniy-pravila-5-verst\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📱 Приложение 5 вёрст:\n"
            "🤖 [Android] — https://www.rustore.ru/catalog/app/com.example.a5verst\n\n"
            "Ваша помощь делает 5 вёрст возможными! ❤️"
        )
        send_vk(FLUD_CHAT_ID, msg)

    # 20:00 - Итоги (Суббота)
    if now.hour == 20 and day == 5:
        send_vk(ORGS_CHAT_ID, "📊 Суббота вечер: Не забудьте подвести итоги недели! ✅")

def get_results():
    now = get_moscow_now()
    offset = (now.weekday() - 5) % 7
    last_sat = (now - timedelta(days=offset)).strftime("%d.%m.%Y")
    
    # Проверяем, не отправляли ли мы уже этот результат сегодня
    if os.path.exists(LOG_RESULTS):
        with open(LOG_RESULTS, "r") as f:
            if f.read().strip() == last_sat:
                print(f"Результаты за {last_sat} уже были отправлены ранее.")
                return

    url = f"https://5verst.ru/kstovoyubileyniy/results/{last_sat}/"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            rows = soup.select("table.sortable tbody tr")
            finishers = 0
            for row in rows:
                if row.find("td") and row.find("td").text.strip().isdigit():
                    finishers += 1

            if finishers > 0:
                msg = f"🌳 Результаты старта {last_sat}\n━━━━━━━━━━━━━━━━━━━━\n\n🏁 Финишировало: {finishers} чел.\n\n📊 Протокол: {url}\n🧡 Спасибо всем участникам и волонтерам!"
                send_vk(FLUD_CHAT_ID, msg)
                send_vk(CHANNEL_ID, msg)
                
                # Записываем, что отправили
                with open(LOG_RESULTS, "w") as f:
                    f.write(last_sat)
                print(f"Результаты за {last_sat} успешно отправлены.")
            else:
                print("Протокол найден, но данных о финишерах пока нет.")
    except Exception as e:
        print(f"Ошибка парсинга результатов: {e}")

def send_daily_report():
    try:
        res = requests.get("https://api.vk.com/method/groups.getById", params={"group_id": VK_GROUP_ID, "fields": "members_count", "access_token": VK_TOKEN, "v": "5.131"}).json()
        count = res['response'][0]['members_count']
        send_vk(ORGS_CHAT_ID, f"📊 Итоги дня:\n👥 Всего участников в группе: {count}")
    except: pass

if __name__ == "__main__":
    if not VK_TOKEN: sys.exit(1)
    now = get_moscow_now()

    # РУЧНОЙ ЗАПУСК
    if any(MANUAL.values()):
        if MANUAL["weather"]: 
            w = get_weather()
            for c in CHAT_IDS: send_vk(c, w)
        if MANUAL["birthdays"]: check_birthdays()
        if MANUAL["reminders"]: send_reminders()
        if MANUAL["report"]: send_daily_report()
        if MANUAL["debug"]: get_results() # Тест результатов
    
    # АВТОМАТИКА
    else:
        # Погода (Суббота 07:00)
        if now.weekday() == 5 and now.hour == 7:
            w = get_weather()
            for c in CHAT_IDS: send_vk(c, w)
        
        # Результаты (Суббота 12:00, 13:00, 14:00 - пока не появятся)
        if now.weekday() == 5 and now.hour in [12, 13, 14]:
            get_results()

        if now.hour == 9: check_birthdays()
        if now.hour == 23: send_daily_report()
        send_reminders() # Внутри сама проверит час и день
