import requests
import json
import time

# === НАСТРОЙКИ ===
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"  # ← Замени на свой токен
BASE_URL = "https://api.gologin.com"

def get_all_profiles_minimal():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "User-Agent": "Gologin-Minimal/1.0",
    }

    minimal_profiles = []  # Будем хранить только id и name
    page = 0
    limit = 30

    print("🔄 Загружаем профили постранично...")

    while True:
        try:
            url = f"{BASE_URL}/browser/v2?page={page}&limit={limit}"
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                profiles = data.get("profiles", [])

                if not profiles:
                    print(f"🔚 Нет данных на странице {page}. Завершаем.")
                    break

                # Извлекаем только id и name
                for profile in profiles:
                    minimal_profiles.append({
                        "id": profile.get("id"),
                        "name": profile.get("name", "Без имени")  # На случай отсутствия имени
                    })

                print(f"✅ Страница {page}: добавлено {len(profiles)} профилей")

                if len(profiles) < limit:
                    break  # Это была последняя страница

                page += 1
                time.sleep(0.3)  # Лёгкая пауза, чтобы не перегружать API

            elif response.status_code == 401:
                print("❌ Ошибка авторизации: проверь API токен.")
                break
            else:
                print(f"❌ Ошибка {response.status_code}: {response.text}")
                break

        except requests.exceptions.RequestException as e:
            print(f"🌐 Ошибка запроса: {e}")
            break

    return minimal_profiles

# === Запуск ===
if __name__ == "__main__":
    profiles = get_all_profiles_minimal()

    print(f"\n📋 Всего получено профилей: {len(profiles)}")
    print("🔹 Формат: {id, name}\n")

    # Выводим первые 10
    for p in profiles[:10]:
        print(f"• ID: {p['id']} | Name: {p['name']}")

    if len(profiles) > 10:
        print(f"... и ещё {len(profiles) - 10} профилей.")

    with open("profiles/data/profiles.json", "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    print("\n💾 Сохранено в 'profiles_id_name.json'")
