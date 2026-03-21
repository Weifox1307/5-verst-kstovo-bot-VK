import os, requests, datetime
from datetime import timedelta

# Данные из Secrets
NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")
SHEET_URL = os.getenv("SHEET_CSV_URL")
EVENT_ID = 10079 # ТВОЙ ID КСТОВО

def get_target_date():
    now = datetime.datetime.now()
    # Если сегодня суббота и время > 11 утра, пишем на следующую неделю
    days_ahead = 5 - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.hour >= 11):
        days_ahead += 7
    return (now + timedelta(days=days_ahead)).strftime("%d.%m.%Y")

def get_token():
    r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", 
                      json={"username": NRMS_USER, "password": NRMS_PASS})
    return r.json()['result']['token']

def run_sync():
    target_date = get_target_date()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Читаем таблицу
    import pandas as pd
    df = pd.read_csv(SHEET_URL)
    new_data = df[df['status'] == 'new']
    
    if new_data.empty: return print("Нет новых записей")

    # 2. Получаем текущий список с сайта, чтобы не удалить тех, кто уже там
    r_curr = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", 
                          json={"event_id": EVENT_ID, "event_date": target_date}, headers=headers)
    
    volunteers = []
    if r_curr.status_code == 200:
        existing = r_curr.json().get('result', {}).get('volunteer_list', [])
        volunteers = [{"verst_id": v['verst_id'], "role_id": v['role_id']} for v in existing]

    # 3. Добавляем новых
    for _, row in new_data.iterrows():
        vid = int(row['verst_id'])
        rid = int(row['role_id'])
        if not any(v['verst_id'] == vid and v['role_id'] == rid for v in volunteers):
            volunteers.append({"verst_id": vid, "role_id": rid})

    # 4. Сохраняем в NRMS
    payload = {
        "event_id": EVENT_ID,
        "date": target_date,
        "upload_status_id": 1,
        "volunteers": volunteers
    }
    res = requests.post("https://nrms.5verst.ru/api/v1/volunteer/event/save", json=payload, headers=headers)
    print(f"Результат NRMS: {res.status_code}")

if __name__ == "__main__":
    run_sync()
