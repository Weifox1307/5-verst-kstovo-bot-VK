import os, requests, datetime
import pandas as pd
from datetime import timedelta, timezone

# --- НАСТРОЙКИ КСТОВО ---
NRMS_USER = os.getenv("NRMS_USERNAME")
NRMS_PASS = os.getenv("NRMS_PASSWORD")
SHEET_URL = os.getenv("SHEET_CSV_URL")
EVENT_ID = 10079 

def get_moscow_now():
    return datetime.datetime.now(timezone(timedelta(hours=3)))

def get_target_date():
    now = get_moscow_now()
    days_ahead = (5 - now.weekday() + 7) % 7
    if days_ahead == 0 and now.hour >= 11:
        days_ahead = 7
    target = now + timedelta(days=days_ahead)
    return target.strftime("%d.%m.%Y")

def get_sync_boundary():
    now = get_moscow_now()
    days_since_sat = (now.weekday() - 5) % 7
    last_sat = now - timedelta(days=days_since_sat)
    boundary = last_sat.replace(hour=11, minute=0, second=0, microsecond=0)
    if now.weekday() == 5 and now.hour < 11:
        boundary -= timedelta(days=7)
    return boundary

def get_token():
    r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", json={"username": NRMS_USER, "password": NRMS_PASS})
    return r.json()['result']['token']

def run_sync():
    target_date = get_target_date()
    boundary_time = get_sync_boundary()
    print(f"--- СИНХРОНИЗАЦИЯ КСТОВО ---")
    print(f"Целевая суббота: {target_date}")
    
    try:
        token = get_token()
    except Exception as e:
        print(f"Ошибка логина: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip()
        new_data = df[df.iloc[:, 4] == 'new'].copy()
        if new_data.empty:
            return print("Новых записей не найдено.")

        # ФИКС ВРЕМЕНИ: Считаем время в таблице сразу как московское
        msk_tz = timezone(timedelta(hours=3))
        new_data.iloc[:, 5] = pd.to_datetime(new_data.iloc[:, 5]).dt.tz_localize(msk_tz, ambiguous='infer')
        new_data = new_data[new_data.iloc[:, 5] > boundary_time]

    except Exception as e:
        print(f"Ошибка таблицы: {e}")
        return
    
    if new_data.empty: 
        return print("Все записи старые.")

    r_curr = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", json={"event_id": EVENT_ID, "event_date": target_date}, headers=headers)
    volunteers = []
    if r_curr.status_code == 200:
        existing = r_curr.json().get('result', {}).get('volunteer_list', [])
        volunteers = [{"verst_id": v['verst_id'], "role_id": v['role_id']} for v in existing]

    added_count = 0
    for _, row in new_data.iterrows():
        vid, rid = int(row.iloc[0]), int(row.iloc[1])
        if not any(v['verst_id'] == vid and v['role_id'] == rid for v in volunteers):
            volunteers.append({"verst_id": vid, "role_id": rid})
            added_count += 1

    if added_count > 0:
        payload = {"event_id": EVENT_ID, "date": target_date, "upload_status_id": 1, "volunteers": volunteers}
        res = requests.post("https://nrms.5verst.ru/api/v1/volunteer/event/save", json=payload, headers=headers)
        print(f"УСПЕХ: Добавлено {added_count}")
    else:
        print("Новых людей нет.")

if __name__ == "__main__":
    run_sync()
