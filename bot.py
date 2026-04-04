import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# --- КОНФИГ ---
VK_TOKEN = os.getenv('VK_TOKEN')
CHAT_IDS_RAW = os.getenv('VK_CHAT_IDS', '')
VK_GROUP_ID = 231094435
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
CHANNEL_ID = -231155212 
EVENT_ID = 10079

NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")

LOG_RESULTS = "last_results_sent.txt"
LAT, LON = 56.1611, 44.2182

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
        else: print(f">>> Отправлено в {peer_id}")
    except: pass

def login_nrms():
    try:
        r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", json={"username": NRMS_USER, "password": NRMS_PASS}, timeout=10)
        return r.json().get("result", {}).get("token")
    except: return None

def get_vk_album(date_str):
    """Ищет ссылку на альбом в ВК по дате"""
    try:
        p = {"owner_id": -VK_GROUP_ID, "access_token": VK_TOKEN, "v": "5.131"}
        resp = requests.get("https://api.vk.com/method/photos.getAlbums", params=p).json()
        albums = resp.get("response", {}).get("items", [])
        day_month = date_str[:5].replace('.', '') # 0404
        for a in albums:
            if day_month in re.sub(r'\D', '', a.get('title', '')):
                return f"https://vk.com/album-{VK_GROUP_ID}_{a['id']}"
    except: pass
    return f"https://vk.com/albums-{VK_GROUP_ID}"

def get_latest_results(is_manual=False):
    now = get_moscow_now()
    offset = (now.weekday() - 5) % 7
    last_sat = (now - timedelta(days=offset)).strftime("%d.%m.%Y")
    
    if not is_manual and os.path.exists(LOG_RESULTS):
        with open(LOG_RESULTS, "r") as f:
            if f.read().strip() == last_sat: return None

    url = f"https://5verst.ru/kstovoyubileyniy/results/{last_sat}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return None
        
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select("table.sortable tbody tr")
        if not rows: return None

        # --- ПАРСИНГ УЧАСТНИКОВ ---
        finishers_count = 0
        newcomers = []
        pbs = []
        club10 = []
        club25 = []
        near10 = []
        
        for row in rows:
            cells = row.find_all("td")
            if not cells or not cells[0].text.strip().isdigit(): continue
            
            finishers_count += 1
            name = cells[1].text.strip()
            total_runs = int(cells[6].text.strip()) if len(cells) > 6 else 0
            is_pb = "ЛР" in row.text or "PB" in row.text

            if total_runs == 1: newcomers.append(name)
            if is_pb: pbs.append(name)
            if total_runs == 10: club10.append(name)
            if total_runs == 25: club25.append(name)
            if total_runs == 9: near10.append(name)

        # --- ПОЛУЧЕНИЕ ВОЛОНТЕРОВ ЧЕРЕЗ API ---
        token = login_nrms()
        vols_list = []
        if token:
            v_res = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", 
                                 json={"event_id": EVENT_ID, "event_date": last_sat},
                                 headers={"Authorization": f"Bearer {token}"}).json()
            vols_data = v_res.get("result", {}).get("volunteer_list", [])
            for v in vols_data:
                vols_list.append(f"⭐ {v['full_name']} — {v['role_name']}")

        # --- СБОРКА СООБЩЕНИЯ ---
        start_num_match = re.search(r'#(\d+)', soup.find('h1').text)
        start_num = start_num_match.group(1) if start_num_match else "??"

        msg = f"🌳 {last_sat} состоялся {start_num}-й старт!\n"
        msg += f"Приняло участие {finishers_count} финишеров и {len(vols_list)} волонтеров.\n\n"
        msg += f"📊 Общая таблица результатов на сайте:\n{url}\n\n"

        if newcomers:
            msg += "🆕 Новые участники:\n" + "\n".join(newcomers) + "\nЖдём вас снова! ✨\n\n"
        
        if pbs:
            msg += "🚀 Личные рекорды установили:\n" + "\n".join(pbs) + "\nПоздравляем! 🎉\n\n"

        if club10: msg += "🏅 Вступили в Клуб 10:\n" + "\n".join(club10) + "\n\n"
        if club25: msg += "🏆 Вступили в Клуб 25:\n" + "\n".join(club25) + "\n\n"
        if near10: msg += "👣 В шаге от Клуба 10:\n" + "\n".join(near10) + "\n\n"

        if vols_list:
            msg += "🧡 Герои нашего старта — наши волонтеры:\n" + "\n".join(vols_list) + "\n\n"

        msg += f"📸 Фотографии в альбоме:\n{get_vk_album(last_sat)}\n\n"
        msg += "5 вёрст | Кстово | 5verst.ru"

        if not is_manual:
            with open(LOG_RESULTS, "w") as f: f.write(last_sat)
        return msg
    except Exception as e:
        print(f"Ошибка отчета: {e}")
        return None

def check_birthdays():
    now = get_moscow_now()
    today_str = now.strftime("%d.%m")
    try:
        res = requests.get("https://api.vk.com/method/groups.getMembers", params={"group_id": VK_GROUP_ID, "fields": "bdate", "access_token": VK_TOKEN, "v": "5.131"}).json()
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
            send_vk(FLUD_CHAT_ID, f"🥳 С ДНЁМ РОЖДЕНИЯ! 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉🧡")
        if now.day == 1 and monthly:
            send_vk(FLUD_CHAT_ID, f"🎂 Именинники месяца:\n\n" + "\n".join(sorted(monthly)))
    except: pass

def send_reminders():
    now = get_moscow_now()
    day = now.weekday()
    if now.hour == 10:
        if day == 6: send_vk(ORGS_CHAT_ID, "📹 Воскресенье: Пора выложить видео организатора в ВК! 🎬")
        if day == 1: send_vk(ORGS_CHAT_ID, "🙋‍♂️ Вторник: Время для поста-зазыва волонтеров! 🧡")
        if day == 3: send_vk(ORGS_CHAT_ID, "✅ Четверг: Постим о готовности старта!")
    if now.hour == 19 and day == 3:
        msg = ("👋 Напоминание о волонтерстве!\n\nДрузья, не забудьте записаться на старт: vk.com/app54498352 📝\n\n"
               "📸 Фото: https://vk.com/albums-231094435\n📖 Инструкции: https://vk.com/topic-231094435_53026364\n"
               "📍 Карта: https://vk.com/topic-231094435_53026365\n\n📱 [Android] — (ссылка в RuStore)")
        send_vk(FLUD_CHAT_ID, msg)

if __name__ == "__main__":
    if not VK_TOKEN: sys.exit(1)
    now = get_moscow_now()
    if any(MANUAL.values()):
        if MANUAL["debug"]:
            res = get_latest_results(is_manual=True)
            if res: send_vk(FLUD_CHAT_ID, res)
        if MANUAL["weather"]: send_vk(FLUD_CHAT_ID, "🌦 Прогноз погоды...")
        if MANUAL["report"]:
            res = requests.get("https://api.vk.com/method/groups.getById", params={"group_id": VK_GROUP_ID, "fields": "members_count", "access_token": VK_TOKEN, "v": "5.131"}).json()
            send_vk(ORGS_CHAT_ID, f"📊 Участников: {res['response'][0]['members_count']}")
    else:
        if now.weekday() == 5 and now.hour == 7:
            # Тут вставь свою функцию погоды
            pass
        if now.weekday() == 5 and now.hour in [12, 13, 14]:
            res = get_latest_results()
            if res: send_vk(FLUD_CHAT_ID, res)
        if now.hour == 9: check_birthdays()
        if now.hour in [10, 19, 20]: send_reminders()
