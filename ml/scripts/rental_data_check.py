"""
One-off script — run to understand the rental training data before Phase 1.
Usage: python ml/scripts/rental_data_check.py
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv("DATABASE_URL"))
RENTAL_CLASSES = ("07 RENTALS - WALKUP APARTMENTS", "08 RENTALS - ELEVATOR APARTMENTS")

with engine.connect() as conn:

    # ── 1. Raw row counts ────────────────────────────────────────────────────
    print("=== 1. Raw rental rows (no filters) ===")
    rows = conn.execute(text("""
        SELECT building_class, COUNT(*) AS cnt
        FROM housing_data
        WHERE building_class IN (
            '07 RENTALS - WALKUP APARTMENTS',
            '08 RENTALS - ELEVATOR APARTMENTS'
        )
        GROUP BY building_class
        ORDER BY building_class
    """)).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]:,}")

    # ── 2. After pipeline filters ────────────────────────────────────────────
    print("\n=== 2. After pipeline filters (price>1000, year_built, lat/lng, gross_sqft>0) ===")
    rows = conn.execute(text("""
        SELECT building_class, COUNT(*) AS cnt
        FROM housing_data
        WHERE building_class IN (
            '07 RENTALS - WALKUP APARTMENTS',
            '08 RENTALS - ELEVATOR APARTMENTS'
        )
          AND CAST(sales_price AS NUMERIC) > 1000
          AND year_built IS NOT NULL
          AND CAST(year_built AS NUMERIC) BETWEEN 1800 AND 2025
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND gross_sqft IS NOT NULL
          AND CAST(gross_sqft AS NUMERIC) > 0
        GROUP BY building_class
        ORDER BY building_class
    """)).fetchall()
    total = 0
    for r in rows:
        print(f"  {r[0]}: {r[1]:,}")
        total += r[1]
    print(f"  TOTAL: {total:,}")

    # ── 3. total_units coverage ──────────────────────────────────────────────
    print("\n=== 3. total_units availability (within filtered set) ===")
    rows = conn.execute(text("""
        SELECT
            building_class,
            COUNT(*) AS total,
            SUM(CASE WHEN total_units IS NOT NULL
                      AND CAST(total_units AS NUMERIC) > 0 THEN 1 ELSE 0 END) AS has_units,
            ROUND(AVG(CASE WHEN total_units IS NOT NULL
                           AND CAST(total_units AS NUMERIC) > 0
                      THEN CAST(total_units AS NUMERIC) END)::NUMERIC, 1) AS avg_units,
            MIN(CASE WHEN total_units IS NOT NULL
                      AND CAST(total_units AS NUMERIC) > 0
                 THEN CAST(total_units AS NUMERIC) END) AS min_units,
            MAX(CASE WHEN total_units IS NOT NULL
                      AND CAST(total_units AS NUMERIC) > 0
                 THEN CAST(total_units AS NUMERIC) END) AS max_units
        FROM housing_data
        WHERE building_class IN (
            '07 RENTALS - WALKUP APARTMENTS',
            '08 RENTALS - ELEVATOR APARTMENTS'
        )
          AND CAST(sales_price AS NUMERIC) > 1000
          AND year_built IS NOT NULL
          AND CAST(year_built AS NUMERIC) BETWEEN 1800 AND 2025
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND gross_sqft IS NOT NULL
          AND CAST(gross_sqft AS NUMERIC) > 0
        GROUP BY building_class
        ORDER BY building_class
    """)).fetchall()
    for r in rows:
        pct = (r[2] / r[1] * 100) if r[1] else 0
        print(f"  {r[0]}")
        print(f"    rows: {r[1]:,}  |  has total_units>0: {r[2]:,} ({pct:.0f}%)")
        print(f"    units — avg: {r[3]}, min: {r[4]}, max: {r[5]}")

    # ── 4. Sales price distribution ──────────────────────────────────────────
    print("\n=== 4. Sales price distribution (\$) ===")
    rows = conn.execute(text("""
        SELECT
            building_class,
            ROUND(PERCENTILE_CONT(0.05) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC))::NUMERIC, 0) AS p5,
            ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC))::NUMERIC, 0) AS p25,
            ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC))::NUMERIC, 0) AS median,
            ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC))::NUMERIC, 0) AS p75,
            ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC))::NUMERIC, 0) AS p95,
            ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC))::NUMERIC, 0) AS p99
        FROM housing_data
        WHERE building_class IN (
            '07 RENTALS - WALKUP APARTMENTS',
            '08 RENTALS - ELEVATOR APARTMENTS'
        )
          AND CAST(sales_price AS NUMERIC) > 1000
          AND year_built IS NOT NULL
          AND latitude IS NOT NULL
          AND gross_sqft IS NOT NULL
          AND CAST(gross_sqft AS NUMERIC) > 0
        GROUP BY building_class
        ORDER BY building_class
    """)).fetchall()
    for r in rows:
        print(f"  {r[0]}")
        print(f"    p5=${r[1]:,.0f}  p25=${r[2]:,.0f}  median=${r[3]:,.0f}  p75=${r[4]:,.0f}  p95=${r[5]:,.0f}  p99=${r[6]:,.0f}")

    # ── 5. Price-per-unit distribution ───────────────────────────────────────
    print("\n=== 5. Price-per-unit distribution (\$/unit, where total_units > 0) ===")
    rows = conn.execute(text("""
        SELECT
            building_class,
            ROUND(PERCENTILE_CONT(0.05) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC) /
                            NULLIF(CAST(total_units AS NUMERIC), 0))::NUMERIC, 0) AS p5,
            ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC) /
                            NULLIF(CAST(total_units AS NUMERIC), 0))::NUMERIC, 0) AS p25,
            ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC) /
                            NULLIF(CAST(total_units AS NUMERIC), 0))::NUMERIC, 0) AS median,
            ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC) /
                            NULLIF(CAST(total_units AS NUMERIC), 0))::NUMERIC, 0) AS p75,
            ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP
                  (ORDER BY CAST(sales_price AS NUMERIC) /
                            NULLIF(CAST(total_units AS NUMERIC), 0))::NUMERIC, 0) AS p95
        FROM housing_data
        WHERE building_class IN (
            '07 RENTALS - WALKUP APARTMENTS',
            '08 RENTALS - ELEVATOR APARTMENTS'
        )
          AND CAST(sales_price AS NUMERIC) > 1000
          AND total_units IS NOT NULL
          AND CAST(total_units AS NUMERIC) > 0
          AND year_built IS NOT NULL
          AND latitude IS NOT NULL
          AND gross_sqft IS NOT NULL
          AND CAST(gross_sqft AS NUMERIC) > 0
        GROUP BY building_class
        ORDER BY building_class
    """)).fetchall()
    for r in rows:
        print(f"  {r[0]}")
        print(f"    p5=${r[1]:,.0f}  p25=${r[2]:,.0f}  median=${r[3]:,.0f}  p75=${r[4]:,.0f}  p95=${r[5]:,.0f}")

    # ── 6. Borough breakdown ─────────────────────────────────────────────────
    print("\n=== 6. Borough breakdown (filtered set) ===")
    rows = conn.execute(text("""
        SELECT borough, building_class, COUNT(*) AS cnt
        FROM housing_data
        WHERE building_class IN (
            '07 RENTALS - WALKUP APARTMENTS',
            '08 RENTALS - ELEVATOR APARTMENTS'
        )
          AND CAST(sales_price AS NUMERIC) > 1000
          AND year_built IS NOT NULL
          AND latitude IS NOT NULL
          AND gross_sqft IS NOT NULL
          AND CAST(gross_sqft AS NUMERIC) > 0
        GROUP BY borough, building_class
        ORDER BY building_class, cnt DESC
    """)).fetchall()
    for r in rows:
        tag = "WU" if "WALKUP" in r[1] else "EL"
        print(f"  [{tag}] {r[0]}: {r[2]:,}")

    # ── 7. Rows that survive a 95th percentile cap within rental only ────────
    print("\n=== 7. Rows surviving a rental-only 95th pct cap ===")
    rows = conn.execute(text("""
        WITH base AS (
            SELECT building_class,
                   CAST(sales_price AS NUMERIC) AS sp,
                   PERCENTILE_CONT(0.95) WITHIN GROUP
                       (ORDER BY CAST(sales_price AS NUMERIC))
                       OVER (PARTITION BY building_class) AS p95
            FROM housing_data
            WHERE building_class IN (
                '07 RENTALS - WALKUP APARTMENTS',
                '08 RENTALS - ELEVATOR APARTMENTS'
            )
              AND CAST(sales_price AS NUMERIC) > 1000
              AND year_built IS NOT NULL
              AND latitude IS NOT NULL
              AND gross_sqft IS NOT NULL
              AND CAST(gross_sqft AS NUMERIC) > 0
        )
        SELECT building_class, COUNT(*) AS cnt
        FROM base
        WHERE sp <= p95
        GROUP BY building_class
        ORDER BY building_class
    """)).fetchall()
    total = 0
    for r in rows:
        print(f"  {r[0]}: {r[1]:,}")
        total += r[1]
    print(f"  TOTAL after per-class 95th cap: {total:,}")
