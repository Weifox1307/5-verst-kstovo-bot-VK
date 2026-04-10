import os, requests, random, sys, json, re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# --- КОНФИГ ---
VK_TOKEN = os.getenv('VK_TOKEN')
VK_GROUP_ID = 231094435
ORGS_CHAT_ID = 2000000263
FLUD_CHAT_ID = 2000000001
EVENT_ID = 10079

NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")

LOG_RESULTS = "last_results_sent.txt"

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
    if not text or not VK_TOKEN: return
    url = "https://api.vk.com/method/messages.send"
    params = {"access_token": VK_TOKEN, "peer_id": peer_id, "message": text, "random_id": random.randint(1, 999999), "v": "5.131"}
    try:
        r = requests.post(url, data=params, timeout=10)
        print(f">>> Сообщение отправлено в {peer_id}")
    except Exception as e:
        print(f"!!! Ошибка отправки ВК: {e}")

def login_nrms():
    if not NRMS_USER or not NRMS_PASS: return None
    try:
        user = NRMS_USER if NRMS_USER.upper().startswith('A') else f"A{NRMS_USER}"
        r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", json={"username": user, "password": NRMS_PASS}, timeout=15)
        return r.json().get("result", {}).get("token")
    except: return None

def get_vk_album(date_str):
    try:
        p = {"owner_id": -VK_GROUP_ID, "access_token": VK_TOKEN, "v": "5.131"}
        resp = requests.get("https://api.vk.com/method/photos.getAlbums", params=p, timeout=10).json()
        albums = resp.get("response", {}).get("items", [])
        day_month = date_str[:5].replace('.', '')
        for a in albums:
            if day_month in re.sub(r'\D', '', a.get('title', '')):
                return f"https://vk.com/album-{VK_GROUP_ID}_{a['id']}"
    except: pass
    return f"https://vk.com/albums-{VK_GROUP_ID}"

def get_latest_results(is_manual=False):
    try:
        now = get_moscow_now()
        offset = (now.weekday() - 5) % 7
        last_sat = (now - timedelta(days=offset)).strftime("%d.%m.%Y")
        
        if not is_manual and os.path.exists(LOG_RESULTS):
            with open(LOG_RESULTS, "r") as f:
                if f.read().strip() == last_sat: return None

        url = f"https://5verst.ru/kstovoyubileyniy/results/{last_sat}/"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code != 200: return None
        
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select("table.sortable tbody tr")
        if not rows: return None

        finishers_count = 0
        newcomers, pbs, club10, club25, near10 = [], [], [], [], []
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 7 or not cells[0].text.strip().isdigit(): continue
            finishers_count += 1
            name = cells[1].text.strip()
            total_runs = int(cells[6].text.strip())
            if total_runs == 1: newcomers.append(name)
            if "ЛР" in row.text or "PB" in row.text: pbs.append(name)
            if total_runs == 10: club10.append(name)
            if total_runs == 25: club25.append(name)
            if total_runs == 9: near10.append(name)

        token = login_nrms()
        vols_list = []
        if token:
            v_res = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", 
                                 json={"event_id": EVENT_ID, "event_date": last_sat},
                                 headers={"Authorization": f"Bearer {token}"}, timeout=15).json()
            for v in v_res.get("result", {}).get("volunteer_list", []):
                vols_list.append(f"⭐ {v['full_name']} — {v['role_name']}")

        title = soup.find('h1').text if soup.find('h1') else ""
        num = re.search(r'#(\d+)', title).group(1) if re.search(r'#(\d+)', title) else "??"

        msg = f"🌳 {last_sat} состоялся {num}-й старт!\nПриняло участие {finishers_count} финишеров и {len(vols_list)} волонтеров.\n\n📊 Результаты: {url}\n\n"
        if newcomers: msg += "🆕 Новички:\n" + "\n".join(newcomers) + "\n\n"
        if pbs: msg += "🚀 Личные рекорды:\n" + "\n".join(pbs) + "\n\n"
        if club10: msg += "🏅 Клуб 10: " + ", ".join(club10) + "\n"
        if club25: msg += "🏆 Клуб 25: " + ", ".join(club25) + "\n"
        if vols_list: msg += "\n🧡 Волонтеры:\n" + "\n".join(vols_list) + "\n\n"
        msg += f"📸 Фото: {get_vk_album(last_sat)}\n\n5 вёрст | Кстово"

        if not is_manual:
            with open(LOG_RESULTS, "w") as f: f.write(last_sat)
        return msg
    except Exception as e:
        print(f"Ошибка парсинга результатов: {e}")
        return None

def check_birthdays():
    try:
        now = get_moscow_now()
        today = now.strftime("%d.%m")
        res = requests.get("https://api.vk.com/method/groups.getMembers", params={"group_id": VK_GROUP_ID, "fields": "bdate", "access_token": VK_TOKEN, "v": "5.131"}, timeout=15).json()
        celebrants = []
        for m in res.get('response', {}).get('items', []):
            bd = m.get('bdate', '')
            if bd and bd.count('.') >= 1:
                if f"{int(bd.split('.')[0]):02d}.{int(bd.split('.')[1]):02d}" == today:
                    celebrants.append(f"[id{m['id']}|{m['first_name']} {m['last_name']}]")
        if celebrants:
            send_vk(FLUD_CHAT_ID, f"🥳 С ДНЁМ РОЖДЕНИЯ! 🎂\n\nСегодня праздник у: {', '.join(celebrants)}! 🎉🧡")
    except: pass

def send_reminders():
    now = get_moscow_now()
    day = now.weekday()
    if now.hour == 10:
        if day == 6: send_vk(ORGS_CHAT_ID, "📹 Воскресенье: Видео организатора!")
        if day == 1: send_vk(ORGS_CHAT_ID, "🙋‍♂️ Вторник: Пост-зазыв волонтеров!")
        if day == 3: send_vk(ORGS_CHAT_ID, "✅ Четверг: Пост о готовности!")
    if now.hour == 19 and day == 3:
        send_vk(FLUD_CHAT_ID, "👋 Друзья, не забудьте записаться на старт: vk.com/app54498352 📝")

if __name__ == "__main__":
    try:
        now = get_moscow_now()
        if any(MANUAL.values()):
            if MANUAL["debug"]:
                res = get_latest_results(is_manual=True)
                if res: send_vk(FLUD_CHAT_ID, res)
        else:
            if now.weekday() == 5 and now.hour == 13:
                res = get_latest_results()
                if res: send_vk(FLUD_CHAT_ID, res)
            if now.hour == 9: check_birthdays()
            if now.hour in [10, 19]: send_reminders()
    except Exception as e:
        print(f"Глобальная ошибка скрипта: {e}")
    
    # Всегда выходим с кодом 0, чтобы GitHub не отменял деплой страницы
    sys.exit(0)
