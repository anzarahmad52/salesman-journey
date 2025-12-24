# /home/frappe/frappe-bench/apps/salesman_journey/salesman_journey/salesman_journey/report/customer_coverage/customer_coverage.py

from __future__ import annotations

import frappe
from frappe.utils import getdate, flt


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    rows, message, stats = get_data(filters)

    report_summary = build_report_summary(stats)

    # Donut overall
    donut_chart = build_donut_chart(stats)

    # Group chart (Territory/Salesman)
    group_chart = build_group_chart(rows, group_by=(filters.get("group_by") or "Territory"))

    # Combine charts: Frappe accepts ONE chart object. We'll return group chart as main chart,
    # and keep donut in message so user still sees it? Better: keep donut as main, group as secondary?
    #
    # Practically: show GROUP chart as main chart (more useful), and summary shows coverage.
    # If you want donut instead, tell me and I will swap.
    chart = group_chart or donut_chart

    return columns, rows, message, chart, report_summary


def get_columns():
    return [
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 220},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 220},
        {"label": "Territory", "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 160},
        {"label": "Customer Group", "fieldname": "customer_group", "fieldtype": "Link", "options": "Customer Group", "width": 160},
        {"label": "Visited?", "fieldname": "visited", "fieldtype": "Check", "width": 90},
        {"label": "Visits", "fieldname": "visit_count", "fieldtype": "Int", "width": 80},
        {"label": "Last Visit Date", "fieldname": "last_visit_date", "fieldtype": "Date", "width": 110},
        {"label": "Salesman", "fieldname": "salesman", "fieldtype": "Link", "options": "User", "width": 180},
    ]


def get_data(filters: dict):
    """
    Filters supported (from customer_coverage.js):
    - date_from (Date)
    - date_to (Date)
    - salesman (User)
    - territory (Territory)
    - customer_group (Customer Group)
    - show_only_not_visited (Check)
    - group_by (Select: Territory/Salesman)
    """
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    salesman = filters.get("salesman")
    territory = filters.get("territory")
    customer_group = filters.get("customer_group")
    show_only_not_visited = filters.get("show_only_not_visited")

    df = getdate(date_from) if date_from else None
    dt = getdate(date_to) if date_to else None

    # Customer filters
    cust_filters = {"disabled": 0}
    if territory:
        cust_filters["territory"] = territory
    if customer_group:
        cust_filters["customer_group"] = customer_group

    customers = frappe.db.get_all(
        "Customer",
        filters=cust_filters,
        fields=["name", "customer_name", "territory", "customer_group"],
        order_by="name asc",
        limit_page_length=5000,
    )

    if not customers:
        stats = {"total": 0, "visited": 0, "not_visited": 0, "coverage_pct": 0.0}
        return [], "", stats

    # Find visit source doctype + mapping
    visit_conf = _detect_visit_source()
    if not visit_conf:
        rows = []
        for c in customers:
            rows.append({
                "customer": c["name"],
                "customer_name": c.get("customer_name"),
                "territory": c.get("territory"),
                "customer_group": c.get("customer_group"),
                "visited": 0,
                "visit_count": 0,
                "last_visit_date": None,
                "salesman": salesman or "",
            })

        if show_only_not_visited:
            rows = [r for r in rows if not r.get("visited")]

        stats = _compute_stats(rows)
        msg = (
            "Customer Coverage: No visit DocType found. "
            "Expected one of: Sales Visit Log / Visit Plan / Check-in Tracker."
        )
        return rows, msg, stats

    doctype = visit_conf["doctype"]
    customer_field = visit_conf["customer_field"]
    date_field = visit_conf["date_field"]
    salesman_field = visit_conf.get("salesman_field")

    # Build SQL conditions
    cond = ["docstatus < 2"]
    vals = {}

    if df:
        cond.append(f"`{date_field}` >= %(df)s")
        vals["df"] = str(df)

    if dt:
        cond.append(f"`{date_field}` <= %(dt)s")
        vals["dt"] = str(dt)

    if salesman and salesman_field:
        cond.append(f"`{salesman_field}` = %(salesman)s")
        vals["salesman"] = salesman

    where_sql = " AND ".join(cond)

    agg = frappe.db.sql(
        f"""
        SELECT
            `{customer_field}` AS customer,
            COUNT(*) AS visit_count,
            MAX(`{date_field}`) AS last_visit_date,
            {f"MAX(`{salesman_field}`) AS salesman" if salesman_field else "'' AS salesman"}
        FROM `tab{doctype}`
        WHERE {where_sql}
          AND `{customer_field}` IS NOT NULL
          AND `{customer_field}` != ''
        GROUP BY `{customer_field}`
        """,
        vals,
        as_dict=True,
    )

    agg_map = {row["customer"]: row for row in (agg or [])}

    rows = []
    for c in customers:
        row = agg_map.get(c["name"])
        visited = 1 if row else 0

        rows.append({
            "customer": c["name"],
            "customer_name": c.get("customer_name"),
            "territory": c.get("territory"),
            "customer_group": c.get("customer_group"),
            "visited": visited,
            "visit_count": int(row.get("visit_count")) if row else 0,
            "last_visit_date": row.get("last_visit_date") if row else None,
            "salesman": row.get("salesman") if row and row.get("salesman") else (salesman or ""),
        })

    if show_only_not_visited:
        rows = [r for r in rows if not r.get("visited")]

    stats = _compute_stats(rows)
    msg = f"Source: {doctype}"
    return rows, msg, stats


def _compute_stats(rows: list[dict]) -> dict:
    total = len(rows)
    visited = sum(1 for r in rows if r.get("visited"))
    not_visited = total - visited
    coverage_pct = (flt(visited) / flt(total) * 100.0) if total else 0.0
    return {
        "total": int(total),
        "visited": int(visited),
        "not_visited": int(not_visited),
        "coverage_pct": float(coverage_pct),
    }


def build_report_summary(stats: dict) -> list[dict]:
    total = stats.get("total", 0)
    visited = stats.get("visited", 0)
    not_visited = stats.get("not_visited", 0)
    coverage_pct = stats.get("coverage_pct", 0.0)

    if coverage_pct >= 80:
        cov_indicator = "green"
    elif coverage_pct >= 50:
        cov_indicator = "orange"
    else:
        cov_indicator = "red"

    return [
        {"label": "Total Customers", "value": total, "indicator": "blue", "datatype": "Int"},
        {"label": "Visited", "value": visited, "indicator": "green", "datatype": "Int"},
        {"label": "Not Visited", "value": not_visited, "indicator": "red", "datatype": "Int"},
        {"label": "Coverage %", "value": round(coverage_pct, 2), "indicator": cov_indicator, "datatype": "Percent"},
    ]


def build_donut_chart(stats: dict) -> dict:
    visited = stats.get("visited", 0)
    not_visited = stats.get("not_visited", 0)

    return {
        "data": {
            "labels": ["Visited", "Not Visited"],
            "datasets": [{"name": "Customers", "values": [visited, not_visited]}],
        },
        "type": "donut",
        "height": 250,
    }


def build_group_chart(rows: list[dict], group_by: str = "Territory") -> dict | None:
    """
    Bar chart grouped by:
    - Territory (row.territory)
    - Salesman (row.salesman)
    """
    if not rows:
        return None

    key_name = "territory" if (group_by or "").lower().startswith("terr") else "salesman"

    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        k = (r.get(key_name) or "Not Set").strip() if isinstance(r.get(key_name), str) else (r.get(key_name) or "Not Set")
        if k not in buckets:
            buckets[k] = {"visited": 0, "not_visited": 0}
        if r.get("visited"):
            buckets[k]["visited"] += 1
        else:
            buckets[k]["not_visited"] += 1

    # Sort labels by total desc
    labels = sorted(buckets.keys(), key=lambda x: (buckets[x]["visited"] + buckets[x]["not_visited"]), reverse=True)

    visited_values = [buckets[l]["visited"] for l in labels]
    not_visited_values = [buckets[l]["not_visited"] for l in labels]

    return {
        "data": {
            "labels": labels[:25],  # keep chart readable (top 25 groups)
            "datasets": [
                {"name": "Visited", "values": visited_values[:25]},
                {"name": "Not Visited", "values": not_visited_values[:25]},
            ],
        },
        "type": "bar",
        "height": 300,
        "colors": None,  # let Frappe handle default colors
        "barOptions": {"stacked": 1},
    }


def _has_field(meta, fieldname: str) -> bool:
    if not fieldname:
        return False

    if hasattr(meta, "has_field") and meta.has_field(fieldname):
        return True

    for df in (meta.get("fields") or []):
        if (df.get("fieldname") or "") == fieldname:
            return True

    return False


def _detect_visit_source() -> dict | None:
    candidates = [
        ("Sales Visit Log", "customer", "visit_date", "salesman"),
        ("Sales Visit Log", "customer", "posting_date", "salesman"),
        ("Sales Visit Log", "customer", "date", "salesman"),

        ("Visit Plan", "customer", "visit_date", "salesman"),
        ("Visit Plan", "customer", "date", "salesman"),

        ("Check-in Tracker", "customer", "checkin_time", "user"),
        ("Check-in Tracker", "customer", "creation", "owner"),
    ]

    for dt, cfield, dfield, sfield in candidates:
        if not frappe.db.exists("DocType", dt):
            continue

        meta = frappe.get_meta(dt)

        if not _has_field(meta, cfield):
            continue
        if not _has_field(meta, dfield):
            continue

        salesman_field = sfield if _has_field(meta, sfield) else None

        return {
            "doctype": dt,
            "customer_field": cfield,
            "date_field": dfield,
            "salesman_field": salesman_field,
        }

    return None
