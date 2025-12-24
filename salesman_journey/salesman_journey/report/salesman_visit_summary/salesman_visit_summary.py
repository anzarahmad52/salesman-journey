import frappe
from frappe.utils import getdate, nowdate


def execute(filters=None):
    filters = filters or {}

    from_date = getdate(filters.get("from_date") or nowdate())
    to_date = getdate(filters.get("to_date") or nowdate())

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    salesman = filters.get("salesman")
    journey_plan = filters.get("journey_plan")
    poor_accuracy_threshold = float(filters.get("poor_accuracy_threshold") or 50)

    columns = get_columns()
    data = get_data(from_date, to_date, salesman, journey_plan, poor_accuracy_threshold)
    chart = get_chart(data)

    return columns, data, None, chart


def get_columns():
    return [
        {"label": "Salesman", "fieldname": "salesman", "fieldtype": "Link", "options": "User", "width": 200},

        {"label": "Planned", "fieldname": "planned_visits", "fieldtype": "Int", "width": 95},
        {"label": "Attempted", "fieldname": "attempted_visits", "fieldtype": "Int", "width": 105},
        {"label": "Completed", "fieldname": "completed_visits", "fieldtype": "Int", "width": 105},
        {"label": "Missed", "fieldname": "missed_visits", "fieldtype": "Int", "width": 95},
        {"label": "Completion %", "fieldname": "completion_pct", "fieldtype": "Percent", "width": 120},

        {"label": "Total Duration (Min)", "fieldname": "total_duration_min", "fieldtype": "Int", "width": 155},
        {"label": "Avg Duration (Min)", "fieldname": "avg_duration_min", "fieldtype": "Float", "width": 145},

        {"label": "Avg Accuracy (m)", "fieldname": "avg_accuracy_m", "fieldtype": "Float", "width": 135},
        {"label": "Poor Accuracy", "fieldname": "poor_accuracy_visits", "fieldtype": "Int", "width": 120},

        {"label": "First Check-in", "fieldname": "first_check_in", "fieldtype": "Datetime", "width": 160},
        {"label": "Last Check-out", "fieldname": "last_check_out", "fieldtype": "Datetime", "width": 160}
    ]


def _duration_minutes(in_time, out_time):
    if not in_time or not out_time:
        return None
    try:
        dt_in = frappe.utils.get_datetime(in_time)
        dt_out = frappe.utils.get_datetime(out_time)
        return int((dt_out - dt_in).total_seconds() // 60)
    except Exception:
        return None


def get_data(from_date, to_date, salesman=None, journey_plan=None, poor_accuracy_threshold=50.0):
    # -------------------
    # Planned (SVL)
    # -------------------
    svl_filters = [["visit_date", "between", [from_date, to_date]]]
    if salesman:
        svl_filters.append(["salesman", "=", salesman])
    if journey_plan:
        svl_filters.append(["journey_plan", "=", journey_plan])

    planned_rows = frappe.get_all(
        "Sales Visit Log",
        filters=svl_filters,
        fields=["salesman", "name"],
        limit_page_length=999999
    )

    planned_by_salesman = {}
    for r in planned_rows:
        planned_by_salesman[r.salesman] = planned_by_salesman.get(r.salesman, 0) + 1

    # -------------------
    # Actual (Check-in Tracker)
    # -------------------
    conditions = ["docstatus < 2", "date(check_in_time) between %(from_date)s and %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if salesman:
        conditions.append("salesman = %(salesman)s")
        params["salesman"] = salesman

    # Note: Journey plan isn't stored in tracker by default.
    # We still allow filtering by journey_plan via planned visits only.
    # If you want strict journey_plan filter in actual too, we can add a custom field later.

    cit_rows = frappe.db.sql(
        f"""
        select
            salesman,
            check_in_time,
            check_out_time,
            location_accuracy
        from `tabCheck-in Tracker`
        where {" and ".join(conditions)}
        """,
        params,
        as_dict=True,
    )

    agg = {}
    for c in cit_rows:
        s = c.get("salesman")
        if not s:
            continue

        a = agg.setdefault(s, {
            "attempted_visits": 0,
            "completed_visits": 0,
            "total_duration_min": 0,
            "dur_count": 0,
            "acc_sum": 0.0,
            "acc_count": 0,
            "poor_accuracy_visits": 0,
            "first_check_in": None,
            "last_check_out": None,
        })

        cin = c.get("check_in_time")
        cout = c.get("check_out_time")

        if cin:
            a["attempted_visits"] += 1
            if not a["first_check_in"] or frappe.utils.get_datetime(cin) < frappe.utils.get_datetime(a["first_check_in"]):
                a["first_check_in"] = cin

        if cout:
            a["completed_visits"] += 1
            if not a["last_check_out"] or frappe.utils.get_datetime(cout) > frappe.utils.get_datetime(a["last_check_out"]):
                a["last_check_out"] = cout

        dur = _duration_minutes(cin, cout)
        if dur is not None:
            a["total_duration_min"] += dur
            a["dur_count"] += 1

        acc = c.get("location_accuracy")
        if acc is not None:
            try:
                acc_f = float(acc)
                a["acc_sum"] += acc_f
                a["acc_count"] += 1
                if acc_f > float(poor_accuracy_threshold):
                    a["poor_accuracy_visits"] += 1
            except Exception:
                pass

    # -------------------
    # Merge & Calculate
    # -------------------
    salesmen = set(planned_by_salesman.keys()) | set(agg.keys())
    out = []

    for s in sorted(salesmen):
        planned = int(planned_by_salesman.get(s, 0))
        attempted = int(agg.get(s, {}).get("attempted_visits", 0))
        completed = int(agg.get(s, {}).get("completed_visits", 0))
        missed = max(planned - completed, 0)

        total_dur = int(agg.get(s, {}).get("total_duration_min", 0))
        dur_count = int(agg.get(s, {}).get("dur_count", 0))
        avg_dur = (total_dur / dur_count) if dur_count else 0

        acc_count = int(agg.get(s, {}).get("acc_count", 0))
        avg_acc = (agg.get(s, {}).get("acc_sum", 0.0) / acc_count) if acc_count else 0

        poor = int(agg.get(s, {}).get("poor_accuracy_visits", 0))
        completion_pct = (completed / planned * 100) if planned else 0

        out.append({
            "salesman": s,
            "planned_visits": planned,
            "attempted_visits": attempted,
            "completed_visits": completed,
            "missed_visits": missed,
            "completion_pct": completion_pct,
            "total_duration_min": total_dur,
            "avg_duration_min": avg_dur,
            "avg_accuracy_m": avg_acc,
            "poor_accuracy_visits": poor,
            "first_check_in": agg.get(s, {}).get("first_check_in"),
            "last_check_out": agg.get(s, {}).get("last_check_out"),
        })

    # Order by Completed desc
    out.sort(key=lambda x: (x.get("completed_visits", 0), x.get("planned_visits", 0)), reverse=True)
    return out


def get_chart(data):
    labels = [d.get("salesman") for d in (data or [])]
    completed = [int(d.get("completed_visits") or 0) for d in (data or [])]
    planned = [int(d.get("planned_visits") or 0) for d in (data or [])]
    missed = [int(d.get("missed_visits") or 0) for d in (data or [])]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Completed", "values": completed},
                {"name": "Planned", "values": planned},
                {"name": "Missed", "values": missed}
            ]
        },
        "type": "bar"
    }
