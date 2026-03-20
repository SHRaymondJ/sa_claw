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
        advisor_id TEXT NOT NULL DEFAULT '',
        advisor_name TEXT NOT NULL,
        store_id TEXT NOT NULL DEFAULT '',
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
    """
    CREATE TABLE IF NOT EXISTS conversation_session_state (
        session_id TEXT PRIMARY KEY,
        active_customer_id TEXT,
        active_customer_name TEXT NOT NULL DEFAULT '',
        active_intent TEXT NOT NULL DEFAULT '',
        active_product_ids TEXT NOT NULL DEFAULT '[]',
        active_task_ids TEXT NOT NULL DEFAULT '[]',
        last_style_focus TEXT NOT NULL DEFAULT '',
        resolution_confidence TEXT NOT NULL DEFAULT 'low',
        updated_at TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES conversation_sessions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_memory_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        note_type TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT NOT NULL,
        confidence TEXT NOT NULL DEFAULT 'medium',
        pinned INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        audience TEXT NOT NULL,
        trigger_terms TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT NOT NULL,
        confidence TEXT NOT NULL DEFAULT 'high',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_memory_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        note_type TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT NOT NULL,
        source_session_id TEXT NOT NULL DEFAULT '',
        confidence TEXT NOT NULL DEFAULT 'low',
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_memory_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        dimension TEXT NOT NULL,
        value TEXT NOT NULL,
        polarity TEXT NOT NULL,
        qualifier TEXT NOT NULL DEFAULT '',
        source_type TEXT NOT NULL,
        source_session_id TEXT NOT NULL DEFAULT '',
        note_source TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'confirmed',
        confidence TEXT NOT NULL DEFAULT 'medium',
        confirmed_by TEXT NOT NULL DEFAULT '',
        effective_at TEXT NOT NULL,
        expires_at TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversation_checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        workflow_name TEXT NOT NULL,
        workflow_stage TEXT NOT NULL,
        user_goal TEXT NOT NULL,
        assistant_summary TEXT NOT NULL,
        focus_customer_id TEXT NOT NULL DEFAULT '',
        focus_customer_name TEXT NOT NULL DEFAULT '',
        result_summary TEXT NOT NULL DEFAULT '',
        next_step TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES conversation_sessions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        advisor_id TEXT NOT NULL,
        store_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        session_id TEXT NOT NULL DEFAULT '',
        before_summary TEXT NOT NULL DEFAULT '',
        after_summary TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
]

CONVERSATION_SESSION_REQUIRED_COLUMNS = {
    "advisor_id": "TEXT NOT NULL DEFAULT ''",
    "store_id": "TEXT NOT NULL DEFAULT ''",
}

SESSION_STATE_REQUIRED_COLUMNS = {
    "workflow_name": "TEXT NOT NULL DEFAULT ''",
    "workflow_stage": "TEXT NOT NULL DEFAULT ''",
    "last_user_goal": "TEXT NOT NULL DEFAULT ''",
    "last_response_shape": "TEXT NOT NULL DEFAULT ''",
    "last_entity_ids": "TEXT NOT NULL DEFAULT '[]'",
    "conversation_mode": "TEXT NOT NULL DEFAULT ''",
    "handoff_reason": "TEXT NOT NULL DEFAULT ''",
    "state_version": "INTEGER NOT NULL DEFAULT 0",
    "working_memory_summary": "TEXT NOT NULL DEFAULT ''",
}


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
        _ensure_required_columns(connection, "conversation_sessions", CONVERSATION_SESSION_REQUIRED_COLUMNS)
        _ensure_required_columns(connection, "conversation_session_state", SESSION_STATE_REQUIRED_COLUMNS)
        connection.commit()
        customer_count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        if customer_count == 0:
            seed_database(connection)
        seed_customer_memory_notes(connection)
        seed_customer_memory_facts(connection)
        seed_knowledge_documents(connection)


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


def seed_customer_memory_notes(connection: sqlite3.Connection) -> None:
    note_count = connection.execute("SELECT COUNT(*) FROM customer_memory_notes").fetchone()[0]
    if note_count > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    rows = connection.execute(
        """
        SELECT id, preferred_channel, style_profile, preferred_colors, preferred_categories, note
        FROM customers
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        colors = json.loads(row["preferred_colors"])
        categories = json.loads(row["preferred_categories"])
        memory_entries = [
            (
                row["id"],
                "relationship_strategy",
                f"更适合通过{row['preferred_channel']}做轻触达，先从{row['style_profile']}与{colors[0]}切入，再带出{categories[0]}相关建议。",
                "seed-profile",
                "high",
                1,
            ),
            (
                row["id"],
                "style_preference",
                f"对{colors[0]}和{categories[0]}反馈更稳定，沟通时更在意版型、面料与穿着场景，不喜欢空泛推荐。",
                "seed-profile",
                "high",
                0,
            ),
            (
                row["id"],
                "service_note",
                row["note"],
                "seed-profile",
                "medium",
                0,
            ),
        ]
        for customer_id, note_type, content, source, confidence, pinned in memory_entries:
            connection.execute(
                """
                INSERT INTO customer_memory_notes (
                    customer_id, note_type, content, source, confidence, pinned, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (customer_id, note_type, content, source, confidence, pinned, now, now),
            )
    connection.commit()


def seed_customer_memory_facts(connection: sqlite3.Connection) -> None:
    fact_count = connection.execute("SELECT COUNT(*) FROM customer_memory_facts").fetchone()[0]
    if fact_count > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    rows = connection.execute(
        """
        SELECT id, preferred_channel, preferred_colors, preferred_categories, style_profile
        FROM customers
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        for category in json.loads(row["preferred_categories"]):
            connection.execute(
                """
                INSERT INTO customer_memory_facts (
                    customer_id, dimension, value, polarity, qualifier, source_type, source_session_id,
                    note_source, status, confidence, confirmed_by, effective_at, expires_at, created_at, updated_at
                ) VALUES (?, 'category_preference', ?, 'positive', '', 'seed-profile', '', 'preferred_categories', 'confirmed', 'high', 'system', ?, '', ?, ?)
                """,
                (row["id"], category, now, now, now),
            )
        for color in json.loads(row["preferred_colors"]):
            connection.execute(
                """
                INSERT INTO customer_memory_facts (
                    customer_id, dimension, value, polarity, qualifier, source_type, source_session_id,
                    note_source, status, confidence, confirmed_by, effective_at, expires_at, created_at, updated_at
                ) VALUES (?, 'color_preference', ?, 'positive', '', 'seed-profile', '', 'preferred_colors', 'confirmed', 'high', 'system', ?, '', ?, ?)
                """,
                (row["id"], color, now, now, now),
            )
        connection.execute(
            """
            INSERT INTO customer_memory_facts (
                customer_id, dimension, value, polarity, qualifier, source_type, source_session_id,
                note_source, status, confidence, confirmed_by, effective_at, expires_at, created_at, updated_at
            ) VALUES (?, 'service_channel', ?, 'positive', ?, 'seed-profile', '', 'customer_profile', 'confirmed', 'medium', 'system', ?, '', ?, ?)
            """,
            (row["id"], row["preferred_channel"], row["style_profile"], now, now, now),
        )
    connection.commit()


def seed_knowledge_documents(connection: sqlite3.Connection) -> None:
    count = connection.execute("SELECT COUNT(*) FROM knowledge_documents").fetchone()[0]
    if count > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    entries = [
        {
            "id": "K001",
            "topic": "relationship_maintenance",
            "audience": "advisor",
            "trigger_terms": ["维护关系", "客户关系", "关怀", "维系", "唤醒"],
            "content": "高价值会员的关系维护不要一上来就推很多商品，先从最近穿着场景、到店计划或上次反馈切入，再自然带出 1 到 2 个更匹配的选择。",
            "source": "store-playbook",
        },
        {
            "id": "K002",
            "topic": "relationship_maintenance",
            "audience": "advisor",
            "trigger_terms": ["微信", "企微", "私聊", "触达"],
            "content": "私聊开场优先用关怀式语气，避免直接成交导向。先确认近况和需求，再给一件最稳的推荐款，会比一口气发商品海报更容易得到回复。",
            "source": "store-playbook",
        },
        {
            "id": "K003",
            "topic": "product_recommendation",
            "audience": "advisor",
            "trigger_terms": ["通勤", "上班", "极简", "利落"],
            "content": "通勤类推荐要突出版型、搭配效率和场景稳定性。客户通常更在意是否省心、是否能高频穿，而不是堆砌面料术语。",
            "source": "styling-guide",
        },
        {
            "id": "K004",
            "topic": "product_recommendation",
            "audience": "advisor",
            "trigger_terms": ["颜色", "低饱和", "雾蓝", "石墨灰", "栗棕"],
            "content": "颜色偏好明确的客户，先给最接近偏好色的一款建立信任，再补一个相邻色选项做对比，命中率通常比直接做大跨度推荐更高。",
            "source": "styling-guide",
        },
        {
            "id": "K005",
            "topic": "service_boundary",
            "audience": "advisor",
            "trigger_terms": ["其他品牌", "政治", "商业", "外部"],
            "content": "工作台只讨论本品牌门店内的客户、商品、库存、任务与服务动作。超出门店数据或品牌边界的话题，应明确收口并引导回可执行范围。",
            "source": "compliance-guide",
        },
        {
            "id": "K006",
            "topic": "relationship_maintenance",
            "audience": "advisor",
            "trigger_terms": ["沉默", "很久没回", "未联系", "唤醒"],
            "content": "对沉默客户，第一轮维护的目标不是立刻成交，而是重新建立轻互动。先让客户愿意回一句，再逐步推进推荐和预约。",
            "source": "crm-sop",
        },
        {
            "id": "K007",
            "topic": "product_recommendation",
            "audience": "advisor",
            "trigger_terms": ["半裙", "外套", "西装", "现货"],
            "content": "在现货推荐里，优先给客户一个最稳主推款，再给一个替代方向。这样既显得专业，也方便客户快速做选择。",
            "source": "crm-sop",
        },
    ]
    for entry in entries:
        connection.execute(
            """
            INSERT INTO knowledge_documents (
                id, topic, audience, trigger_terms, content, source, confidence, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'high', 1, ?, ?)
            """,
            (
                entry["id"],
                entry["topic"],
                entry["audience"],
                json.dumps(entry["trigger_terms"], ensure_ascii=False),
                entry["content"],
                entry["source"],
                now,
                now,
            ),
        )
    connection.commit()


def _ensure_required_columns(connection: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, definition in columns.items():
        if column_name in existing:
            continue
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_session(
    connection: sqlite3.Connection,
    session_id: str,
    advisor_id: str,
    advisor_name: str,
    store_id: str,
    store_name: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    _ensure_required_columns(connection, "conversation_sessions", CONVERSATION_SESSION_REQUIRED_COLUMNS)
    _ensure_required_columns(connection, "conversation_session_state", SESSION_STATE_REQUIRED_COLUMNS)
    exists = connection.execute(
        "SELECT 1 FROM conversation_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if exists:
        connection.execute(
            "UPDATE conversation_sessions SET advisor_id = ?, advisor_name = ?, store_id = ?, store_name = ?, updated_at = ? WHERE id = ?",
            (advisor_id, advisor_name, store_id, store_name, now, session_id),
        )
    else:
        connection.execute(
            """
            INSERT INTO conversation_sessions (id, advisor_id, advisor_name, store_id, store_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, advisor_id, advisor_name, store_id, store_name, now, now),
        )
    state_exists = connection.execute(
        "SELECT 1 FROM conversation_session_state WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if state_exists:
        connection.execute(
            "UPDATE conversation_session_state SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
    else:
        connection.execute(
            """
            INSERT INTO conversation_session_state (
                session_id, active_customer_id, active_customer_name, active_intent,
                active_product_ids, active_task_ids, last_style_focus, resolution_confidence,
                workflow_name, workflow_stage, last_user_goal, last_response_shape, last_entity_ids,
                conversation_mode, handoff_reason, state_version, working_memory_summary, updated_at
            ) VALUES (?, NULL, '', '', '[]', '[]', '', 'low', '', '', '', '', '[]', '', '', 0, '', ?)
            """,
            (session_id, now),
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


def get_session_state(connection: sqlite3.Connection, session_id: str) -> dict:
    row = connection.execute(
        """
        SELECT session_id, active_customer_id, active_customer_name, active_intent,
               active_product_ids, active_task_ids, last_style_focus, resolution_confidence,
               workflow_name, workflow_stage, last_user_goal, last_response_shape, last_entity_ids,
               conversation_mode, handoff_reason, state_version, working_memory_summary, updated_at
        FROM conversation_session_state
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return {
            "session_id": session_id,
            "active_customer_id": None,
            "active_customer_name": "",
            "active_intent": "",
            "active_product_ids": [],
            "active_task_ids": [],
            "last_style_focus": "",
            "resolution_confidence": "low",
            "workflow_name": "",
            "workflow_stage": "",
            "last_user_goal": "",
            "last_response_shape": "",
            "last_entity_ids": [],
            "conversation_mode": "",
            "handoff_reason": "",
            "state_version": 0,
            "working_memory_summary": "",
            "updated_at": "",
        }

    payload = dict(row)
    payload["active_product_ids"] = json.loads(payload["active_product_ids"] or "[]")
    payload["active_task_ids"] = json.loads(payload["active_task_ids"] or "[]")
    payload["last_entity_ids"] = json.loads(payload["last_entity_ids"] or "[]")
    return payload


def update_session_state(
    connection: sqlite3.Connection,
    session_id: str,
    *,
    active_customer_id: str | None,
    active_customer_name: str = "",
    active_intent: str = "",
    active_product_ids: list[str] | None = None,
    active_task_ids: list[str] | None = None,
    last_style_focus: str = "",
    resolution_confidence: str = "low",
    workflow_name: str = "",
    workflow_stage: str = "",
    last_user_goal: str = "",
    last_response_shape: str = "",
    last_entity_ids: list[str] | None = None,
    conversation_mode: str = "",
    handoff_reason: str = "",
    state_version: int | None = None,
    working_memory_summary: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    current_row = connection.execute(
        "SELECT state_version FROM conversation_session_state WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    next_state_version = int(current_row["state_version"]) if current_row else 0
    if state_version is None:
        next_state_version += 1
    else:
        next_state_version = state_version
    connection.execute(
        """
        UPDATE conversation_session_state
        SET active_customer_id = ?,
            active_customer_name = ?,
            active_intent = ?,
            active_product_ids = ?,
            active_task_ids = ?,
            last_style_focus = ?,
            resolution_confidence = ?,
            workflow_name = ?,
            workflow_stage = ?,
            last_user_goal = ?,
            last_response_shape = ?,
            last_entity_ids = ?,
            conversation_mode = ?,
            handoff_reason = ?,
            state_version = ?,
            working_memory_summary = ?,
            updated_at = ?
        WHERE session_id = ?
        """,
        (
            active_customer_id,
            active_customer_name,
            active_intent,
            json.dumps(active_product_ids or [], ensure_ascii=False),
            json.dumps(active_task_ids or [], ensure_ascii=False),
            last_style_focus,
            resolution_confidence,
            workflow_name,
            workflow_stage,
            last_user_goal,
            last_response_shape,
            json.dumps(last_entity_ids or [], ensure_ascii=False),
            conversation_mode,
            handoff_reason,
            next_state_version,
            working_memory_summary,
            now,
            session_id,
        ),
    )
    connection.commit()


def get_customer_memory_notes(connection: sqlite3.Connection, customer_id: str, limit: int = 4) -> list[dict]:
    rows = connection.execute(
        """
        SELECT note_type, content, source, confidence, pinned, updated_at
        FROM customer_memory_notes
        WHERE customer_id = ?
        ORDER BY pinned DESC, updated_at DESC, id DESC
        LIMIT ?
        """,
        (customer_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_customer_memory_suggestions(
    connection: sqlite3.Connection,
    customer_id: str,
    limit: int = 6,
    session_id: str | None = None,
) -> list[dict]:
    if session_id:
        rows = connection.execute(
            """
            SELECT id, note_type, content, source, source_session_id, confidence, status, updated_at
            FROM customer_memory_suggestions
            WHERE customer_id = ? AND status = 'pending' AND source_session_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (customer_id, session_id, limit),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, note_type, content, source, source_session_id, confidence, status, updated_at
            FROM customer_memory_suggestions
            WHERE customer_id = ? AND status = 'pending'
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (customer_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def add_customer_memory_note(
    connection: sqlite3.Connection,
    customer_id: str,
    note_type: str,
    content: str,
    *,
    source: str,
    confidence: str = "medium",
    pinned: bool = False,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO customer_memory_notes (
            customer_id, note_type, content, source, confidence, pinned, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (customer_id, note_type, content, source, confidence, 1 if pinned else 0, now, now),
    )
    connection.commit()


def add_customer_memory_suggestion(
    connection: sqlite3.Connection,
    customer_id: str,
    note_type: str,
    content: str,
    *,
    source: str,
    source_session_id: str,
    confidence: str = "low",
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    existing = connection.execute(
        """
        SELECT id
        FROM customer_memory_suggestions
        WHERE customer_id = ? AND content = ? AND status = 'pending'
        ORDER BY id DESC
        LIMIT 1
        """,
        (customer_id, content),
    ).fetchone()
    if existing is not None:
        return int(existing["id"])

    cursor = connection.execute(
        """
        INSERT INTO customer_memory_suggestions (
            customer_id, note_type, content, source, source_session_id, confidence, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (customer_id, note_type, content, source, source_session_id, confidence, now, now),
    )
    connection.commit()
    return int(cursor.lastrowid)


def add_customer_memory_fact(
    connection: sqlite3.Connection,
    customer_id: str,
    *,
    dimension: str,
    value: str,
    polarity: str,
    qualifier: str = "",
    source_type: str,
    source_session_id: str = "",
    note_source: str = "",
    status: str = "confirmed",
    confidence: str = "medium",
    confirmed_by: str = "",
    effective_at: str | None = None,
    expires_at: str = "",
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        """
        INSERT INTO customer_memory_facts (
            customer_id, dimension, value, polarity, qualifier, source_type, source_session_id,
            note_source, status, confidence, confirmed_by, effective_at, expires_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_id,
            dimension,
            value,
            polarity,
            qualifier,
            source_type,
            source_session_id,
            note_source,
            status,
            confidence,
            confirmed_by,
            effective_at or now,
            expires_at,
            now,
            now,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_customer_memory_facts(
    connection: sqlite3.Connection,
    customer_id: str,
    *,
    statuses: list[str] | None = None,
    limit: int = 24,
) -> list[dict]:
    if statuses:
        placeholders = ",".join("?" for _ in statuses)
        rows = connection.execute(
            f"""
            SELECT id, customer_id, dimension, value, polarity, qualifier, source_type, source_session_id,
                   note_source, status, confidence, confirmed_by, effective_at, expires_at, updated_at
            FROM customer_memory_facts
            WHERE customer_id = ? AND status IN ({placeholders})
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (customer_id, *statuses, limit),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, customer_id, dimension, value, polarity, qualifier, source_type, source_session_id,
                   note_source, status, confidence, confirmed_by, effective_at, expires_at, updated_at
            FROM customer_memory_facts
            WHERE customer_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (customer_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def update_memory_suggestion_status(
    connection: sqlite3.Connection,
    suggestion_id: int,
    *,
    status: str,
) -> dict | None:
    row = connection.execute(
        """
        SELECT id, customer_id, note_type, content, source, source_session_id, confidence, status
        FROM customer_memory_suggestions
        WHERE id = ?
        """,
        (suggestion_id,),
    ).fetchone()
    if row is None:
        return None

    connection.execute(
        "UPDATE customer_memory_suggestions SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now(timezone.utc).isoformat(), suggestion_id),
    )
    connection.commit()
    return dict(row)


def update_customer_memory_fact_status(
    connection: sqlite3.Connection,
    *,
    customer_id: str,
    note_source: str,
    source_session_id: str = "",
    from_status: str = "pending",
    to_status: str,
    confirmed_by: str = "",
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    if source_session_id:
        cursor = connection.execute(
            """
            UPDATE customer_memory_facts
            SET status = ?,
                confirmed_by = ?,
                updated_at = ?
            WHERE customer_id = ?
              AND note_source = ?
              AND source_session_id = ?
              AND status = ?
            """,
            (to_status, confirmed_by, now, customer_id, note_source, source_session_id, from_status),
        )
    else:
        cursor = connection.execute(
            """
            UPDATE customer_memory_facts
            SET status = ?,
                confirmed_by = ?,
                updated_at = ?
            WHERE customer_id = ?
              AND note_source = ?
              AND status = ?
            """,
            (to_status, confirmed_by, now, customer_id, note_source, from_status),
        )
    connection.commit()
    return int(cursor.rowcount)


def add_audit_event(
    connection: sqlite3.Connection,
    *,
    advisor_id: str,
    store_id: str,
    action_type: str,
    entity_type: str,
    entity_id: str,
    session_id: str = "",
    before_summary: str = "",
    after_summary: str = "",
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO audit_events (
            advisor_id, store_id, action_type, entity_type, entity_id, session_id, before_summary, after_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            advisor_id,
            store_id,
            action_type,
            entity_type,
            entity_id,
            session_id,
            before_summary,
            after_summary,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def find_related_session_ids(
    connection: sqlite3.Connection,
    *,
    customer_id: str = "",
    task_id: str = "",
    session_id: str = "",
) -> list[str]:
    rows = connection.execute(
        """
        SELECT session_id, active_customer_id, active_task_ids
        FROM conversation_session_state
        """
    ).fetchall()
    matched: list[str] = []
    for row in rows:
        state_customer_id = str(row["active_customer_id"] or "")
        active_task_ids = json.loads(row["active_task_ids"] or "[]")
        candidate = str(row["session_id"])
        if session_id and candidate == session_id:
            matched.append(candidate)
            continue
        if customer_id and state_customer_id == customer_id:
            matched.append(candidate)
            continue
        if task_id and task_id in active_task_ids:
            matched.append(candidate)
    return matched


def bump_session_state_versions(connection: sqlite3.Connection, session_ids: list[str]) -> None:
    if not session_ids:
        return
    placeholders = ",".join("?" for _ in session_ids)
    connection.execute(
        f"""
        UPDATE conversation_session_state
        SET state_version = state_version + 1,
            updated_at = ?
        WHERE session_id IN ({placeholders})
        """,
        (datetime.now(timezone.utc).isoformat(), *session_ids),
    )
    connection.commit()


def add_conversation_checkpoint(
    connection: sqlite3.Connection,
    session_id: str,
    *,
    workflow_name: str,
    workflow_stage: str,
    user_goal: str,
    assistant_summary: str,
    focus_customer_id: str = "",
    focus_customer_name: str = "",
    result_summary: str = "",
    next_step: str = "",
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO conversation_checkpoints (
            session_id, workflow_name, workflow_stage, user_goal, assistant_summary,
            focus_customer_id, focus_customer_name, result_summary, next_step, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            workflow_name,
            workflow_stage,
            user_goal,
            assistant_summary,
            focus_customer_id,
            focus_customer_name,
            result_summary,
            next_step,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_conversation_checkpoints(connection: sqlite3.Connection, session_id: str, limit: int = 12) -> list[dict]:
    rows = connection.execute(
        """
        SELECT id, workflow_name, workflow_stage, user_goal, assistant_summary,
               focus_customer_id, focus_customer_name, result_summary, next_step, created_at
        FROM conversation_checkpoints
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def row_to_dict(row: Optional[sqlite3.Row] = None) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)
