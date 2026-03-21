import os, requests, pandas as pd, datetime
from datetime import timedelta

# Настройки из GitHub Secrets
NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")
EVENT_ID = 10061 
SHEET_URL = os.getenv("SHEET_CSV_URL")

def get_next_saturday():
    """Находит дату ближайшей субботы в формате ДД.ММ.ГГГГ"""
    now = datetime.datetime.now()
    # 5 — это суббота (Monday=0, Saturday=5)
    days_ahead = 5 - now.weekday()
    if days_ahead < 0: # Если уже воскресенье
        days_ahead += 7
    next_sat = now + timedelta(days=days_ahead)
    return next_sat.strftime("%d.%m.%Y")

def get_nrms_token():
    r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", 
                      json={"username": NRMS_USER, "password": NRMS_PASS})
    return r.json()['result']['token']

def sync():
    # 1. Загружаем заявки из таблицы
    try:
        df = pd.read_csv(SHEET_URL)
        # Очищаем пустые строки и берем только статус 'new'
        new_volunteers = df[df['status'] == 'new'].dropna(subset=['verst_id'])
    except Exception as e:
        return print(f"Ошибка чтения таблицы: {e}")

    if new_volunteers.empty:
        return print("Новых заявок нет")

    token = get_nrms_token()
    headers = {"Authorization": f"Bearer {token}"}
    current_date = get_next_saturday()
    print(f"Работаем с датой: {current_date}")

    # 2. Получаем текущий список из NRMS
    r_current = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", 
                             json={"event_id": EVENT_ID, "event_date": current_date}, headers=headers)
    
    vol_list = []
    # Сохраняем тех, кто уже записан на сайте
    if 'volunteer_list' in r_current.json().get('result', {}):
        for v in r_current.json()['result']['volunteer_list']:
            vol_list.append({"verst_id": v['verst_id'], "role_id": v['role_id']})
    
    # 3. Добавляем новых из Google Таблицы
    for _, row in new_volunteers.iterrows():
        vid = int(float(row['verst_id'])) # защита от формата float в CSV
        rid = int(row['role_id'])
        # Проверка, чтобы не дублировать
        if not any(v['verst_id'] == vid and v['role_id'] == rid for v in vol_list):
            vol_list.append({"verst_id": vid, "role_id": rid})

    # 4. Сохраняем всё в NRMS
    payload = {
        "event_id": EVENT_ID,
        "date": current_date,
        "upload_status_id": 1,
        "volunteers": vol_list
    }
    
    res = requests.post("https://nrms.5verst.ru/api/v1/volunteer/event/save", 
                       json=payload, headers=headers)
    
    if res.status_code == 200:
        print(f"Успешно! В списке теперь {len(vol_list)} волонтеров.")
    else:
        print(f"Ошибка сохранения: {res.text}")

if __name__ == "__main__":
    sync()
