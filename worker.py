import os, requests, pandas as pd, vk_api, json

# Данные из GitHub Secrets
NRMS_USER = os.getenv("NRMS_USERNAME") # Твой A790217375
NRMS_PASS = os.getenv("NRMS_PASSWORD")
EVENT_ID = 10079 # Парк Станкозавода
SHEET_URL = os.getenv("SHEET_CSV_URL") # Ссылка на CSV таблицы

def get_nrms_token():
    r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", 
                      json={"username": NRMS_USER, "password": NRMS_PASS})
    return r.json()['result']['token']

def sync():
    # 1. Загружаем заявки из таблицы
    try:
        df = pd.read_csv(SHEET_URL)
        new_volunteers = df[df['status'] == 'new']
    except: return print("Таблица пуста")

    if new_volunteers.empty:
        return print("Новых заявок нет")

    token = get_nrms_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Получаем дату ближайшего старта (автоматически)
    # Для простоты можно захардкодить или вытянуть из /calendar/event/list
    current_date = "28.03.2026" 

    # 3. Получаем ТЕКУЩИЙ список волонтеров из NRMS, чтобы не затереть существующих
    r_current = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", 
                             json={"event_id": EVENT_ID, "event_date": current_date}, headers=headers)
    
    # Формируем список волонтеров для отправки (старые + новые)
    vol_list = []
    # Добавляем тех, кто уже в системе
    for v in r_current.json()['result']['volunteer_list']:
        vol_list.append({"verst_id": v['verst_id'], "role_id": v['role_id']})
    
    # Добавляем новых из таблицы
    for _, row in new_volunteers.iterrows():
        vol_list.append({"verst_id": int(row['verst_id']), "role_id": int(row['role_id'])})

    # 4. СОХРАНЯЕМ ОБНОВЛЕННЫЙ СПИСОК
    payload = {
        "event_id": EVENT_ID,
        "date": current_date,
        "upload_status_id": 1,
        "volunteers": vol_list
    }
    
    res = requests.post("https://nrms.5verst.ru/api/v1/volunteer/event/save", 
                       json=payload, headers=headers)
    
    if res.status_code == 200:
        print(f"Успешно синхронизировано {len(new_volunteers)} новых волонтеров!")
        # В идеале тут надо пометить строки в Google Таблице как 'done' 
        # Но для первой версии достаточно, что мы их добавили.

if __name__ == "__main__":
    sync()
