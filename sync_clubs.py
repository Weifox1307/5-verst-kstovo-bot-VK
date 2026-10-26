# -*- coding: utf-8 -*-
import os
import re
import time
import json
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# 1. Настройки Google Drive
# ID твоего файла на Google Диске (возьми из адресной строки при открытии файла)
DRIVE_FILE_ID = os.environ.get("DRIVE_FILE_ID")
SERVICE_ACCOUNT_JSON = os.environ.get("GDRIVE_SERVICE_ACCOUNT_KEY")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}
base_url = "https://5verst.ru/kstovoyubileyniy/results/all/"
domain = "https://5verst.ru"

session = requests.Session()
session.headers.update(headers)

def get_drive_service():
    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def download_old_excel_from_drive(drive_service):
    print("Скачиваю предыдущую таблицу с Google Диска...")
    try:
        request = drive_service.files().get_media(fileId=DRIVE_FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        old_df = pd.read_excel(fh, sheet_name=0)
        print("Предыдущая таблица успешно получена!")
        return old_df
    except Exception as e:
        print(f"Не удалось загрузить старый файл с Диска (первый запуск?): {e}")
        return None

def upload_new_excel_to_drive(drive_service, local_file_path):
    print("Обновляю файл на Google Диске...")
    media = MediaFileUpload(local_file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    drive_service.files().update(
        fileId=DRIVE_FILE_ID,
        media_body=media
    ).execute()
    print("Google Диск успешно обновлён! Ссылка и ID файла остались прежними.")

def get_event_info():
    print("Получаю официальный список стартов...")
    try:
        response = session.get(base_url, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []

        table = soup.find('table')
        if not table:
            return []

        rows = table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                link_tag = cols[1].find('a')
                if link_tag:
                    date_str = link_tag.get_text(strip=True)
                    href = link_tag.get('href')
                    url = href if href.startswith('http') else (domain + href if href.startswith('/') else f"{domain}/{href}")

                    try:
                        f_target = int(cols[2].get_text(strip=True))
                        v_target = int(cols[3].get_text(strip=True))
                    except:
                        f_target, v_target = 0, 0

                    try:
                        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                        events.append({
                            'date': date_obj,
                            'url': url,
                            'f_target': f_target,
                            'v_target': v_target
                        })
                    except:
                        continue

        events.sort(key=lambda x: x['date'])
        return events
    except Exception as e:
        print(f"Ошибка получения списка: {e}")
        return []

def extract_clubs(element):
    run, vol = 0, 0
    if not element:
        return run, vol
    imgs = element.find_all('img')
    for img in imgs:
        src = img.get('src', '')
        if '_finish.svg' in src:
            m = re.search(r'(\d+)_finish', src)
            if m:
                run = int(m.group(1))
        elif '_volunteer.svg' in src:
            m = re.search(r'(\d+)_volunteer', src)
            if m:
                vol = int(m.group(1))
    return run, vol

def parse_single_event(event):
    date_str = event['date'].strftime("%d.%m.%Y")
    print(f"Старт {date_str}...", end=" ")

    try:
        response = session.get(event['url'], timeout=25)
        if response.status_code == 429:
            print("Лимит 429! Ожидание 60 сек...")
            time.sleep(60)
            return parse_single_event(event)

        soup = BeautifulSoup(response.text, 'html.parser')
        local_people = {}

        # Финишеры
        f_table = soup.find('table', class_='results-table')
        if f_table:
            for row in f_table.find_all('tr'):
                link = row.find('a', href=re.compile(r'/userstats/\d+'))
                if link:
                    user_id = link.get('href').rstrip('/').split('/')[-1]
                    name = link.get_text(strip=True)
                    r_c, v_c = extract_clubs(row)
                    local_people[user_id] = {
                        'user_id': str(user_id),
                        'Имя': name,
                        'Клуб финишей': r_c,
                        'Клуб волонтерств': v_c
                    }

        # Волонтеры
        v_table = None
        for t in soup.find_all('table'):
            if "РОЛЬ" in t.get_text().upper():
                v_table = t
                break

        if v_table:
            for row in v_table.find_all('tr'):
                link = row.find('a', href=re.compile(r'/userstats/\d+'))
                if link:
                    user_id = link.get('href').rstrip('/').split('/')[-1]
                    name = link.get_text(strip=True)
                    r_c, v_c = extract_clubs(row)

                    if user_id not in local_people:
                        local_people[user_id] = {
                            'user_id': str(user_id),
                            'Имя': name,
                            'Клуб финишей': r_c,
                            'Клуб волонтерств': v_c
                        }
                    else:
                        local_people[user_id]['Клуб финишей'] = max(local_people[user_id]['Клуб финишей'], r_c)
                        local_people[user_id]['Клуб волонтерств'] = max(local_people[user_id]['Клуб волонтерств'], v_c)

        print(f"ОК ({len(local_people)} чел.)")
        return list(local_people.values())

    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def main():
    drive_service = get_drive_service()
    old_df = download_old_excel_from_drive(drive_service)

    events_list = get_event_info()
    if not events_list:
        print("Старты не найдены.")
        return

    print(f"\nНайдено стартов: {len(events_list)}")
    final_database = {}

    for event in events_list:
        people = parse_single_event(event)
        for p in people:
            name = p['Имя']
            if name not in final_database:
                final_database[name] = p
            else:
                final_database[name]['Клуб финишей'] = max(final_database[name]['Клуб финишей'], p['Клуб финишей'])
                final_database[name]['Клуб волонтерств'] = max(final_database[name]['Клуб волонтерств'], p['Клуб волонтерств'])

        time.sleep(random.uniform(5.0, 7.0))

    new_df = pd.DataFrame(list(final_database.values()))
    # Очистка нулевых
    new_df = new_df[(new_df['Клуб финишей'] > 0) | (new_df['Клуб волонтерств'] > 0)].copy()

    # Сравнение (Diff)
    if old_df is not None:
        merged = pd.merge(
            new_df,
            old_df[['Имя', 'Клуб финишей', 'Клуб волонтерств', 'Примечания (парк)', 'Статус вручения']],
            on='Имя',
            how='left',
            suffixes=('', '_было')
        )

        merged['Клуб финишей_было'] = merged['Клуб финишей_было'].fillna(0).astype(int)
        merged['Клуб волонтерств_было'] = merged['Клуб волонтерств_было'].fillna(0).astype(int)

        changes = []
        gramoty_rows = []

        for _, r in merged.iterrows():
            name = r['Имя']
            cur_r, prev_r = r['Клуб финишей'], r['Клуб финишей_было']
            cur_v, prev_v = r['Клуб волонтерств'], r['Клуб волонтерств_было']
            park_note = r['Примечания (парк)'] if pd.notna(r['Примечания (парк)']) else ""
            status = r['Статус вручения'] if pd.notna(r['Статус вручения']) else ""

            ch_items = []
            if cur_r > prev_r:
                ch_items.append(f"Финиши: {prev_r} → {cur_r}")
                gramoty_rows.append({
                    'Имя участника': name,
                    'Смена клуба': f"Финиши: {prev_r} → {cur_r}",
                    'Необходимая грамота': f"Клуб {cur_r} финишей",
                    'Статус вручения': status if status else 'Подготовить',
                    'Примечание': park_note if park_note else 'Новый клуб финишей'
                })

            if cur_v > prev_v:
                ch_items.append(f"Волонтерства: {prev_v} → {cur_v}")
                gramoty_rows.append({
                    'Имя участника': name,
                    'Смена клуба': f"Волонтерства: {prev_v} → {cur_v}",
                    'Необходимая грамота': f"Клуб {cur_v} волонтерств",
                    'Статус вручения': status if status else 'Подготовить',
                    'Примечание': park_note if park_note else 'Новый клуб волонтерств'
                })

            changes.append(", ".join(ch_items) if ch_items else "")

        merged['Смена клуба'] = changes
        merged['Примечания (парк)'] = merged['Примечания (парк)'].fillna("")
        merged['Статус вручения'] = merged['Статус вручения'].fillna("")

        sheet1_df = merged[['Имя', 'Клуб финишей', 'Клуб волонтерств', 'Смена клуба', 'Примечания (парк)', 'Статус вручения']]
        sheet1_df = sheet1_df.sort_values(by=['Клуб финишей', 'Клуб волонтерств'], ascending=False)
        gramoty_df = pd.DataFrame(gramoty_rows)
    else:
        new_df['Смена клуба'] = ""
        new_df['Примечания (парк)'] = ""
        new_df['Статус вручения'] = ""
        sheet1_df = new_df[['Имя', 'Клуб финишей', 'Клуб волонтерств', 'Смена клуба', 'Примечания (парк)', 'Статус вручения']]
        sheet1_df = sheet1_df.sort_values(by=['Клуб финишей', 'Клуб волонтерств'], ascending=False)
        gramoty_df = pd.DataFrame(columns=['Имя участника', 'Смена клуба', 'Необходимая грамота', 'Статус вручения', 'Примечание'])

    output_filename = "updated_clubs.xlsx"
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        sheet1_df.to_excel(writer, sheet_name='Sheet1', index=False)
        gramoty_df.to_excel(writer, sheet_name='Список на выдачу грамот', index=False)

    print(f"Готово! В клубах: {len(sheet1_df)}, на грамоты: {len(gramoty_df)}")
    upload_new_excel_to_drive(drive_service, output_filename)

if __name__ == '__main__':
    main()
