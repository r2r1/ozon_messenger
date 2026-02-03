import json
import time
import os
from gologin import GoLogin
from urllib.parse import quote

# --- Настройки ---
PROFILES_FILE = "profiles/data/profiles.json"
DELAY_BETWEEN_PROFILES = 10  # Время открытия одного профиля (сек)
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"  # ← Замени на свой токен из https://app.gologin.com/#/settings

def read_profiles_from_json(filepath):
    """Читает profiles.json и возвращает список профилей"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("profiles", [])
            else:
                print("❌ Неверный формат файла profiles.json")
                return []
    except FileNotFoundError:
        print(f"❌ Файл не найден: {filepath}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка чтения JSON: {e}")
        return []

if __name__ == "__main__":
    # Проверяем токен
    if API_TOKEN == "your_api_token_here":
        print("❗ Укажи свой API токен Gologin в коде!")
        exit(1)

    # Читаем профили
    profiles = read_profiles_from_json(PROFILES_FILE)
    if not profiles:
        print("❌ Нет профилей для запуска.")
        exit(1)

    print(f"📁 Найдено профилей: {len(profiles)}")

    for idx, profile in enumerate(profiles, start=1):
        profile_name = profile.get("name")
        profile_id = profile.get("id")

        if not profile_id:
            print(f"{idx}. ⚠️ Пропущен: нет ID")
            continue

        if not profile_name:
            print(f"{idx}. ⚠️ Пропущен: нет имени")
            continue

        print(f"\n➡️ {idx}. Запуск профиля: {profile_name} (ID: {profile_id})")

        # Инициализируем GoLogin
        gl = GoLogin({
            "token": API_TOKEN,
            "profile_id": profile_id,
            "skip_proxy_check": True,
        })

        try:
            # Запускаем браузер
            debugger_address = gl.start()
            print(f"✅ Браузер запущен: {profile_name}")

            # Ждём 10 секунд
            time.sleep(DELAY_BETWEEN_PROFILES)

            # Останавливаем браузер
            gl.stop()
            print(f"🛑 Браузер остановлен: {profile_name}")

        except Exception as e:
            print(f"❌ Ошибка при работе с профилем {profile_name}: {e}")
            try:
                gl.stop()  # Попробуем остановить, если завис
            except:
                pass

        # Пауза перед следующим профилем (не обязательна, но можно добавить)
        if idx < len(profiles):
            print(f"⏳ Ожидание перед следующим профилем...")

    print("🎉 Все профили были запущены и закрыты по очереди!")
