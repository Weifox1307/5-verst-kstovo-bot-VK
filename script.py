import os
import requests
import random
import pytz
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
LOCATION_ID = "kstovoyubileyniy"
EVENT_ID = 10079  # ID Кстово Юбилейный
PEER_ID = os.getenv("PEER_ID") # Твой 2000000001
VK_TOKEN = os.getenv("VK_TOKEN")
NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")

class NRMS_API:
    def __init__(self, user, pwd):
        self.base_url = "https://nrms.5verst.ru/api/v1"
        self.headers = {"Content-Type": "application/json"}
        self.user = user
        self.pwd = pwd

    def login(self):
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
            # Формат даты для API: DD.MM.YYYY
            f_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            r = requests.post(f"{self.base_url}/event/volunteer/list", 
                             json={"event_id": EVENT_ID, "event_date": f_date}, 
                             headers=self.headers, timeout=15)
            return r.json().get("result", {}).get("volunteer_list", [])
        except: return []

def get_detailed_results(date_str):
    """Парсим сайт для получения списков людей (новички, ЛР и т.д.)"""
    url_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    url = f"https://5verst.ru/{LOCATION_ID}/results/{url_date}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    res = {
        "count": 0, "url": url,
        "new_total": [], "new_location": [], "pbs": []
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return res
        
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', class_='results-table')
        if not table: table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]
            res["count"] = len(rows)
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 10: continue
                
                name = cols[1].get_text(strip=True).split('\n')[0]
                total_runs = cols[7].get_text(strip=True)
                loc_runs = cols[8].get_text(strip=True)
                pb_status = cols[9].get_text(strip=True)
                
                if total_runs == "1": res["new_total"].append(name)
                elif loc_runs == "1": res["new_location"].append(name)
                if "ЛР" in pb_status: res["pbs"].append(name)
    except: pass
    return res

def get_next_start_info():
    tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(tz)
    days_ahead = 5 - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_sat = now + timedelta(days=days_ahead)
    return next_sat.strftime("%d.%m.%Y"), "08:40"

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
    # Если ты хочешь потестить 2026 год, а на календаре 2024, 
    # мы можем просто вручную задать дату для теста:
    
    # ВАРИАНТ ДЛЯ ТЕСТА 9 МАЯ 2026:
    display_date = "09.05.2026"
    date_str = "2026-05-09"
    
    print(f"Запуск теста для даты: {display_date}")

    # 1. Получаем результаты с сайта
    results = get_detailed_results(date_str)
    if results["count"] == 0:
        print(f"Результаты за {display_date} не найдены на сайте. Проверь ссылку: {results['url']}")
        # Если не находит, попробуй за 2024 год для проверки связи:
        # date_str = "2024-05-11" 
        # display_date = "11.05.2024"
        # results = get_detailed_results(date_str)
        exit()

    # 2. Получаем волонтеров через NRMS API
    api = NRMS_API(NRMS_USER, NRMS_PASS)
    volunteers_text = ""
    organizers = []
    
    if api.login():
        vols_raw = api.get_volunteers(date_str)
        if vols_raw:
            v_list = []
            for v in vols_raw:
                name = v.get("full_name")
                role = v.get("role_name")
                v_list.append(f"• {name} — {role}")
                if "Организатор" in role: organizers.append(name)
            volunteers_text = "\n".join(v_list)
        else:
            print("API логин успешен, но список волонтеров пуст.")
    else:
        print("Ошибка логина в NRMS. Проверь логин/пароль в Secrets.")

    # 3. Собираем текст сообщения
    # Для теста следующего старта (после 9 мая это будет 16 мая)
    next_date = "16.05.2026"
    next_time = "08:40"
    
    msg = [f"🌳 5 вёрст Кстово Юбилейный"]
    msg.append(f"🗓 Старт от {display_date}\n━━━━━━━━━━━━━━")
    
    if organizers:
        msg.append(f"🔥 Организаторы: {', '.join(set(organizers))}\n")
    
    msg.append(f"🏁 Финишировало участников: {results['count']}")
    msg.append(f"📊 Протокол: {results['url']}\n")

    if results['new_total']:
        msg.append(f"🏃‍♂️ Новые участники:\n" + "\n".join(results['new_total']) + "\n")
    
    if results['new_location']:
        msg.append(f"🏃‍♂️ Впервые на нашей локации:\n" + "\n".join(results['new_location']) + "\n")

    if results['pbs']:
        msg.append(f"🥇 Личные рекорды:\n" + "\n".join(results['pbs']) + "\nПоздравляем! 🎉\n")

    if volunteers_text:
        msg.append(f"🍃 Герои нашего старта — волонтеры:\n{volunteers_text}\n")

    msg.append(f"━━━━━━━━━━━━━━")
    msg.append(f"📅 СЛЕДУЮЩИЙ СТАРТ: {next_date}")
    msg.append(f"⏰ Время сбора: {next_time}")
    msg.append(f"Ждём вас снова! 🙌")

    final_msg = "\n".join(msg)
    print(final_msg)
    
    if VK_TOKEN and PEER_ID:
        res = send_to_vk(final_msg)
        print("Ответ ВК:", res)
