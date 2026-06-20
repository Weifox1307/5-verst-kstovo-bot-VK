import os
import requests
import random
import pytz
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
LOCATION_ID = "kstovoyubileyniy"
EVENT_ID = 10079
PEER_ID = os.getenv("PEER_ID")
VK_TOKEN = os.getenv("VK_TOKEN")
NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")

# Список юбилейных чисел (клубы)
MILESTONES = [10, 25, 50, 100, 250, 500]

def get_detailed_results(date_str):
    # Форматируем дату для URL (из 2026-06-20 в 20.06.2026)
    url_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    url = f"https://5verst.ru/{LOCATION_ID}/results/{url_date}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    res = {
        "count": 0, 
        "url": url, 
        "new_total": [], 
        "new_location": [], 
        "pbs": [],
        "run_milestones": []
    }
    
    try:
        print(f"Запрос к результатам: {url}")
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"Сайт вернул статус: {r.status_code}")
            return res
        
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.select_one(".results-table") or soup.select_one("table.sortable") or soup.find("table")
        
        if table:
            rows = table.find_all('tr')[1:] # Пропускаем заголовок
            res["count"] = len(rows)
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 9: continue
                
                # Имя участника
                name = cols[1].get_text(strip=True).split('\n')[0]
                
                try:
                    # Чистим данные от текста и иконок, оставляем только цифры
                    total_runs_raw = cols[7].get_text(strip=True)
                    total_runs = int(re.sub(r'\D', '', total_runs_raw)) if total_runs_raw else 0
                    
                    loc_runs_raw = cols[8].get_text(strip=True)
                    loc_runs = int(re.sub(r'\D', '', loc_runs_raw)) if loc_runs_raw else 0
                    
                    pb_status = cols[9].get_text(strip=True)
                    
                    # 1. Первый старт в системе 5 вёрст
                    if total_runs == 1:
                        res["new_total"].append(name)
                    # 2. Первый старт именно в этой локации
                    elif loc_runs == 1:
                        res["new_location"].append(name)
                    
                    # 3. Проверка на юбилейный клуб (бег)
                    if total_runs in MILESTONES:
                        res["run_milestones"].append(f"{name} ({total_runs} старт)")
                        
                    # 4. Личный рекорд
                    if "ЛР" in pb_status:
                        res["pbs"].append(name)
                        
                except Exception as e:
                    continue
        else:
            print("Таблица не найдена на странице.")
            
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        
    return res

class NRMS_API:
    def __init__(self, user, pwd):
        self.base_url = "https://nrms.5verst.ru/api/v1"
        self.headers = {"Content-Type": "application/json"}
        self.user, self.pwd = (user or ""), (pwd or "")

    def login(self):
        if not self.user or not self.pwd: return False
        try:
            r = requests.post(f"{self.base_url}/auth/login", 
                             json={"username": self.user, "password": self.pwd}, timeout=10)
            token = r.json().get("result", {}).get("token")
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
                return True
        except: return False
        return False

    def get_volunteers(self, date_str):
        try:
            f_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            r = requests.post(f"{self.base_url}/event/volunteer/list", 
                             json={"event_id": EVENT_ID, "event_date": f_date}, 
                             headers=self.headers, timeout=15)
            return r.json().get("result", {}).get("volunteer_list", [])
        except: return []

def send_to_vk(message):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "peer_id": PEER_ID, "message": message,
        "random_id": random.getrandbits(31),
        "access_token": VK_TOKEN, "v": "5.131"
    }
    return requests.post(url, params=params).json()

if __name__ == "__main__":
    tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(tz)

    # Автоматический расчет последней субботы
    offset = (now.weekday() - 5) % 7
    last_sat_dt = now - timedelta(days=offset)
    
    # --- ДЛЯ ТЕСТА ПРОШЛОЙ НЕДЕЛИ (13 июня) ---
    # Раскомментируй строку ниже, если хочешь проверить за 13.06.2026
    last_sat_dt = datetime.strptime("2026-06-13", "%Y-%m-%d")
    # ------------------------------------------

    date_str = last_sat_dt.strftime("%Y-%m-%d")
    display_date = last_sat_dt.strftime("%d.%m.%Y")
    next_display_date = (last_sat_dt + timedelta(days=7)).strftime("%d.%m.%Y")

    print(f"Ищем результаты за: {display_date}")

    results = get_detailed_results(date_str)
    
    if results["count"] > 0:
        api = NRMS_API(NRMS_USER, NRMS_PASS)
        volunteers_text = ""
        vol_milestones = []
        organizers = []
        
        if api.login():
            vols_raw = api.get_volunteers(date_str)
            if vols_raw:
                v_list = []
                for v in vols_raw:
                    name = v.get("full_name")
                    role = v.get("role_name")
                    v_count = v.get("volunteering_count", 0)
                    
                    v_list.append(f"• {name} — {role}")
                    if "Организатор" in role: organizers.append(name)
                    
                    # Проверка на юбилейный клуб (волонтерство)
                    if v_count in MILESTONES:
                        vol_milestones.append(f"{name} ({v_count} раз)")
                
                volunteers_text = "\n".join(v_list)
        
        # Собираем итоговое сообщение
        msg = [
            f"🌳 5 вёрст Кстово Юбилейный",
            f"🗓 Старт от {display_date}\n━━━━━━━━━━━━━━",
            f"🏁 Финишировало участников: {results['count']}",
            f"📊 Протокол: {results['url']}\n"
        ]
        
        if organizers:
            msg.insert(2, f"🔥 Организаторы: {', '.join(set(organizers))}\n")

        # КЛУБЫ (Милестоны)
        all_milestones = results['run_milestones'] + vol_milestones
        if all_milestones:
            msg.append(f"🏆 Вступили в юбилейные клубы:\n" + "\n".join(all_milestones) + "\nГордимся вами! 👏\n")

        if results['new_total']:
            msg.append(f"🏃‍♂️ Новые участники:\n" + "\n".join(results['new_total']) + "\n")
        
        if results['new_location']:
            msg.append(f"🏃‍♂️ Впервые у нас:\n" + "\n".join(results['new_location']) + "\n")

        if results['pbs']:
            msg.append(f"🥇 Личные рекорды:\n" + "\n".join(results['pbs']) + "\nПоздравляем! 🎉\n")

        if volunteers_text:
            msg.append(f"🍃 Герои нашего старта — волонтеры:\n{volunteers_text}\n")

        msg.append(f"━━━━━━━━━━━━━━\n📅 СЛЕДУЮЩИЙ СТАРТ: {next_display_date}\n⏰ Время: 08:40\nЖдём вас! 🙌")
        
        final_msg = "\n".join(msg)
        print(final_msg)
        
        if VK_TOKEN and PEER_ID:
            send_to_vk(final_msg)
    else:
        print(f"Результаты за {display_date} пока не загружены на сайт.")
