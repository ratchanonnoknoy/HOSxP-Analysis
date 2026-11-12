import argparse

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ============================================================
# 1) ตั้งค่า (แก้ตรงนี้ได้เลย)
# ============================================================
DB_NAME = "hos"
DEFAULT_TABLE = "patient"

# ฟิลด์ที่ใช้ join ตารางบ่อยๆ ใน HOSxP จะถูกไฮไลต์สีม่วง
JOIN_KEYS = {"hn", "vn", "an", "cid", "icode", "pttype", "hcode",
             "doctor", "depcode", "ward", "spclty", "regdate", "vstdate"}

# ป้ายและสีของคอลัมน์ Key
KEY_LABELS = {
    "PRI": ("🔑 PK", "bold yellow"),   # Primary Key
    "UNI": ("◆ UNI", "bold magenta"),  # Unique
    "MUL": ("◇ IDX", "cyan"),          # Index ธรรมดา
}

engine = create_engine(
    URL.create(
        "mysql+pymysql",
        username="root",
        password="",
        host="127.0.0.1",
        port=3306,
        database=DB_NAME,
    )
)
console = Console()


# ============================================================
# 2) ฟังก์ชันดึงข้อมูลจากฐานข้อมูล
# ============================================================
def run_query(sql, **params):
    """รัน SQL แล้วคืนผลเป็น DataFrame (ใส่ชื่อฐานข้อมูลให้อัตโนมัติ)"""
    return pd.read_sql(text(sql), engine, params={"db": DB_NAME, **params})


def get_columns(table_name):
    """ดึงรายชื่อคอลัมน์ทั้งหมดของตาราง"""
    return run_query(
        """
        SELECT ORDINAL_POSITION AS position,
               COLUMN_NAME      AS field,
               COLUMN_TYPE      AS data_type,
               IS_NULLABLE      AS nullable,
               COLUMN_KEY       AS key_type,
               COLUMN_COMMENT   AS comment
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table_name
        ORDER BY ORDINAL_POSITION
        """,
        table_name=table_name,
    )


def get_row_count_text(table_name):
    """ดึงจำนวนแถวโดยประมาณ (เร็วกว่า COUNT(*) มาก)"""
    result = run_query(
        """
        SELECT TABLE_ROWS AS total_rows
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table_name
        """,
        table_name=table_name,
    )
    if result.empty or pd.isna(result["total_rows"][0]):
        return "ไม่ทราบจำนวนแถว"
    return f"~{int(result['total_rows'][0]):,} แถว"


def get_indexes(table_name):
    """ดึงรายการ Index ของตาราง"""
    return run_query(
        """
        SELECT INDEX_NAME AS index_name,
               NON_UNIQUE AS non_unique,
               GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS columns
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table_name
        GROUP BY INDEX_NAME, NON_UNIQUE
        ORDER BY INDEX_NAME = 'PRIMARY' DESC, INDEX_NAME
        """,
        table_name=table_name,
    )


def find_similar_tables(keyword):
    """ค้นหาตารางที่ชื่อมีคำนี้อยู่ (ใช้ตอนพิมพ์ชื่อตารางผิด)"""
    result = run_query(
        """
        SELECT TABLE_NAME AS name
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME LIKE :keyword
        LIMIT 50
        """,
        keyword=f"%{keyword}%",
    )
    return result["name"].tolist()


def get_sample_values(table_name, rows_to_scan=500):
    """
    ดึงค่าตัวอย่างของแต่ละคอลัมน์ โดยหาค่าแรกที่ 'ไม่ว่าง'
    จาก 500 แถวแรกของตาราง
    """
    df = pd.read_sql(text(f"SELECT * FROM `{table_name}` LIMIT {rows_to_scan}"), engine)
    samples = {}

    for column in df.columns:
        values = df[column].dropna()                      # ตัดค่า NULL
        values = values[values.astype(str).str.strip() != ""]  # ตัดค่าว่าง
        first_value = values.iloc[0] if len(values) > 0 else ""

        if isinstance(first_value, (bytes, bytearray)):
            samples[column] = "<binary>"
        else:
            samples[column] = str(first_value).replace("\n", " ")[:28]

    return samples, len(df)


# ============================================================
# 3) ฟังก์ชันแสดงผลสวยๆ
# ============================================================
def pick_field_style(field, key_type):
    """เลือกสีชื่อฟิลด์: PK = เหลือง, คีย์ join = ม่วง, อื่นๆ = เขียว"""
    if key_type == "PRI":
        return "bold yellow"
    if field.lower() in JOIN_KEYS:
        return "bold magenta"
    return "green"


def build_table(table_name, columns, samples, sample_count, show_sample):
    """สร้างตารางสำหรับแสดงโครงสร้าง"""
    caption = f"{len(columns)} คอลัมน์"
    if show_sample:
        caption += f" • sample จาก {sample_count} แถวแรก"

    table = Table(
        title=f"📋 [bold cyan]{table_name}[/bold cyan] [dim]({get_row_count_text(table_name)})[/dim]",
        box=box.SIMPLE_HEAD,
        header_style="bold white on dark_blue",
        row_styles=["", "on grey15"],  # แถวสลับสี
        caption=caption,
    )

    # หัวคอลัมน์
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Field", no_wrap=True)
    table.add_column("Type", style="cyan", max_width=22, overflow="fold")
    table.add_column("Key", justify="center", no_wrap=True)
    table.add_column("Null", justify="center", no_wrap=True)
    if show_sample:
        table.add_column("Sample", max_width=30, overflow="fold")
    table.add_column("Comment", style="italic yellow", overflow="fold")

    # ใส่ข้อมูลทีละแถว
    for col in columns.itertuples(index=False):
        key_label, key_style = KEY_LABELS.get(col.key_type, ("", ""))
        null_text = Text("•", style="dim") if col.nullable == "YES" else Text("NOT NULL", style="bold red")

        row = [
            str(col.position),
            Text(col.field, style=pick_field_style(col.field, col.key_type)),
            Text(col.data_type),
            Text(key_label, style=key_style),
            null_text,
        ]

        if show_sample:
            sample = samples.get(col.field, "")
            row.append(Text(sample, style="") if sample else Text("-", style="dim"))

        row.append(Text(col.comment or ""))
        table.add_row(*row)

    return table


def print_indexes(table_name):
    """แสดงรายการ Index ใต้ตาราง"""
    for idx in get_indexes(table_name).itertuples(index=False):
        if idx.index_name == "PRIMARY":
            tag = "[yellow]PRIMARY[/yellow]"
        elif idx.non_unique == 0:
            tag = "[magenta]UNIQUE[/magenta]"
        else:
            tag = "[cyan]INDEX[/cyan]"
        console.print(f"  {tag} [bold]{idx.index_name}[/bold] → ({idx.columns})")


# ============================================================
# 4) ฟังก์ชันหลัก
# ============================================================
def describe_table(table_name, show_sample):
    columns = get_columns(table_name)

    # ถ้าไม่พบตาราง ให้แนะนำชื่อใกล้เคียง
    if columns.empty:
        console.print(f"[yellow]ไม่พบตาราง[/yellow] [bold]{table_name}[/bold]")
        similar = find_similar_tables(table_name)
        if similar:
            console.print("[dim]ตารางที่ชื่อคล้ายกัน:[/dim] " + ", ".join(f"[cyan]{n}[/cyan]" for n in similar))
        return

    samples, sample_count = get_sample_values(table_name) if show_sample else ({}, 0)

    console.print()
    console.print(build_table(table_name, columns, samples, sample_count, show_sample))
    print_indexes(table_name)
    console.print("\n[dim]สี: 🟨 PK  🟪 คีย์ join (hn/vn/an/...)  🟩 ฟิลด์ทั่วไป[/dim]\n")


def main():
    parser = argparse.ArgumentParser(description="แกะโครงสร้างตาราง HOSxP")
    parser.add_argument("table", nargs="?", default=DEFAULT_TABLE, help="ชื่อตาราง")
    parser.add_argument("--no-sample", action="store_true",
                        help="ไม่แสดงค่าตัวอย่าง (กันข้อมูลผู้ป่วยโชว์บนจอ)")
    args = parser.parse_args()

    try:
        describe_table(args.table, show_sample=not args.no_sample)
    except Exception as error:
        console.print(f"[red]เกิดข้อผิดพลาด:[/red] {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
