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
    # Ищем ближайшую субботу
    days_ahead = (5 - now.weekday() + 7) % 7
    # Если сегодня суббота и время после 11:00, планируем на следующую
    if days_ahead == 0 and now.hour >= 11:
        days_ahead = 7
    target = now + timedelta(days=days_ahead)
    return target.strftime("%d.%m.%Y")

def get_sync_boundary():
    now = get_moscow_now()
    days_since_sat = (now.weekday() - 5) % 7
    last_sat = now - timedelta(days=days_since_sat)
    boundary = last_sat.replace(hour=11, minute=0, second=0, microsecond=0)
    # Если сейчас суббота до 11 утра, граница - прошлая суббота
    if now.weekday() == 5 and now.hour < 11:
        boundary -= timedelta(days=7)
    return boundary

def get_token():
    if not NRMS_USER or not NRMS_PASS:
        return None
    username = NRMS_USER if NRMS_USER.upper().startswith('A') else f"A{NRMS_USER}"
    try:
        r = requests.post("https://nrms.5verst.ru/api/v1/auth/login", 
                          json={"username": username, "password": NRMS_PASS}, 
                          timeout=15)
        return r.json().get('result', {}).get('token')
    except Exception as e:
        print(f"Ошибка входа в NRMS: {e}")
        return None

def run_sync():
    if not SHEET_URL:
        return print("Ошибка: Не указан SHEET_CSV_URL")
        
    target_date = get_target_date()
    boundary_time = get_sync_boundary().replace(tzinfo=timezone(timedelta(hours=3)))
    
    print(f"--- СИНХРОНИЗАЦИЯ КСТОВО ---")
    print(f"Целевая суббота: {target_date}")
    
    token = get_token()
    if not token:
        return print("Не удалось получить токен NRMS.")

    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Читаем Google Таблицу (CSV)
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip()
        
        # Фильтруем только записи со статусом 'new'
        # Столбец 4 - Статус (new), Столбец 5 - Дата записи
        new_data = df[df.iloc[:, 4] == 'new'].copy()
        
        if new_data.empty:
            return print("Новых записей в таблице не найдено.")

        # Преобразование даты записи в московское время для сравнения с границей
        msk_tz = timezone(timedelta(hours=3))
        new_data.iloc[:, 5] = pd.to_datetime(new_data.iloc[:, 5]).dt.tz_localize(msk_tz, ambiguous='infer')
        
        # Оставляем только те, что были созданы после "границы" (11:00 прошлой субботы)
        new_data = new_data[new_data.iloc[:, 5] > boundary_time]

    except Exception as e:
        return print(f"Ошибка при обработке таблицы: {e}")
    
    if new_data.empty: 
        return print("Все новые записи в таблице старше границы синхронизации.")

    # Получаем текущий список волонтеров из NRMS, чтобы не дублировать
    try:
        r_curr = requests.post("https://nrms.5verst.ru/api/v1/event/volunteer/list", 
                               json={"event_id": EVENT_ID, "event_date": target_date}, 
                               headers=headers, timeout=15)
        volunteers = []
        if r_curr.status_code == 200:
            existing = r_curr.json().get('result', {}).get('volunteer_list', [])
            # Сохраняем существующих в формате NRMS
            volunteers = [{"verst_id": int(v['verst_id']), "role_id": int(v['role_id'])} for v in existing]
    except Exception as e:
        return print(f"Ошибка получения списка NRMS: {e}")

    # Добавляем новых из таблицы, если их еще нет в NRMS
    added_count = 0
    for _, row in new_data.iterrows():
        try:
            # Превращаем ID в числа для корректного сравнения
            vid = int(float(row.iloc[0]))
            rid = int(float(row.iloc[1]))
            
            if not any(v['verst_id'] == vid and v['role_id'] == rid for v in volunteers):
                volunteers.append({"verst_id": vid, "role_id": rid})
                added_count += 1
        except: continue

    # Если есть кого добавить — сохраняем весь список
    if added_count > 0:
        payload = {
            "event_id": EVENT_ID, 
            "date": target_date, 
            "upload_status_id": 1, 
            "volunteers": volunteers
        }
        try:
            res = requests.post("https://nrms.5verst.ru/api/v1/volunteer/event/save", 
                                json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                print(f"УСПЕХ: Добавлено новых волонтеров: {added_count}")
            else:
                print(f"Ошибка сохранения NRMS: {res.text}")
        except Exception as e:
            print(f"Критическая ошибка при отправке в NRMS: {e}")
    else:
        print("В NRMS уже есть все люди, указанные в таблице.")

if __name__ == "__main__":
    run_sync()
