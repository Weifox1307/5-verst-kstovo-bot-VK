import requests
from bs4 import BeautifulSoup
import datetime
import random
import pytz
import os

# --- НАСТРОЙКИ ---
# Имя локации из URL (например, 'park-gorkogo')
LOCATION_ID = "kstovoyubileyniy"  # ЗАМЕНИ НА СВОЁ
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") # ID группы (без минуса)

def get_next_saturday_data():
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(moscow_tz)
    
    # Вычисляем следующую субботу
    days_ahead = 7
    next_sat = now + datetime.timedelta(days=days_ahead)
    
    # Генерируем случайное время между 08:40 и 10:00
    # Общее количество минут от 08:40 (520 мин) до 10:00 (600 мин)
    random_minutes = random.randint(520, 600)
    h = random_minutes // 60
    m = random_minutes % 60
    
    start_time = f"{h:02d}:{m:02d}"
    date_str = next_sat.strftime("%d.%m.%Y")
    
    return date_str, start_time

def get_5verst_results():
    url = f"https://5verst.ru/{LOCATION_ID}/results/latest/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Парсим количество участников (примерная логика, зависит от верстки сайта)
        # Обычно на сайте есть заголовок или блок с цифрами
        stats = soup.find_all("div", class_="results-stats__item-value")
        if stats:
            finishers = stats[0].get_text(strip=True)
            volunteers = stats[1].get_text(strip=True) if len(stats) > 1 else "?"
            return f"Сегодня финишировало: {finishers} человек. Волонтеров: {volunteers}."
        return "Результаты уже на сайте!"
    except Exception as e:
        return f"Результаты доступны по ссылке: {url}"

def send_to_vk(message):
    url = "https://api.vk.com/method/wall.post"
    params = {
        "owner_id": f"-{GROUP_ID}",
        "message": message,
        "access_token": VK_TOKEN,
        "v": "5.131"
    }
    r = requests.post(url, params=params)
    return r.json()

if __name__ == "__main__":
    date_sat, time_sat = get_next_saturday_data()
    results = get_5verst_results()
    
    final_text = (
        f"📊 Результаты сегодняшнего старта:\n{results}\n\n"
        f"📅 Следующий старт: {date_sat}\n"
        f"⏰ Время сбора (ориентировочно): {time_sat}\n"
        f"Ждем всех!"
    )
    
    print(final_text)
    if VK_TOKEN and GROUP_ID:
        res = send_to_vk(final_text)
        print("Ответ ВК:", res)
    else:
        print("Ошибка: Нет токенов в Secrets!")
