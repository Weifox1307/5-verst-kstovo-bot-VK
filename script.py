import requests
from bs4 import BeautifulSoup
import datetime
import random
import pytz
import os

# --- НАСТРОЙКИ ---
LOCATION_ID = "kstovoyubileyniy" 
VK_TOKEN = os.getenv("VK_TOKEN")
PEER_ID = os.getenv("PEER_ID") # Впиши 2000000260 в Secrets на GitHub

def get_next_saturday_data():
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(moscow_tz)
    
    # Считаем следующую субботу (+7 дней)
    next_sat = now + datetime.timedelta(days=7)
    
    # Генерируем время в промежутке 08:40 - 10:00
    # 8:40 = 520 мин, 10:00 = 600 мин
    random_minutes = random.randint(520, 600)
    h = random_minutes // 60
    m = random_minutes % 60
    
    start_time = f"{h:02d}:{m:02d}"
    date_str = next_sat.strftime("%d.%m.%Y")
    
    return date_str, start_time

def get_5verst_results():
    url = f"https://5verst.ru/{LOCATION_ID}/results/latest/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"Результаты уже на сайте: {url}"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем блок со статистикой
        # На сайте 5верст это обычно элементы с классом results-stats__item-value
        stats = soup.find_all(class_="results-stats__item-value")
        
        if stats and len(stats) >= 2:
            finishers = stats[0].get_text(strip=True)
            volunteers = stats[1].get_text(strip=True)
            return f"🏁 Финишировало: {finishers} участников\n🧡 Помогали: {volunteers} волонтеров"
        
        return f"Результаты загружены! См. по ссылке: {url}"
    except Exception as e:
        return f"Результаты доступны здесь: {url}"

def send_to_vk_chat(message):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "peer_id": PEER_ID,
        "message": message,
        "random_id": random.getrandbits(31),
        "access_token": VK_TOKEN,
        "v": "5.131"
    }
    r = requests.post(url, params=params)
    return r.json()

if __name__ == "__main__":
    if not VK_TOKEN or not PEER_ID:
        print("Ошибка: Проверь Secrets VK_TOKEN и PEER_ID!")
        exit(1)

    date_sat, time_sat = get_next_saturday_data()
    results = get_5verst_results()
    
    text = (
        f"🌳 5 вёрст Кстово Юбилейный\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 Результаты сегодняшнего старта:\n"
        f"{results}\n\n"
        f"📅 СЛЕДУЮЩИЙ СТАРТ: {date_sat}\n"
        f"⏰ Время сбора: {time_sat}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Ждем всех в парке! 🙌"
    )
    
    print("Отправка сообщения...")
    res = send_to_vk_chat(text)
    print("Ответ ВК:", res)
