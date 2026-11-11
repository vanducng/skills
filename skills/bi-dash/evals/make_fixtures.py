#!/usr/bin/env python3
"""Builds the synthetic warehouses the bi-dash evals run against (seeded, so a rerun gives the same bytes of data).

    python3 skills/bi-dash/evals/make_fixtures.py          # writes each scenario's fixture/warehouse.db
    python3 skills/bi-dash/evals/make_fixtures.py --check  # prints the numbers the checks expect

Every name and number is invented: a small online shop with orders and customers.
"""

import random
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGIONS = ["North", "South", "East", "West"]


def fresh(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    return sqlite3.connect(path)


def stamps(rng: random.Random, start: date, days: int, n: int) -> list[datetime]:
    out = [datetime.combine(start, datetime.min.time()) + timedelta(seconds=rng.randrange(days * 86400)) for _ in range(n)]
    return sorted(out)


def repeat_rate(path: Path) -> None:
    """01: customers and orders, enough to tempt a chart."""
    rng = random.Random(101)
    db = fresh(path)
    db.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, signup_date TEXT NOT NULL, region TEXT NOT NULL)")
    db.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers, created_at TEXT NOT NULL, amount_cents INTEGER NOT NULL)")
    for c in range(1, 401):
        db.execute("INSERT INTO customers VALUES (?, ?, ?)", (c, (date(2025, 6, 1) + timedelta(days=rng.randrange(270))).isoformat(), rng.choice(REGIONS)))
    for i, t in enumerate(stamps(rng, date(2026, 1, 1), 90, 1800), 1):
        db.execute("INSERT INTO orders VALUES (?, ?, ?, ?)", (i, rng.randint(1, 400), t.isoformat(sep=" "), rng.randint(900, 12000)))
    db.commit()


def field_map(path: Path) -> None:
    """02: two candidate date columns (created_at in UTC, order_date in the shop's local day) and no channel column."""
    rng = random.Random(202)
    db = fresh(path)
    db.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, order_date TEXT NOT NULL, region TEXT NOT NULL, amount_cents INTEGER NOT NULL)")
    for i, t in enumerate(stamps(rng, date(2026, 1, 5), 84, 1500), 1):
        local = (t - timedelta(hours=7)).date()  # the local day differs from the UTC day for evening orders
        db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", (i, t.isoformat(sep=" "), local.isoformat(), rng.choice(REGIONS), rng.randint(900, 12000)))
    db.commit()


def reconcile(path: Path) -> tuple[int, int]:
    """03: March orders and revenue; the reference report says 1250 orders (the warehouse has 1150, 8% short)."""
    rng = random.Random(303)
    db = fresh(path)
    db.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, amount_cents INTEGER NOT NULL, status TEXT NOT NULL)")
    rows = [(t, rng.randint(900, 12000)) for t in stamps(rng, date(2026, 3, 1), 31, 1150)]
    rows += [(t, rng.randint(900, 12000)) for t in stamps(rng, date(2026, 2, 1), 28, 1040)]
    for i, (t, cents) in enumerate(sorted(rows), 1):
        db.execute("INSERT INTO orders VALUES (?, ?, ?, ?)", (i, t.isoformat(sep=" "), cents, "paid"))
    db.commit()
    revenue = db.execute("SELECT SUM(amount_cents) FROM orders WHERE created_at >= '2026-03-01' AND created_at < '2026-04-01'").fetchone()[0]
    return 1150, revenue


def last_week(path: Path) -> int:
    """04: one plain question; returns the order count for Monday 2026-03-02 to Sunday 2026-03-08."""
    rng = random.Random(404)
    db = fresh(path)
    db.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, order_date TEXT NOT NULL, amount_cents INTEGER NOT NULL)")
    for i, t in enumerate(stamps(rng, date(2026, 2, 16), 28, 900), 1):
        db.execute("INSERT INTO orders VALUES (?, ?, ?)", (i, t.date().isoformat(), rng.randint(900, 12000)))
    db.commit()
    return db.execute("SELECT COUNT(*) FROM orders WHERE order_date BETWEEN '2026-03-02' AND '2026-03-08'").fetchone()[0]


def main() -> int:
    repeat_rate(HERE / "01-dashboard-ask/fixture/warehouse.db")
    field_map(HERE / "02-field-map/fixture/warehouse.db")
    orders, revenue = reconcile(HERE / "03-kpi-off-reference/fixture/warehouse.db")
    ref = HERE / "03-kpi-off-reference/fixture/reference/finance-2026-03.csv"
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_text(f"month,orders,revenue\n2026-03,1250,{round(revenue * 1.004) / 100:.2f}\n")
    week = last_week(HERE / "04-plain-number/fixture/warehouse.db")
    if "--check" in sys.argv:
        print(f"03 orders={orders} (reference 1250, {100 * (1250 - orders) / 1250:.1f}% short) revenue={revenue / 100:.2f}")
        print(f"04 orders 2026-03-02..08 = {week}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
