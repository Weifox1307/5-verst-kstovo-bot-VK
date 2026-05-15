import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os
import random

# --- НАСТРОЙКИ ---
LOCATION_ID = "kstovoyubileyniy"
VK_TOKEN = os.getenv("VK_TOKEN")
PEER_ID = os.getenv("PEER_ID")

def get_next_saturday():
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(moscow_tz)
    days_ahead = 5 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_sat = now + datetime.timedelta(days=days_ahead)
    return next_sat.strftime("%d.%m.%Y")

def parse_5verst():
    url = f"https://5verst.ru/{LOCATION_ID}/results/latest/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        data = {
            "organizers": [],
            "new_total": [],
            "new_location": [],
            "pbs": [],
            "volunteers": [],
            "clubs": []
        }

        # 1. Парсим волонтеров (блок под таблицей)
        vol_items = soup.select(".results-volunteers__item")
        for item in vol_items:
            v_text = item.get_text(strip=True)
            data["volunteers"].append(v_text)
            if "Организатор" in v_text or "Директор" in v_text:
                data["organizers"].append(v_text.split("—")[0].strip())

        # 2. Парсим таблицу результатов
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")[1:] # Пропускаем заголовок
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5: continue
                
                name = cols[1].get_text(strip=True)
                total_runs = cols[7].get_text(strip=True) # Колонка 'Всего'
                loc_runs = cols[8].get_text(strip=True)   # Колонка 'В этой лок.'
                pb_status = cols[9].get_text(strip=True)  # Колонка 'ЛР'
                
                # Новички
                if total_runs == "1":
                    data["new_total"].append(name)
                elif loc_runs == "1":
                    data["new_location"].append(name)
                
                # Личные рекорды
                if "ЛР" in pb_status:
                    data["pbs"].append(name)
                
                # Клубы
                if total_runs in ["10", "25", "50", "100", "250"]:
                    data["clubs"].append(f"{name} ({total_runs} старт!)")

        return data
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return None

if __name__ == "__main__":
    results = parse_5verst()
    next_sat_date = get_next_saturday()

    if not results:
        print("Данные не найдены.")
        exit()

    # Сборка сообщения
    msg = []
    
    if results['organizers']:
        msg.append(f"🔥 Организаторы: {', '.join(results['organizers'])}")
    
    msg.append(f"\nРезультаты старта доступны на сайте 👇")
    msg.append(f"5verst.ru/{LOCATION_ID}/results/latest/\n")

    if results['new_total']:
        msg.append(f"🏃‍♂️ Новые участники:\n" + "\n".join(results['new_total']) + "\n")
    
    if results['new_location']:
        msg.append(f"🏃‍♂️ Впервые на нашей локации:\n" + "\n".join(results['new_location']) + "\n")

    if results['pbs']:
        msg.append(f"🥇 Личные рекорды установили:\n" + "\n".join(results['pbs']) + "\nПоздравляем! 🎉\n")

    if results['clubs']:
        msg.append(f"🎖 Переход в новые клубы:\n" + "\n".join(results['clubs']) + "\n")

    if results['volunteers']:
        msg.append(f"🍃 Герои нашего старта — волонтеры:\n" + "\n".join(results['volunteers']))

    msg.append(f"\n━━━━━━━━━━━━━━")
    msg.append(f"📅 СЛЕДУЮЩИЙ СТАРТ: {next_sat_date}")
    msg.append(f"⏰ Время сбора: 08:40")
    msg.append(f"Ждём вас снова! 🙌")

    final_text = "\n".join(msg)
    
    # Отправка в ВК
    url_vk = "https://api.vk.com/method/messages.send"
    params = {
        "peer_id": PEER_ID,
        "message": final_text,
        "random_id": random.getrandbits(31),
        "access_token": VK_TOKEN,
        "v": "5.131"
    }
    
    print(final_text)
    r = requests.post(url_vk, params=params).json()
    print("Ответ ВК:", r)
