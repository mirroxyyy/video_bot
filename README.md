# Video Analytics Telegram Bot

Telegram-бот для аналитики видео-креаторов на основе данных из PostgreSQL. Позволяет задавать вопросы на русском языке и получать числовые ответы по видео и их просмотрам.


## Стек технологий

* Python 3.13
* PostgreSQL
* SQLAlchemy
* aiogram
* Pydantic v2
* OpenAI API
* Docker


## Переменные окружения (.env)

```bash
DB_USER=user
DB_PASS=password
DB_NAME=video_bot
DB_HOST=localhost
DB_PORT=5432

BOT_TOKEN=token
OPENAI_KEY=key
OPENAI_URL=url

LOG_LEVEL=INFO
```

* `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
* `BOT_TOKEN`: токен Telegram-бота
* `OPENAI_KEY` и `OPENAI_URL`: для работы LLM
* DB_*: данные подключения к PostgreSQL


## Загрузка данных

Для загрузки JSON-файла в базу используйте Docker:

```bash
docker run \
    --rm \
    --env-file .env \
    -v "$PWD/videos.json":/videos.json \
    video_bot:latest \
    python src/video_bot/load_json_data.py /videos.json
```

Для работы необходимо указать путь к файлу `videos.json`, в команде выше предполагается, что файл лежит в папке, из которой запускается команда.

## Запуск бота

```bash
docker run -d --env-file .env video_bot:latest
```

## Архитектура и логика

1. **Пользовательский запрос (NL)** -> **LLM** -> **JSON AST (QueryPlanV2)**

   * Строго валидная структура через Pydantic v2
   * Поддерживает: count, sum, distinct, фильтры AND/OR, date ranges, delta_* поля

2. **JSON -> SQLAlchemy-запрос**

   * Через builder (`query_builder.py`)
   * Автоматически выбирается правильная таблица (`videos` / `video_snapshots`) и поле даты

3. **SQLAlchemy -> PostgreSQL** -> результат одно число

4. **Ответ пользователю** в Telegram
