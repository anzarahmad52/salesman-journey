import frappe
from frappe.utils import getdate


GOOD_ACC = 20.0
MEDIUM_ACC = 50.0


def execute(filters=None):
    filters = filters or {}

    date = getdate(filters.get("date"))
    salesman = filters.get("salesman")
    customer = filters.get("customer")
    journey_plan = filters.get("journey_plan")
    status = (filters.get("status") or "").strip()
    accuracy_threshold = float(filters.get("accuracy_threshold") or 50)

    columns = get_columns()
    data = get_data(date, salesman, customer, journey_plan, status, accuracy_threshold)
    return columns, data


def get_columns():
    return [
        {"label": "Visit Log", "fieldname": "visit_log", "fieldtype": "Link", "options": "Sales Visit Log", "width": 170},
        {"label": "Visit Date", "fieldname": "visit_date", "fieldtype": "Date", "width": 95},
        {"label": "Salesman", "fieldname": "salesman", "fieldtype": "Link", "options": "User", "width": 160},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Journey Plan", "fieldname": "journey_plan", "fieldtype": "Link", "options": "Journey Plan Template", "width": 170},

        {"label": "Check-in Time", "fieldname": "check_in_time", "fieldtype": "Datetime", "width": 160},
        {"label": "Check-out Time", "fieldname": "check_out_time", "fieldtype": "Datetime", "width": 160},

        {"label": "Duration (Min)", "fieldname": "duration_min", "fieldtype": "Int", "width": 110},
        {"label": "Completed", "fieldname": "is_completed", "fieldtype": "Check", "width": 90},

        {"label": "Location Accuracy (m)", "fieldname": "location_accuracy", "fieldtype": "Float", "width": 150},
        {"label": "Accuracy Flag", "fieldname": "accuracy_flag", "fieldtype": "Data", "width": 120},

        {"label": "Outcome", "fieldname": "outcome", "fieldtype": "Data", "width": 110},
        {"label": "Linked Order", "fieldname": "linked_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},

        {"label": "Notes", "fieldname": "notes", "fieldtype": "Small Text", "width": 260},
        {"label": "Status", "fieldname": "row_status", "fieldtype": "Data", "width": 120},
    ]


def accuracy_flag(acc):
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


def duration_minutes(in_time, out_time):
    if not in_time or not out_time:
        return None
    try:
        dt_in = frappe.utils.get_datetime(in_time)
        dt_out = frappe.utils.get_datetime(out_time)
        return int((dt_out - dt_in).total_seconds() // 60)
    except Exception:
        return None


def get_data(date, salesman, customer, journey_plan, status, accuracy_threshold):
    # Planned visits (SVL)
    svl_filters = [["visit_date", "=", date]]
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
        order_by="salesman asc, customer asc"
    )

    if not svl_rows:
        return []

    svl_names = [r.name for r in svl_rows]
    svl_tuple = tuple(svl_names) if len(svl_names) > 1 else (svl_names[0],)

    # Trackers on same day
    cit_conditions = ["docstatus < 2", "date(check_in_time) = %(d)s"]
    params = {"d": date}

    if salesman:
        cit_conditions.append("salesman = %(salesman)s")
        params["salesman"] = salesman
    if customer:
        cit_conditions.append("customer = %(customer)s")
        params["customer"] = customer

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
        {**params, "svl_names": svl_tuple},
        as_dict=True,
    )

    # Match logic
    by_visit_log = {}
    by_key = {}

    for c in cit_rows:
        if c.get("visit_log"):
            if c.visit_log not in by_visit_log:
                by_visit_log[c.visit_log] = c
        else:
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

        dur = duration_minutes(check_in_time, check_out_time)
        completed = 1 if check_out_time else 0

        acc = tracker.location_accuracy if tracker else None
        flag = accuracy_flag(acc)

        row_status = "Completed" if completed else "Missed"

        # Apply status filter
        if status == "Completed Only" and not completed:
            continue
        if status == "Missed Only" and completed:
            continue
        if status == "Planned Only":
            # Planned only shows all planned rows, regardless of completion
            pass

        # Additional “poor accuracy” classification is shown in flag, but not filtering by default
        out.append({
            "visit_log": r.name,
            "visit_date": r.visit_date,
            "salesman": r.salesman,
            "customer": r.customer,
            "journey_plan": r.journey_plan,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "duration_min": dur,
            "is_completed": completed,
            "location_accuracy": acc,
            "accuracy_flag": flag,
            "outcome": r.outcome,
            "linked_order": r.linked_order,
            "notes": (tracker.notes if tracker and tracker.get("notes") else r.remarks),
            "row_status": row_status,
        })

    return out
