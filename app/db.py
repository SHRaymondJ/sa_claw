from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.config import get_app_settings


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        tier TEXT NOT NULL,
        city TEXT NOT NULL,
        store_name TEXT NOT NULL,
        style_profile TEXT NOT NULL,
        preferred_colors TEXT NOT NULL,
        preferred_categories TEXT NOT NULL,
        size_note TEXT NOT NULL,
        preferred_channel TEXT NOT NULL,
        note TEXT NOT NULL,
        last_purchase_date TEXT NOT NULL,
        last_contact_at TEXT NOT NULL,
        lifetime_value INTEGER NOT NULL,
        annual_visits INTEGER NOT NULL,
        avatar_seed TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        importance INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        color TEXT NOT NULL,
        size_range TEXT NOT NULL,
        price INTEGER NOT NULL,
        collection_name TEXT NOT NULL,
        style_tags TEXT NOT NULL,
        image_url TEXT NOT NULL,
        image_source_name TEXT NOT NULL,
        image_source_url TEXT NOT NULL,
        replacement_strategy TEXT NOT NULL,
        summary TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory (
        product_id TEXT PRIMARY KEY,
        availability TEXT NOT NULL,
        store_stock INTEGER NOT NULL,
        warehouse_stock INTEGER NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS follow_up_tasks (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        task_type TEXT NOT NULL,
        due_date TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        suggested_tone TEXT NOT NULL,
        reason TEXT NOT NULL,
        recommended_product_ids TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS interaction_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversation_sessions (
        id TEXT PRIMARY KEY,
        advisor_name TEXT NOT NULL,
        store_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversation_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES conversation_sessions(id)
    )
    """,
]


PRODUCT_IMAGE_CATALOG = [
    {
        "image_url": "/crm/products/look-01.svg",
        "source_name": "replaceable-local-illustration",
        "source_url": "https://ui.shadcn.com",
    },
    {
        "image_url": "/crm/products/look-02.svg",
        "source_name": "replaceable-local-illustration",
        "source_url": "https://ui.shadcn.com",
    },
    {
        "image_url": "/crm/products/look-03.svg",
        "source_name": "replaceable-local-illustration",
        "source_url": "https://ui.shadcn.com",
    },
    {
        "image_url": "/crm/products/look-04.svg",
        "source_name": "replaceable-local-illustration",
        "source_url": "https://ui.shadcn.com",
    },
    {
        "image_url": "/crm/products/look-05.svg",
        "source_name": "replaceable-local-illustration",
        "source_url": "https://ui.shadcn.com",
    },
    {
        "image_url": "/crm/products/look-06.svg",
        "source_name": "replaceable-local-illustration",
        "source_url": "https://ui.shadcn.com",
    },
]


def get_connection() -> sqlite3.Connection:
    settings = get_app_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()
        customer_count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        if customer_count == 0:
            seed_database(connection)


def seed_database(connection: sqlite3.Connection) -> None:
    rng = random.Random(42)
    settings = get_app_settings()
    now = datetime.now(timezone.utc)

    surnames = ["林", "周", "许", "陈", "沈", "梁", "顾", "韩", "乔", "袁", "宋", "郑"]
    given_names = ["知夏", "清越", "言初", "墨宁", "安禾", "可颂", "亦棠", "若汐", "明夏", "青岚"]
    tiers = ["黑金", "高潜", "重点", "稳定"]
    profiles = ["通勤精裁", "松弛针织", "轻礼服", "假日丹宁", "极简层搭"]
    colors = ["象牙白", "石墨灰", "雾蓝", "栗棕", "橄榄绿", "燕麦色"]
    categories = ["西装", "衬衫", "针织", "风衣", "半裙", "连衣裙", "牛仔", "外套"]
    product_templates = [
        ("静线", "西装", "双排扣外套"),
        ("知屿", "衬衫", "垂感衬衫"),
        ("温序", "针织", "细针套衫"),
        ("雾航", "风衣", "轻量风衣"),
        ("折光", "半裙", "修身半裙"),
        ("浅湾", "连衣裙", "通勤长裙"),
        ("原野", "牛仔", "直筒牛仔裤"),
        ("边界", "外套", "短款夹克"),
    ]
    customer_tags = [
        "高净值",
        "近 14 天未联系",
        "偏好通勤",
        "偏好低饱和",
        "最近看过新季西装",
        "生日月",
        "本周可到店",
        "偏好整套搭配",
        "对新品敏感",
        "微信回复积极",
    ]

    for index in range(96):
        series, category, subcategory = product_templates[index % len(product_templates)]
        image = PRODUCT_IMAGE_CATALOG[index % len(PRODUCT_IMAGE_CATALOG)]
        color = colors[index % len(colors)]
        product_id = f"P{index + 1:03d}"
        style_tags = ["利落", "可通勤", "面料挺阔"] if category == "西装" else ["柔和", "易搭配", "高频穿着"]
        price = 699 + (index % 8) * 180
        connection.execute(
            """
            INSERT INTO products (
                id, name, category, subcategory, color, size_range, price,
                collection_name, style_tags, image_url, image_source_name,
                image_source_url, replacement_strategy, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                f"{series} {color}{subcategory}",
                category,
                subcategory,
                color,
                "S-XL",
                price,
                "春夏城市系列",
                json.dumps(style_tags, ensure_ascii=False),
                image["image_url"],
                image["source_name"],
                image["source_url"],
                "如后续接入真实商品图，保持同尺寸比例并更新来源字段。",
                f"{series} 系列的 {subcategory}，更适合 {color} 与通勤层搭场景。",
            ),
        )
        stock = 2 + (index % 9)
        warehouse = 8 + (index % 16)
        availability = "现货充足" if stock >= 5 else "门店余量紧张"
        connection.execute(
            "INSERT INTO inventory (product_id, availability, store_stock, warehouse_stock) VALUES (?, ?, ?, ?)",
            (product_id, availability, stock, warehouse),
        )

    for index in range(360):
        name = f"{surnames[index % len(surnames)]}{given_names[index % len(given_names)]}"
        customer_id = f"C{index + 1:03d}"
        tier = tiers[index % len(tiers)]
        profile = profiles[index % len(profiles)]
        purchase_offset = 2 + (index % 75)
        contact_offset = 1 + (index % 28)
        preferred_colors = [colors[index % len(colors)], colors[(index + 2) % len(colors)]]
        preferred_categories = [categories[index % len(categories)], categories[(index + 3) % len(categories)]]
        connection.execute(
            """
            INSERT INTO customers (
                id, name, tier, city, store_name, style_profile, preferred_colors,
                preferred_categories, size_note, preferred_channel, note,
                last_purchase_date, last_contact_at, lifetime_value, annual_visits, avatar_seed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                name,
                tier,
                "上海",
                settings.store_name,
                profile,
                json.dumps(preferred_colors, ensure_ascii=False),
                json.dumps(preferred_categories, ensure_ascii=False),
                rng.choice(["上装 M / 下装 27", "上装 S / 下装 26", "上装 L / 下装 28"]),
                rng.choice(["微信", "企微", "电话"]),
                f"偏好 {profile}，更在意版型和面料触感。",
                (now - timedelta(days=purchase_offset)).date().isoformat(),
                (now - timedelta(days=contact_offset)).isoformat(),
                6000 + (index % 24) * 680,
                2 + (index % 10),
                f"seed-{index % 12}",
            ),
        )

        chosen_tags = rng.sample(customer_tags, 3)
        for importance, tag in enumerate(chosen_tags, start=1):
            connection.execute(
                "INSERT INTO customer_tags (customer_id, tag, importance) VALUES (?, ?, ?)",
                (customer_id, tag, importance),
            )

        for log_index in range(2):
            connection.execute(
                """
                INSERT INTO interaction_logs (customer_id, channel, summary, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    customer_id,
                    "微信" if log_index == 0 else "到店",
                    f"围绕 {preferred_categories[0]} 做过推荐，客户对 {preferred_colors[0]} 反馈较好。",
                    (now - timedelta(days=contact_offset + log_index * 6)).isoformat(),
                ),
            )

    for index in range(42):
        customer_id = f"C{index + 1:03d}"
        product_ids = [f"P{(index % 24) + 1:03d}", f"P{((index + 9) % 24) + 1:03d}"]
        due_date = (now + timedelta(days=(index % 5) - 1)).date().isoformat()
        priority = ["高", "中", "中", "低"][index % 4]
        status = "open" if index % 6 != 0 else "done"
        task_type = ["回访未触达客户", "推荐新季单品", "生日月关怀", "提醒试穿预约"][index % 4]
        connection.execute(
            """
            INSERT INTO follow_up_tasks (
                id, customer_id, task_type, due_date, priority, status,
                suggested_tone, reason, recommended_product_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"T{index + 1:03d}",
                customer_id,
                task_type,
                due_date,
                priority,
                status,
                ["利落", "自然", "亲和", "关怀"][index % 4],
                "客户近期未收到定向推荐，且店内有匹配库存。",
                json.dumps(product_ids, ensure_ascii=False),
            ),
        )

    connection.commit()


def ensure_session(connection: sqlite3.Connection, session_id: str, advisor_name: str, store_name: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    exists = connection.execute(
        "SELECT 1 FROM conversation_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if exists:
        connection.execute(
            "UPDATE conversation_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
    else:
        connection.execute(
            """
            INSERT INTO conversation_sessions (id, advisor_name, store_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, advisor_name, store_name, now, now),
        )
    connection.commit()


def add_turn(connection: sqlite3.Connection, session_id: str, role: str, message: str, summary: str) -> None:
    connection.execute(
        """
        INSERT INTO conversation_turns (session_id, role, message, summary, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, role, message, summary, datetime.now(timezone.utc).isoformat()),
    )
    connection.execute(
        "UPDATE conversation_sessions SET updated_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), session_id),
    )
    connection.commit()


def get_recent_turn_summaries(connection: sqlite3.Connection, session_id: str, limit: int = 4) -> list[str]:
    rows = connection.execute(
        """
        SELECT summary
        FROM conversation_turns
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [row["summary"] for row in reversed(rows)]


def row_to_dict(row: Optional[sqlite3.Row] = None) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)
