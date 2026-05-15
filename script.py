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
    # Ищем ближайшую субботу
    days_ahead = 5 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_sat = now + datetime.timedelta(days=days_ahead)
    return next_sat.strftime("%d.%m.%Y")

def parse_5verst():
    url = f"https://5verst.ru/{LOCATION_ID}/results/latest/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        session = requests.Session()
        res = session.get(url, headers=headers, timeout=30)
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

        # 1. ПАРСИМ ВОЛОНТЕРОВ
        # Ищем всех волонтеров в блоке под таблицей
        vol_items = soup.select(".results-volunteers__item")
        for item in vol_items:
            v_text = item.get_text(strip=True).replace(" - ", " — ")
            data["volunteers"].append(v_text)
            if "Организатор" in v_text:
                name = v_text.split("—")[0].strip()
                data["organizers"].append(name)

        # 2. ПАРСИМ ТАБЛИЦУ (Более надежный способ)
        table = soup.find("table", class_="results-table")
        if not table:
            # Попробуем найти любую таблицу если класс не совпал
            table = soup.find("table")

        if table:
            # Определяем индексы колонок по заголовкам
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            
            idx_name = 1
            idx_total = 7
            idx_loc = 8
            idx_pb = 9
            
            # Пытаемся динамически найти индексы если они съехали
            for i, h in enumerate(headers):
                if "Всего" in h: idx_total = i
                if "локал" in h: idx_loc = i
                if "ЛР" in h: idx_pb = i

            rows = table.find_all("tr")[1:] # Пропускаем шапку
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5: continue
                
                name = cols[idx_name].get_text(strip=True)
                # Убираем лишние слова из имени если они там есть (например ЛР)
                name = name.split('\n')[0].strip()
                
                total_runs = cols[idx_total].get_text(strip=True)
                loc_runs = cols[idx_loc].get_text(strip=True)
                pb_status = cols[idx_pb].get_text(strip=True)
                
                if total_runs == "1":
                    data["new_total"].append(name)
                elif loc_runs == "1":
                    data["new_location"].append(name)
                
                if "ЛР" in pb_status:
                    data["pbs"].append(name)
                
                if total_runs in ["10", "25", "50", "100"]:
                    data["clubs"].append(f"{name} ({total_runs} старт!)")

        return data
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

if __name__ == "__main__":
    results = parse_5verst()
    next_sat_date = get_next_saturday()

    if not results:
        exit("Не удалось спарсить сайт.")

    # Собираем сообщение по твоему шаблону
    msg = []
    
    if results['organizers']:
        # Убираем дубли в оргах и красиво пишем
        orgs_unique = list(dict.fromkeys(results['organizers']))
        msg.append(f"🔥 Организаторы: {' и '.join(orgs_unique)}")
    
    msg.append(f"\nОбщая таблица с результатами на сайте 👇")
    msg.append(f"5verst.ru/{LOCATION_ID}/results/latest/\n")

    if results['new_total']:
        msg.append(f"🏃‍♂️ Новые участники:\n" + "\n".join(results['new_total']) + "\n")
    
    if results['new_location']:
        msg.append(f"🏃‍♂️ Впервые пробежали «5 вёрст Кстово Юбилейный»:\n" + "\n".join(results['new_location']) + "\n")

    if results['pbs']:
        msg.append(f"🥇 Личные рекорды установили:\n" + "\n".join(results['pbs']) + "\nПоздравляем 🎉\n")

    if results['clubs']:
        msg.append(f"🎖 Переход в новые клубы:\n" + "\n".join(results['clubs']) + "\n")

    msg.append(f"📸 Фотографии можно посмотреть в альбомах группы ВК.\n")

    if results['volunteers']:
        msg.append(f"🍃 Ну и конечно герои нашего старта - наши волонтеры:\n")
        msg.append("\n".join(results['volunteers']))

    msg.append(f"\n━━━━━━━━━━━━━━")
    msg.append(f"📅 СЛЕДУЮЩИЙ СТАРТ: {next_sat_date}")
    msg.append(f"⏰ Время сбора: 08:40")
    msg.append(f"Ждём вас снова! 🙌")

    final_text = "\n".join(msg)
    
    # Отправка
    url_vk = "https://api.vk.com/method/messages.send"
    params = {
        "peer_id": os.getenv("PEER_ID"),
        "message": final_text,
        "random_id": random.getrandbits(31),
        "access_token": os.getenv("VK_TOKEN"),
        "v": "5.131"
    }
    
    print(final_text) # Для логов GitHub
    requests.post(url_vk, params=params)
