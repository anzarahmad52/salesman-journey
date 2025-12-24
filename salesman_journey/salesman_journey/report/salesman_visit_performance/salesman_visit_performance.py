import frappe
from frappe.utils import getdate, nowdate
from frappe.utils.data import flt


GOOD_ACC = 20.0
MEDIUM_ACC = 50.0


def execute(filters=None):
    filters = filters or {}

    view_mode = (filters.get("view_mode") or "Detail").strip()
    from_date = getdate(filters.get("from_date") or nowdate())
    to_date = getdate(filters.get("to_date") or nowdate())

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    if view_mode == "Summary":
        columns = get_summary_columns()
        data = get_summary_data(filters, from_date, to_date)
        chart = get_summary_chart(data)
        return columns, data, None, chart

    if view_mode == "Customer Summary":
        columns = get_customer_summary_columns()
        data = get_customer_summary_data(filters, from_date, to_date)

        # Multiple dashboards (KPI cards)
        report_summary = get_customer_summary_report_summary(data)

        # Salesman-wise dashboard chart (not customer-wise)
        chart = get_customer_summary_chart(data)

        # Return: columns, data, message, chart, report_summary
        return columns, data, None, chart, report_summary

    # Default: Detail
    columns = get_detail_columns()
    data = get_detail_data(filters, from_date, to_date)
    return columns, data

def get_detail_columns():
    return [
        {"label": "Visit Log", "fieldname": "visit_log", "fieldtype": "Link", "options": "Sales Visit Log", "width": 170},
        {"label": "Visit Date", "fieldname": "visit_date", "fieldtype": "Date", "width": 95},
        {"label": "Salesman", "fieldname": "salesman", "fieldtype": "Link", "options": "User", "width": 160},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 190},
        {"label": "Journey Plan", "fieldname": "journey_plan", "fieldtype": "Link", "options": "Journey Plan Template", "width": 170},

        {"label": "Check-in Time", "fieldname": "check_in_time", "fieldtype": "Datetime", "width": 160},
        {"label": "Check-out Time", "fieldname": "check_out_time", "fieldtype": "Datetime", "width": 160},

        {"label": "Duration (Min)", "fieldname": "duration_min", "fieldtype": "Int", "width": 110},
        {"label": "Completed", "fieldname": "is_completed", "fieldtype": "Check", "width": 90},

        {"label": "Location Accuracy (m)", "fieldname": "location_accuracy", "fieldtype": "Float", "width": 140},
        {"label": "Accuracy Flag", "fieldname": "accuracy_flag", "fieldtype": "Data", "width": 120},

        {"label": "Outcome", "fieldname": "outcome", "fieldtype": "Data", "width": 110},
        {"label": "Linked Order", "fieldname": "linked_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": "Notes", "fieldname": "notes", "fieldtype": "Small Text", "width": 220},
    ]


def get_summary_columns():
    return [
        {"label": "Salesman", "fieldname": "salesman", "fieldtype": "Link", "options": "User", "width": 190},

        {"label": "Planned Visits", "fieldname": "planned_visits", "fieldtype": "Int", "width": 120},
        {"label": "Attempted Visits", "fieldname": "attempted_visits", "fieldtype": "Int", "width": 130},
        {"label": "Completed Visits", "fieldname": "completed_visits", "fieldtype": "Int", "width": 130},
        {"label": "Missed Visits", "fieldname": "missed_visits", "fieldtype": "Int", "width": 120},
        {"label": "Completion %", "fieldname": "completion_pct", "fieldtype": "Percent", "width": 115},

        {"label": "Total Duration (Min)", "fieldname": "total_duration_min", "fieldtype": "Int", "width": 150},
        {"label": "Avg Duration (Min)", "fieldname": "avg_duration_min", "fieldtype": "Float", "width": 140},

        {"label": "Avg Accuracy (m)", "fieldname": "avg_accuracy_m", "fieldtype": "Float", "width": 130},
        {"label": "Poor Accuracy Visits", "fieldname": "poor_accuracy_visits", "fieldtype": "Int", "width": 150}
    ]


def get_customer_summary_columns():
    return [
        {"label": "Salesman", "fieldname": "salesman", "fieldtype": "Link", "options": "User", "width": 180},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 190},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 220},

        {"label": "Planned Visits", "fieldname": "planned_visits", "fieldtype": "Int", "width": 120},
        {"label": "Completed Visits", "fieldname": "completed_visits", "fieldtype": "Int", "width": 130},
        {"label": "Missed Visits", "fieldname": "missed_visits", "fieldtype": "Int", "width": 120},

        {"label": "Sales Invoice Count", "fieldname": "invoice_count", "fieldtype": "Int", "width": 150},
        {"label": "Total Revenue", "fieldname": "invoice_revenue", "fieldtype": "Currency", "width": 140},
    ]

def _accuracy_flag(acc):
    if acc is None:
        return "N/A"
    try:
        a = float(acc)
    except Exception:
        return "N/A"

    if a <= GOOD_ACC:
        return "Good"
    if a <= MEDIUM_ACC:
        return "Medium"
    return "Poor"


def _duration_minutes(in_time, out_time):
    if not in_time or not out_time:
        return None
    try:
        dt_in = frappe.utils.get_datetime(in_time)
        dt_out = frappe.utils.get_datetime(out_time)
        return int((dt_out - dt_in).total_seconds() // 60)
    except Exception:
        return None

def get_detail_data(filters, from_date, to_date):
    salesman = filters.get("salesman")
    customer = filters.get("customer")
    journey_plan = filters.get("journey_plan")
    only_completed = int(filters.get("only_completed") or 0)

    svl_filters = [["visit_date", "between", [from_date, to_date]]]
    if salesman:
        svl_filters.append(["salesman", "=", salesman])
    if customer:
        svl_filters.append(["customer", "=", customer])
    if journey_plan:
        svl_filters.append(["journey_plan", "=", journey_plan])

    svl_rows = frappe.get_all(
        "Sales Visit Log",
        filters=svl_filters,
        fields=[
            "name", "visit_date", "salesman", "customer", "journey_plan",
            "check_in_time", "check_out_time", "outcome", "linked_order", "remarks"
        ],
        order_by="visit_date desc, salesman asc, customer asc"
    )

    if not svl_rows:
        return []

    svl_names = [r.name for r in svl_rows]

    cit_conditions = ["docstatus < 2", "date(check_in_time) between %(from_date)s and %(to_date)s"]
    cit_params = {"from_date": from_date, "to_date": to_date}

    if salesman:
        cit_conditions.append("salesman = %(salesman)s")
        cit_params["salesman"] = salesman
    if customer:
        cit_conditions.append("customer = %(customer)s")
        cit_params["customer"] = customer

    svl_tuple = tuple(svl_names) if len(svl_names) > 1 else (svl_names[0],)

    cit_rows = frappe.db.sql(
        f"""
        select
            name, salesman, customer, check_in_time, check_out_time,
            location_accuracy, visit_log, notes, modified
        from `tabCheck-in Tracker`
        where {" and ".join(cit_conditions)}
          and (
              visit_log in %(svl_names)s
              or visit_log is null
              or visit_log = ''
          )
        order by modified desc
        """,
        {**cit_params, "svl_names": svl_tuple},
        as_dict=True,
    )

    by_visit_log = {}
    by_key = {}

    for c in cit_rows:
        if c.get("visit_log"):
            if c.visit_log not in by_visit_log:
                by_visit_log[c.visit_log] = c
        else:
            if c.get("check_in_time"):
                k = (c.get("salesman"), c.get("customer"), str(getdate(c.get("check_in_time"))))
                if k not in by_key:
                    by_key[k] = c

    out = []
    for r in svl_rows:
        tracker = by_visit_log.get(r.name)
        if not tracker:
            k = (r.salesman, r.customer, str(getdate(r.visit_date)))
            tracker = by_key.get(k)

        check_in_time = tracker.check_in_time if tracker and tracker.get("check_in_time") else r.check_in_time
        check_out_time = tracker.check_out_time if tracker and tracker.get("check_out_time") else r.check_out_time

        duration_min = _duration_minutes(check_in_time, check_out_time)
        is_completed = 1 if check_out_time else 0

        if only_completed and not is_completed:
            continue

        acc = tracker.location_accuracy if tracker else None
        acc_flag = _accuracy_flag(acc)

        out.append({
            "visit_log": r.name,
            "visit_date": r.visit_date,
            "salesman": r.salesman,
            "customer": r.customer,
            "journey_plan": r.journey_plan,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "duration_min": duration_min,
            "is_completed": is_completed,
            "location_accuracy": acc,
            "accuracy_flag": acc_flag,
            "outcome": r.outcome,
            "linked_order": r.linked_order,
            "notes": (tracker.notes if tracker and tracker.get("notes") else r.remarks),
        })

    return out

def get_summary_data(filters, from_date, to_date):
    salesman = filters.get("salesman")
    journey_plan = filters.get("journey_plan")
    poor_accuracy_threshold = float(filters.get("poor_accuracy_threshold") or 50)

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

    cit_conditions = ["docstatus < 2", "date(check_in_time) between %(from_date)s and %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if salesman:
        cit_conditions.append("salesman = %(salesman)s")
        params["salesman"] = salesman

    cit_rows = frappe.db.sql(
        f"""
        select
            salesman,
            check_in_time,
            check_out_time,
            location_accuracy
        from `tabCheck-in Tracker`
        where {" and ".join(cit_conditions)}
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
            "poor_accuracy_visits": 0
        })

        if c.get("check_in_time"):
            a["attempted_visits"] += 1

        if c.get("check_out_time"):
            a["completed_visits"] += 1

        dur = _duration_minutes(c.get("check_in_time"), c.get("check_out_time"))
        if dur is not None:
            a["total_duration_min"] += dur
            a["dur_count"] += 1

        acc = c.get("location_accuracy")
        # ignore 0 values (your DB currently stores 0 everywhere)
        if acc is not None:
            try:
                acc_f = float(acc)
                if acc_f > 0:
                    a["acc_sum"] += acc_f
                    a["acc_count"] += 1
                    if acc_f > poor_accuracy_threshold:
                        a["poor_accuracy_visits"] += 1
            except Exception:
                pass

    salesmen = set(planned_by_salesman.keys()) | set(agg.keys())
    out = []

    for s in sorted(salesmen):
        planned = int(planned_by_salesman.get(s, 0))
        attempted = int(agg.get(s, {}).get("attempted_visits", 0))
        completed = int(agg.get(s, {}).get("completed_visits", 0))
        total_dur = int(agg.get(s, {}).get("total_duration_min", 0))

        denom = completed or int(agg.get(s, {}).get("dur_count", 0)) or 0
        avg_dur = (total_dur / denom) if denom else 0

        acc_count = int(agg.get(s, {}).get("acc_count", 0))
        avg_acc = (agg.get(s, {}).get("acc_sum", 0.0) / acc_count) if acc_count else 0

        poor = int(agg.get(s, {}).get("poor_accuracy_visits", 0))
        missed = max(planned - completed, 0)
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
            "poor_accuracy_visits": poor
        })

    out.sort(key=lambda x: (x.get("completed_visits", 0), x.get("planned_visits", 0)), reverse=True)
    return out


def get_summary_chart(data):
    labels = [d.get("salesman") for d in (data or [])]
    completed = [int(d.get("completed_visits") or 0) for d in (data or [])]
    planned = [int(d.get("planned_visits") or 0) for d in (data or [])]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Completed Visits", "values": completed},
                {"name": "Planned Visits", "values": planned},
            ],
        },
        "type": "bar"
    }
def get_customer_summary_data(filters, from_date, to_date):
    salesman = filters.get("salesman")
    customer = filters.get("customer")
    journey_plan = filters.get("journey_plan")

    # 1) Visit counts per salesman+customer from Sales Visit Log
    svl_conditions = ["visit_date between %(from_date)s and %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if salesman:
        svl_conditions.append("salesman = %(salesman)s")
        params["salesman"] = salesman
    if customer:
        svl_conditions.append("customer = %(customer)s")
        params["customer"] = customer
    if journey_plan:
        svl_conditions.append("journey_plan = %(journey_plan)s")
        params["journey_plan"] = journey_plan

    svl_agg = frappe.db.sql(
        f"""
        select
            salesman,
            customer,
            count(*) as planned_visits,
            sum(case when check_out_time is not null then 1 else 0 end) as completed_visits
        from `tabSales Visit Log`
        where {" and ".join(svl_conditions)}
        group by salesman, customer
        """,
        params,
        as_dict=True,
    )

    if not svl_agg:
        return []

    # Prepare unique customer list
    customers = sorted({r.get("customer") for r in svl_agg if r.get("customer")})
    cust_tuple = tuple(customers) if len(customers) > 1 else (customers[0],)

    # 2) Sales Invoices per customer (date range)
    inv_rows = frappe.db.sql(
        """
        select
            customer,
            count(*) as invoice_count,
            sum(grand_total) as invoice_revenue
        from `tabSales Invoice`
        where docstatus = 1
          and ifnull(is_return, 0) = 0
          and posting_date between %(from_date)s and %(to_date)s
          and customer in %(customers)s
        group by customer
        """,
        {**params, "customers": cust_tuple},
        as_dict=True,
    )

    inv_by_customer = {r["customer"]: r for r in (inv_rows or [])}

    # 3) Customer names
    cust_names = {}
    for c in customers:
        cust_names[c] = frappe.db.get_value("Customer", c, "customer_name") or ""

    out = []
    for r in svl_agg:
        cust = r.get("customer")
        inv = inv_by_customer.get(cust) or {}

        planned = int(r.get("planned_visits") or 0)
        completed = int(r.get("completed_visits") or 0)
        missed = max(planned - completed, 0)

        out.append({
            "salesman": r.get("salesman"),
            "customer": cust,
            "customer_name": cust_names.get(cust, ""),

            "planned_visits": planned,
            "completed_visits": completed,
            "missed_visits": missed,

            "invoice_count": int(inv.get("invoice_count") or 0),
            "invoice_revenue": flt(inv.get("invoice_revenue") or 0),
        })

    # Sort by revenue then completed
    out.sort(key=lambda x: (x.get("invoice_revenue", 0), x.get("completed_visits", 0)), reverse=True)
    return out


def _agg_salesman_dashboard_from_customer_rows(data):
    """
    Customer Summary table is salesman+customer rows.
    For dashboard/chart we aggregate by salesman only.
    """
    agg = {}
    for r in (data or []):
        s = r.get("salesman")
        if not s:
            continue

        a = agg.setdefault(s, {
            "completed_visits": 0,
            "invoice_count": 0,
            "invoice_revenue": 0.0
        })

        a["completed_visits"] += int(r.get("completed_visits") or 0)
        a["invoice_count"] += int(r.get("invoice_count") or 0)
        a["invoice_revenue"] += flt(r.get("invoice_revenue") or 0)

    out = []
    for s, v in agg.items():
        out.append({"salesman": s, **v})

    out.sort(key=lambda x: (x.get("invoice_revenue", 0), x.get("completed_visits", 0)), reverse=True)
    return out


def get_customer_summary_report_summary(data):
    """
    Multiple dashboards (KPI cards) at top
    """
    total_completed = sum(int(r.get("completed_visits") or 0) for r in (data or []))
    total_invoices = sum(int(r.get("invoice_count") or 0) for r in (data or []))
    total_revenue = sum(flt(r.get("invoice_revenue") or 0) for r in (data or []))

    return [
        {"label": "Completed Visits", "value": total_completed, "datatype": "Int"},
        {"label": "Sales Invoice Count", "value": total_invoices, "datatype": "Int"},
        {"label": "Total Revenue", "value": total_revenue, "datatype": "Currency"},
    ]


def get_customer_summary_chart(data):
    """
    Salesman-wise dashboard chart:
    - Completed Visits (bar)
    - Sales Invoice Count (bar)
    - Total Revenue (line)
    """
    agg = _agg_salesman_dashboard_from_customer_rows(data)

    agg = agg[:12]

    labels = [d.get("salesman") for d in agg]
    completed = [int(d.get("completed_visits") or 0) for d in agg]
    invoices = [int(d.get("invoice_count") or 0) for d in agg]
    revenue = [flt(d.get("invoice_revenue") or 0) for d in agg]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Completed Visits", "values": completed, "chartType": "bar"},
                {"name": "Sales Invoice Count", "values": invoices, "chartType": "bar"},
                {"name": "Total Revenue", "values": revenue, "chartType": "line"},
            ],
        },
        "type": "axis-mixed"
    }