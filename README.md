# Ozon Parser

Парсер товаров Ozon.ru с GUI и Telegram-ботом. Многопоточный сбор данных о товарах и продавцах.

## Demo

<video src="assets/demo.mp4" controls width="100%"></video>


## Возможности

- ✅ Парсинг до 10,000 товаров из категорий
- ✅ Данные о продавцах: ИНН, рейтинг, статистика
- ✅ Многопоточность (до 5 воркеров)
- ✅ Экспорт в Excel + JSON
- ✅ Telegram бот для управления
- ✅ GUI интерфейс

## Установка

```bash
git clone https://github.com/NurjahonErgashevMe/ozon-parser
cd ozon-parser
pip install -r requirements.txt
```

**Требования**: Python 3.11, Chrome браузер

## Запуск

```bash
python main.py          # GUI
python bot.py           # Только Telegram бот
python app.py           # CLI
```

## Конфигурация

Создайте `config.txt`:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_user_id
USER_your_user_id_SELECTED_FIELDS=seller_name,company_name,seller_link,orders_count,average_rating,reviews_count,inn,working_time
USER_your_user_id_FIELD_ORDER=seller_name,company_name,seller_link,orders_count,average_rating,reviews_count,inn,working_time
USER_your_user_id_DEFAULT_COUNT=500
USER_your_user_id_MIN_ORDERS=0
```

## Доступные поля

| Поле | Описание |
|------|----------|
| `seller_id` | ID продавца |
| `seller_name` | Имя продавца |
| `company_name` | Название компании |
| `inn` | ИНН продавца |
| `orders_count` | Количество заказов |
| `reviews_count` | Количество отзывов |
| `average_rating` | Средний рейтинг |
| `working_time` | Дата регистрации |
| `seller_link` | Ссылка на продавца |

## Особенности

- **Обход блокировки**: 3 драйвера × 3 попытки = 9 попыток обхода антибота
- **Резервный поиск seller_id**: если не найден в основных данных, ищет по всему JSON
- **Умное управление ресурсами**: автоматическое распределение воркеров между пользователями
- **Headless режим**: настраивается в `src/config/settings.py`

## Структура вывода

```
output/
└── category_name_DD.MM.YYYY_HH-MM-SS/
    ├── links_*.json               # Собранные ссылки
    ├── category_*.json            # Данные в JSON
    └── category_*.xlsx            # Excel отчет
```

## Troubleshooting

**Парсинг селлеров не работает?**
- Проверьте что в `SELECTED_FIELDS` есть хотя бы одно поле селлера: `seller_name`, `company_name`, `inn`, `orders_count`, `reviews_count`, `average_rating`, `working_time`, `seller_link`

**Нужна фильтрация по заказам продавца?**
- Установите `USER_<id>_MIN_ORDERS` (0 — отключить фильтр).

**Блокировка Ozon?**
- Установите `HEADLESS = False` в `src/config/settings.py`
- Используйте прокси
- Увеличьте задержки между запросами

## Лицензия

MIT License