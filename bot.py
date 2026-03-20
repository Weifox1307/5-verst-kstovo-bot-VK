import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import os
import sys

# Достаем ключ из секретов GitHub
token = os.getenv('VK_TOKEN')

if not token:
    print("Ошибка: VK_TOKEN не найден в переменных окружения!")
    sys.exit(1)

def main():
    try:
        vk_session = vk_api.VkApi(token=token)
        longpoll = VkLongPoll(vk_session)
        vk = vk_session.get_api()
        
        print("Бот '5 вёрст Кстово' запущен и готов к работе! 🏃‍♂️")

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                msg = event.text.lower()
                user_id = event.user_id

                # Твоя база ответов
                if msg in ["привет", "старт", "начало", "инфо"]:
                    vk.messages.send(
                        user_id=user_id,
                        message="Привет, атлет! 🏃‍♂️\nСтарт каждую субботу в 9:00 в парке 'Юбилейный'.",
                        random_id=0
                    )
                elif msg == "статус":
                    vk.messages.send(
                        user_id=user_id,
                        message="Бот на базе и работает в штатном режиме! 🦾",
                        random_id=0
                    )
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        # Если ошибка, скрипт завершится, и GitHub Actions перезапустит его позже

if __name__ == "__main__":
    main()
