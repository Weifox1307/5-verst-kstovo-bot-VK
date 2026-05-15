import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os
import random
import re

# --- НАСТРОЙКИ ---
LOCATION_ID = "kstovoyubileyniy"
VK_TOKEN = os.getenv("VK_TOKEN")
PEER_ID = os.getenv("PEER_ID") # Твой 2000000001

def get_next_saturday():
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(moscow_tz)
    # Если сегодня суббота (5), прибавляем 7 дней, иначе ищем ближайшую субботу
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
        
        results = {
            "organizers": [],
            "new_total": [],      # Вообще первый раз на 5 верст
            "new_location": [],   # Первый раз именно в этой локации
            "pbs": [],            # Личные рекорды
            "volunteers": [],     # Список всех волонтеров
            "clubs": []           # Переход в клубы (25, 50 и т.д.)
        }

        # 1. ПАРСИНГ ВОЛОНТЕРОВ И ОРГАНИЗАТОРОВ
        vol_items = soup.find_all("div", class_="results-volunteers__item")
        for item in vol_items:
            text = item.get_text(strip=True)
            if "—" in text:
                name, role = map(str.strip, text.split("—", 1))
                results["volunteers"].append(f"{name} — {role}")
                if "Организатор" in role:
                    results["organizers"].append(name)
            else:
                results["volunteers"].append(text)

        # 2. ПАРСИНГ ТАБЛИЦЫ РЕЗУЛЬТАТОВ
        rows = soup.find_all("tr", class_="results-table__row")
        for row in rows:
            name_tag = row.find("td", class_="results-table__user-name")
            if not name_tag: continue
            name = name_tag.get_text(strip=True)
            
            # Ищем ЛР
            if row.find("span", string=re.compile("ЛР")):
                results["pbs"].append(name)
            
            # Проверяем количество стартов (ячейки с цифрами)
            cells = row.find_all("td", class_="results-table__cell--center")
            if len(cells) >= 2:
                total_runs = cells[0].get_text(strip=True) # Всего
                loc_runs = cells[1].get_text(strip=True)   # В этой локации
                
                if total_runs == "1":
                    results["new_total"].append(name)
                elif loc_runs == "1":
                    results["new_location"].append(name)
                
                # Клубы (если число круглое)
                if total_runs in ["10", "25", "50", "100", "250"]:
                    results["clubs"].append(f"{name} ({total_runs} старт!)")

        return results
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None

def send_to_vk(message):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "peer_id": PEER_ID,
        "message": message,
        "random_id": random.getrandbits(31),
        "access_token": VK_TOKEN,
        "v": "5.131"
    }
    return requests.post(url, params=params).json()

if __name__ == "__main__":
    data = parse_5verst()
    next_date = get_next_saturday()
    
    if not data:
        print("Не удалось получить данные.")
        exit(1)

    # Формируем текст
    orgs = ", ".join(data['organizers']) if data['organizers'] else "Информация уточняется"
    newbies = "\n".join(data['new_total']) if data['new_total'] else "Новых участников не было"
    first_loc = "\n".join(data['new_location']) if data['new_location'] else "Все уже бегали у нас"
    pbs = "\n".join(data['pbs']) if data['pbs'] else "В этот раз без рекордов"
    vols = "\n".join(data['volunteers'])
    clubs = "\n".join(data['clubs'])

    message = (
        f"🔥 Организаторы: {orgs}\n\n"
        f"Бежим вместе. Помним вместе.\n"
        f"Общая таблица с результатами на сайте 👇\n"
        f"5verst.ru/{LOCATION_ID}/results/latest/\n\n"
        f"🏃‍♂️ Новые участники:\n{newbies}\n\n"
        f"🏃‍♂️ Впервые пробежали «5 вёрст Кстово Юбилейный»:\n{first_loc}\n\n"
        f"🥇 Личные рекорды установили:\n{pbs}\n"
        f"Поздравляем 🎉\n\n"
    )

    if data['clubs']:
        message += f"🎖 Вступили в клубы:\n{clubs}\n\n"

    message += (
        f"📸 Фотографии можно посмотреть в альбомах группы.\n\n"
        f"🍃 Ну и конечно герои нашего старта - наши волонтеры:\n\n{vols}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 СЛЕДУЮЩИЙ СТАРТ: {next_date}\n"
        f"⏰ Время сбора: 08:40\n"
        f"Ждём вас снова! 🙌"
    )

    print(message)
    res = send_to_vk(message)
    print("Ответ ВК:", res)
