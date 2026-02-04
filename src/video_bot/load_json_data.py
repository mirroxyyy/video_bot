import asyncio
import json
import sys
from datetime import datetime

import asyncpg

from video_bot.config import get_config

BATCH_SIZE = 10000


async def load_data(videos: list):
    video_records = []
    snapshot_records = []

    for video in videos:
        video_records.append(
            (
                video["id"],
                datetime.fromisoformat(video["video_created_at"]),
                int(video["views_count"]),
                int(video["likes_count"]),
                int(video["reports_count"]),
                int(video["comments_count"]),
                video["creator_id"],
                datetime.fromisoformat(video["created_at"]),
                datetime.fromisoformat(video["updated_at"]),
            )
        )
        for snapshot in video["snapshots"]:
            snapshot_records.append(
                (
                    snapshot["id"],
                    snapshot["video_id"],
                    int(snapshot["views_count"]),
                    int(snapshot["likes_count"]),
                    int(snapshot["reports_count"]),
                    int(snapshot["comments_count"]),
                    int(snapshot["delta_views_count"]),
                    int(snapshot["delta_likes_count"]),
                    int(snapshot["delta_reports_count"]),
                    int(snapshot["delta_comments_count"]),
                    datetime.fromisoformat(snapshot["created_at"]),
                    datetime.fromisoformat(snapshot["updated_at"]),
                )
            )

    config = get_config()
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASS,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT,
    )

    async with conn.transaction():
        await conn.copy_records_to_table(
            "videos",
            records=video_records,
            columns=[
                "id",
                "video_created_at",
                "views_count",
                "likes_count",
                "reports_count",
                "comments_count",
                "creator_id",
                "created_at",
                "updated_at",
            ],
        )

        await conn.copy_records_to_table(
            "video_snapshots",
            records=snapshot_records,
            columns=[
                "id",
                "video_id",
                "views_count",
                "likes_count",
                "reports_count",
                "comments_count",
                "delta_views_count",
                "delta_likes_count",
                "delta_reports_count",
                "delta_comments_count",
                "created_at",
                "updated_at",
            ],
        )

    await conn.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python load_json_data.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path, "r") as f:
        data = json.load(f)
    videos = data["videos"]

    asyncio.run(load_data(videos))


if __name__ == "__main__":
    main()
