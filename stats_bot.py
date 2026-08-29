import os
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import numpy as np  # <-- Библиотека для расчета линии тренда
import vk_api
from vk_api.upload import VkUpload
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================= НАСТРОЙКИ БОТА =================
VK_TOKEN = os.getenv('VK_TOKEN')
PEER_ID = 2000000001 # ID беседы (ОБЯЗАТЕЛЬНО ПРОВЕРЬ, ЧТО ГРУППА АДМИН В ЧАТЕ)
STATS_URL = 'https://stat5verst.ru/kstovoyubileyniy/starts_all'
# ==================================================

def fetch_and_parse_data():
    """Открывает страницу в скрытом браузере, дожидается скриптов и парсит таблицу"""
    print(f"[{datetime.now()}] Открываем браузер для загрузки {STATS_URL}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(STATS_URL)
        page.wait_for_selector('table', timeout=15000)
        html = page.content()
        browser.close()
    
    print(f"[{datetime.now()}] Страница загружена, ищем данные...")
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    
    if not table:
        raise ValueError("Таблица со статистикой не найдена.")

    rows = table.find_all('tr')
    
    start_numbers = []
    finishers = []
    volunteers = []

    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) >= 4:
            try:
                s_num = int(cols[0].text.strip())
                f_count = int(cols[2].text.strip())
                v_count = int(cols[3].text.strip())
                
                start_numbers.append(s_num)
                finishers.append(f_count)
                volunteers.append(v_count)
            except ValueError:
                continue

    sorted_data = sorted(zip(start_numbers, finishers, volunteers), key=lambda x: x[0])
    
    if not sorted_data:
        raise ValueError("Данные для построения графика пусты.")

    x_starts = [item[0] for item in sorted_data]
    y_finishers = [item[1] for item in sorted_data]
    y_volunteers = [item[2] for item in sorted_data]

    return x_starts, y_finishers, y_volunteers

def create_chart(x, y_fin, y_vol, filename='parkrun_stats.png'):
    print(f"[{datetime.now()}] Отрисовка графика с трендом и цифрами...")
    
    plt.style.use('seaborn-v0_8-whitegrid')
    # Сделали график чуть шире, чтобы цифрам было не тесно
    fig, ax = plt.subplots(figsize=(12, 6))

    # Рисуем основные линии
    ax.plot(x, y_fin, color='#2B326D', marker='o', linewidth=2, markersize=5, label='Финишеры')
    ax.plot(x, y_vol, color='#E6564C', marker='o', linewidth=2, markersize=5, label='Волонтёры')

    # РАСЧЕТ И ОТРИСОВКА ЛИНИИ ТРЕНДА (Линейная регрессия для финишеров)
    if len(x) > 1:
        z = np.polyfit(x, y_fin, 1)
        p = np.poly1d(z)
        ax.plot(x, p(x), color='#2B326D', linestyle='--', alpha=0.4, label='Тренд (финишеры)')

    # ДОБАВЛЕНИЕ ЦИФР НАД ТОЧКАМИ
    for i in range(len(x)):
        # Цифры финишеров (чуть выше точки)
        ax.annotate(str(y_fin[i]), (x[i], y_fin[i]), textcoords="offset points", 
                    xytext=(0, 8), ha='center', fontsize=8, color='#2B326D', fontweight='bold')
        # Цифры волонтеров (чуть ниже точки)
        ax.annotate(str(y_vol[i]), (x[i], y_vol[i]), textcoords="offset points", 
                    xytext=(0, -14), ha='center', fontsize=8, color='#E6564C', fontweight='bold')

    ax.set_title('Динамика посещаемости: 5 вёрст в парке Юбилейный | Кстово', fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel('Номер старта', fontsize=12, labelpad=10)
    ax.set_ylabel('Количество человек', fontsize=12, labelpad=10)
    
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, linestyle='--', alpha=0.7)

    # Убираем рамки сверху и справа
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Чтобы верхние цифры не улетали за край графика, искусственно поднимаем "потолок"
    max_y = max(y_fin)
    ax.set_ylim(bottom=0, top=max_y + (max_y * 0.15))

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()
    
    return filename

def send_to_vk(filename):
    if not VK_TOKEN:
        raise ValueError("Токен ВК не найден в переменных окружения!")

    print(f"[{datetime.now()}] Отправка в ВК (Peer ID: {PEER_ID})...")
    
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    upload = VkUpload(vk_session)

    # ИСПРАВЛЕНИЕ: Явно указываем peer_id серверу загрузки ВКонтакте
    photo = upload.photo_messages(photos=filename, peer_id=PEER_ID)[0]
    attachment = f"photo{photo['owner_id']}_{photo['id']}"

    message_text = "📊 Еженедельная статистика парковых пробежек обновлена! Динамика финишеров и волонтеров."

    vk.messages.send(
        peer_id=PEER_ID,
        random_id=vk_api.utils.get_random_id(),
        message=message_text,
        attachment=attachment
    )
    print(f"[{datetime.now()}] Успешно отправлено!")

def main():
    image_path = 'parkrun_stats.png'
    try:
        x, y_fin, y_vol = fetch_and_parse_data()
        create_chart(x, y_fin, y_vol, image_path)
        send_to_vk(image_path)
    except Exception as e:
        print(f"[{datetime.now()}] ПРОИЗОШЛА ОШИБКА: {e}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == '__main__':
    main()
