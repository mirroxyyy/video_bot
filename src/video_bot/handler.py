from datetime import datetime, timedelta
from logging import getLogger

from aiogram import Router
from aiogram.types import Message
from openai import AsyncOpenAI
from pydantic import ValidationError
from sqlalchemy import ClauseElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from video_bot.answer import (
    Answer,
    Condition,
    ConditionGroup,
    Entity,
    FilterNode,
    LogicalOp,
    Operation,
)
from video_bot.config import get_config
from video_bot.database.models import VideoOrm, VideoSnapshotOrm

logger = getLogger(__name__)
router = Router(name=__name__)

SYSTEM_PROMPT = """
Ты — аналитический парсер запросов на русском языке.
Твоя задача — преобразовывать пользовательские вопросы в СТРОГО валидный JSON,
который описывает план запроса к базе данных.

ВАЖНО:
- Ты НИКОГДА не пишешь SQL.
- Ты НИКОГДА не добавляешь поясняющий текст.
- Ты ВСЕГДА возвращаешь ТОЛЬКО валидный JSON.
- Если ты не уверен — делай самый консервативный и безопасный вариант.
- Любой ответ вне JSON считается ошибкой.

ДОСТУПНЫЕ ДАННЫЕ

В базе есть ТОЛЬКО две таблицы:

1) videos — финальная статистика по видео
Поля:
- id (string)
- creator_id (string)
- video_created_at (timestamp)
- views_count (int)
- likes_count (int)
- comments_count (int)
- reports_count (int)

2) video_snapshots — почасовые снапшоты
Поля:
- id (string)
- video_id (string)
- views_count (int)
- likes_count (int)
- comments_count (int)
- reports_count (int)
- delta_views_count (int)
- delta_likes_count (int)
- delta_comments_count (int)
- delta_reports_count (int)
- created_at (timestamp)

ОБЩИЕ ПРАВИЛА

1) Если в вопросе есть слова: "выросло", "прирост", "изменилось", "увеличилось", ТО нужно использовать ТОЛЬКО поля delta_* из video_snapshots.
2) Если спрашивают: "сколько всего видео", "видео вышло", "опубликовано", ТО используется таблица videos.
3) Если спрашивают: "за день", "в этот день", "28 ноября 2025", ТО фильтрация делается по одному календарному дню.
4) Если спрашивают: "с X по Y включительно", ТО это диапазон дат [X, Y].
5) "Сколько разных видео" = count DISTINCT video_id.
6) Всегда возвращается ОДНО число.

ФОРМАТ JSON (СТРОГО)

JSON ВСЕГДА имеет следующую структуру:

{
  "entity": "video" | "video_snapshots",
  "operation": "count" | "sum",
  "field": string,
  "distinct": boolean,
  "where": <filter_tree> | null,
  "date_filter": {
    "from": "YYYY-MM-DDTHH:MM:SS",
    "to": "YYYY-MM-DDTHH:MM:SS"
  } | null
}

FILTER TREE

Фильтры описываются как логическое дерево.

1) ГРУППА:

{
  "type": "group",
  "op": "and" | "or",
  "conditions": [ <filter_node>, ... ]
}

2) УСЛОВИЕ:

{
  "type": "condition",
  "field": string,
  "operator": "=" | "!=" | ">" | ">=" | "<" | "<=",
  "value": number | string
}

ОГРАНИЧЕНИЯ:
- field ДОЛЖЕН существовать в выбранной таблице.
- delta_* поля МОЖНО использовать ТОЛЬКО с entity = "video_snapshots".
- video_created_at используется ТОЛЬКО для entity = "video".
- created_at используется ТОЛЬКО для entity = "video_snapshots".
- COUNT + delta_* запрещён, КРОМЕ случаев count DISTINCT video_id.
- Если фильтров нет — where = null.
- Если даты нет — date_filter = null.

Если запрос некорректный или неоднозначный,
верни максимально безопасный вариант без выдумывания.


ПРИМЕРЫ:

Вопрос:
Сколько всего видео есть в системе?

Ответ:
{
  "entity": "video",
  "operation": "count",
  "field": "id",
  "distinct": true,
  "where": null,
  "date_filter": null
}

Вопрос:
Сколько видео у креатора с id 42 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?

Ответ:
{
  "entity": "video",
  "operation": "count",
  "field": "id",
  "distinct": true,
  "where": {
    "type": "group",
    "op": "and",
    "conditions": [
      {
        "type": "condition",
        "field": "creator_id",
        "operator": "=",
        "value": 42
      }
    ]
  },
  "date_filter": {
    "from": "2025-11-01T00:00:00",
    "to": "2025-11-05T23:59:59"
  }
}

Вопрос:
На сколько просмотров в сумме выросли все видео 28 ноября 2025?

Ответ:
{
  "entity": "video_snapshots",
  "operation": "sum",
  "field": "delta_views_count",
  "distinct": false,
  "where": null,
  "date_filter": {
    "from": "2025-11-28T00:00:00",
    "to": "2025-11-28T23:59:59"
  }
}

Вопрос:
Сколько разных видео получали новые просмотры 27 ноября 2025?

Ответ:
{
  "entity": "video_snapshots",
  "operation": "count",
  "field": "video_id",
  "distinct": true,
  "where": {
    "type": "group",
    "op": "and",
    "conditions": [
      {
        "type": "condition",
        "field": "delta_views_count",
        "operator": ">",
        "value": 0
      }
    ]
  },
  "date_filter": {
    "from": "2025-11-27T00:00:00",
    "to": "2025-11-27T23:59:59"
  }
}

ВАЖНОЕ ПРАВИЛО:
ТВОЙ ОТВЕТ — ЭТО ВСЕГДА ТОЛЬКО JSON.
НИКАКОГО ТЕКСТА, КОММЕНТАРИЕВ ИЛИ ПОЯСНЕНИЙ.
"""


async def make_request(req: str) -> str | None:
    config = get_config()
    client = AsyncOpenAI(
        base_url=config.OPENAI_URL,
        api_key=config.OPENAI_KEY,
    )

    response = await client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req},
        ],
    )
    return response.choices[0].message.content


def build_filter(node: FilterNode, entity_cls) -> ClauseElement:
    if isinstance(node, Condition):
        field = getattr(entity_cls, node.field)
        op = node.operator

        if op == "=":
            return field == node.value
        elif op == "!=":
            return field != node.value
        elif op == ">":
            return field > node.value
        elif op == ">=":
            return field >= node.value
        elif op == "<":
            return field < node.value
        elif op == "<=":
            return field <= node.value
        else:
            raise ValueError(f"Unsupported operator {op}")
    elif isinstance(node, ConditionGroup):
        children = [build_filter(c, entity_cls) for c in node.conditions]
        if node.op == LogicalOp.and_:
            return and_(*children)  # type: ignore
        elif node.op == LogicalOp.or_:
            return or_(*children)  # type: ignore
        else:
            raise ValueError(f"Unsupported logical op {node.op}")
    else:
        raise ValueError("Unknown FilterNode type")


def build_query(plan: Answer):
    entity_cls = VideoOrm if plan.entity == Entity.video else VideoSnapshotOrm

    field = getattr(entity_cls, plan.field)

    if plan.operation == Operation.count_:
        if plan.distinct:
            stmt = select(func.count(func.distinct(field)))
        else:
            stmt = select(func.count(field))
    elif plan.operation == Operation.sum:
        stmt = select(func.coalesce(func.sum(field), 0))
    else:
        raise ValueError(f"Unsupported operation {plan.operation}")

    filters = []
    if plan.where:
        filters.append(build_filter(plan.where, entity_cls))

    if plan.date_filter:
        from_date: datetime = plan.date_filter.from_
        to_date: datetime = plan.date_filter.to

        date_field = (
            entity_cls.created_at
            if plan.entity == Entity.video_snapshots
            else entity_cls.video_created_at  # type: ignore
        )
        filters.append(date_field >= from_date)
        filters.append(date_field <= to_date)

    if filters:
        stmt = stmt.where(and_(*filters))

    return stmt


async def get_answer(text) -> Answer | None:
    for _ in range(2):
        res = await make_request(f"Пользовательский запрос: {text}]")
        if not res:
            return None
        try:
            logger.info("received answer: %s", res)
            return Answer.model_validate_json(res)
        except ValidationError:
            logger.info("request error", exc_info=True)
            pass


async def get_data(sessionmaker: async_sessionmaker[AsyncSession], answer: Answer):
    stmt = build_query(answer)
    async with sessionmaker() as session:
        res = await session.execute(stmt)
    result = res.scalar_one()
    return result


@router.message()
async def handler(message: Message, sessionmaker: async_sessionmaker[AsyncSession]):
    logger.info(
        "got message from %s",
        message.from_user.id if message.from_user else message.chat.id,
    )
    if not message.text:
        await message.answer("Пустой запрос")
        return

    logger.info("received text: %s", message.text)
    try:
        answ = await get_answer(message.text)
        if not answ:
            await message.answer("Некорректный запрос")
            return

        res = await get_data(sessionmaker, answ)
        logger.info("result: %s", res)
        await message.answer(str(res))
    except BaseException:
        logger.error("handling error:", exc_info=True)
        await message.answer("Некорректный запрос")
