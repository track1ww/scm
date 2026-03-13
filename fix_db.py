# -*- coding: utf-8 -*-
"""
MySQL scm_db — item_code 누락 컬럼 및 관련 인덱스 추가 마이그레이션
실행: python fix_mysql_item_code.py
"""
import os
import pymysql

DB_CONFIG = dict(
    host     = os.environ.get("SCM_DB_HOST", "localhost"),
    port     = int(os.environ.get("SCM_DB_PORT", 3306)),
    user     = os.environ.get("SCM_DB_USER", "scm_user"),
    password = os.environ.get("SCM_DB_PASS", "scm1234"),
    database = os.environ.get("SCM_DB_NAME", "scm_db"),
    charset  = "utf8mb4",
    cursorclass = pymysql.cursors.DictCursor,
)

def col_exists(cur, table, col):
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = %s
          AND COLUMN_NAME  = %s
    """, (table, col))
    return cur.fetchone()["cnt"] > 0

def add_col(cur, table, col, definition):
    if col_exists(cur, table, col):
        print(f"  ↩️  {table}.{col} — 이미 존재, 스킵")
    else:
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {definition}")
        print(f"  ✅ {table}.{col} 추가 완료")

def main():
    conn = pymysql.connect(**DB_CONFIG)
    cur  = conn.cursor()
    print("=" * 55)
    print("MySQL scm_db 마이그레이션 시작")
    print("=" * 55)

    # ── 1) inventory.item_code ─────────────────────────────
    # db.py 스키마에 있지만 이전에 생성된 테이블에 없을 수 있음
    print("\n[inventory]")
    add_col(cur, "inventory", "item_code",     "VARCHAR(100)")
    add_col(cur, "inventory", "lot_number",    "VARCHAR(100)")
    add_col(cur, "inventory", "expiry_date",   "DATE")
    add_col(cur, "inventory", "serial_number", "VARCHAR(100)")
    add_col(cur, "inventory", "system_qty",    "INT DEFAULT 0")
    add_col(cur, "inventory", "min_stock",     "INT DEFAULT 0")

    # item_code 기존 데이터 보정: NULL이면 item_name 으로 채움
    cur.execute("""
        UPDATE inventory SET item_code = item_name
        WHERE item_code IS NULL OR item_code = ''
    """)
    print(f"  🔧 inventory.item_code NULL → item_name 으로 보정: {cur.rowcount}건")

    # ── 2) stock_movements.item_code ──────────────────────
    print("\n[stock_movements]")
    add_col(cur, "stock_movements", "item_code",  "VARCHAR(100)")
    add_col(cur, "stock_movements", "warehouse",  "VARCHAR(100)")
    add_col(cur, "stock_movements", "lot_number", "VARCHAR(100)")

    # item_code NULL → item_name 보정
    cur.execute("""
        UPDATE stock_movements SET item_code = item_name
        WHERE item_code IS NULL OR item_code = ''
    """)
    print(f"  🔧 stock_movements.item_code NULL → item_name 으로 보정: {cur.rowcount}건")

    # ── 3) moving_avg_price ───────────────────────────────
    print("\n[moving_avg_price]")
    add_col(cur, "moving_avg_price", "item_code", "VARCHAR(100)")

    cur.execute("""
        UPDATE moving_avg_price SET item_code = item_name
        WHERE item_code IS NULL OR item_code = ''
    """)
    print(f"  🔧 moving_avg_price.item_code NULL → item_name 으로 보정: {cur.rowcount}건")

    # ── 4) 인덱스 추가 (없으면) ──────────────────────────
    print("\n[인덱스]")
    def add_index(table, idx_name, col):
        try:
            cur.execute(f"CREATE INDEX `{idx_name}` ON `{table}`(`{col}`)")
            print(f"  ✅ INDEX {idx_name} 추가")
        except pymysql.err.OperationalError as e:
            if "Duplicate key name" in str(e):
                print(f"  ↩️  INDEX {idx_name} — 이미 존재")
            else:
                print(f"  ⚠️  {e}")

    add_index("inventory",        "idx_inv_item_code",  "item_code")
    add_index("stock_movements",  "idx_sm_item_code",   "item_code")
    add_index("moving_avg_price", "idx_map_item_code",  "item_code")

    conn.commit()
    cur.close()
    conn.close()

    print("\n" + "=" * 55)
    print("✅ 마이그레이션 완료!")
    print("=" * 55)

if __name__ == "__main__":
    main()
