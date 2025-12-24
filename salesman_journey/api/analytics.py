import frappe
from frappe.utils import getdate, add_months, nowdate
from frappe.utils.data import flt


GOOD_ACC = 20.0
MEDIUM_ACC = 50.0


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


@frappe.whitelist()
def get_month_calendar(month_date=None, salesman=None, journey_plan=None, poor_accuracy_threshold=50):
    """
    Returns calendar data in the shape:
    {
      "month": "YYYY-MM",
      "days": {
        "YYYY-MM-DD": {
          "planned": int,
          "completed": int,
          "missed": int,
          "avg_accuracy_m": float
        }
      }
    }

    Notes:
    - Planned from Sales Visit Log
    - Completed/missed from Sales Visit Log (based on check_out_time)
    - Avg accuracy from Check-in Tracker
    - IMPORTANT: we ignore accuracy values = 0 because DB currently stores 0 always.
      After fixing check-in API, real accuracy will start appearing.
    """
    if not month_date:
        month_date = nowdate()

    d = getdate(month_date)
    month_start = d.replace(day=1)
    month_end = add_months(month_start, 1)

    salesman = (salesman or "").strip() or None
    journey_plan = (journey_plan or "").strip() or None
    poor_accuracy_threshold = flt(poor_accuracy_threshold or 50)

    # -----------------------------
    # 1) Planned visits (SVL)
    # -----------------------------
    svl_filters = [
        ["visit_date", ">=", month_start],
        ["visit_date", "<", month_end],
    ]
    if salesman:
        svl_filters.append(["salesman", "=", salesman])
    if journey_plan:
        svl_filters.append(["journey_plan", "=", journey_plan])

    svl_rows = frappe.get_all(
        "Sales Visit Log",
        filters=svl_filters,
        fields=["name", "visit_date", "check_out_time"],
        limit_page_length=999999
    )

    days = {}

    def _get_day(date_obj):
        ds = str(getdate(date_obj))
        if ds not in days:
            days[ds] = {"planned": 0, "completed": 0, "missed": 0, "avg_accuracy_m": 0}
        return days[ds]

    for r in svl_rows:
        day = _get_day(r.visit_date)
        day["planned"] += 1

        if r.check_out_time:
            day["completed"] += 1
        else:
            # planned but not completed = missed
            day["missed"] += 1

    # -----------------------------
    # 2) Accuracy from Check-in Tracker
    # -----------------------------
    # We use check_in_time date window for the same month
    cit_conditions = [
        "docstatus < 2",
        "check_in_time >= %(from_dt)s",
        "check_in_time < %(to_dt)s",
    ]
    params = {
        "from_dt": f"{month_start} 00:00:00",
        "to_dt": f"{month_end} 00:00:00",
    }

    if salesman:
        cit_conditions.append("salesman = %(salesman)s")
        params["salesman"] = salesman

    # If you want accuracy only for a specific plan, you would need visit_log join,
    # but calendar view is fine without it.
    cit_rows = frappe.db.sql(
        f"""
        SELECT
          DATE(check_in_time) as d,
          location_accuracy
        FROM `tabCheck-in Tracker`
        WHERE {" AND ".join(cit_conditions)}
        """,
        params,
        as_dict=True
    )

    acc_sum = {}
    acc_count = {}

    for c in cit_rows:
        ds = str(getdate(c.get("d")))
        acc = c.get("location_accuracy")

        # IMPORTANT FIX:
        # ignore 0 accuracy because your DB currently stores 0 for all.
        # after API fix, real values will be used.
        if acc is None:
            continue

        try:
            acc_f = float(acc)
        except Exception:
            continue

        if acc_f <= 0:
            continue

        acc_sum[ds] = acc_sum.get(ds, 0.0) + acc_f
        acc_count[ds] = acc_count.get(ds, 0) + 1

    for ds, s in acc_sum.items():
        if ds not in days:
            days[ds] = {"planned": 0, "completed": 0, "missed": 0, "avg_accuracy_m": 0}

        cnt = acc_count.get(ds, 0)
        days[ds]["avg_accuracy_m"] = (s / cnt) if cnt else 0

    return {
        "month": month_start.strftime("%Y-%m"),
        "days": days
    }





# import frappe
# from frappe.utils import getdate, nowdate


# @frappe.whitelist()
# def get_salesman_kpis(from_date=None, to_date=None, salesman=None):
#     """
#     KPIs for a salesman between date range.
#     - Planned visits: from Sales Visit Log
#     - Attempted/completed/duration/avg accuracy: from Check-in Tracker
#     """
#     salesman = salesman or frappe.session.user
#     from_date = getdate(from_date or nowdate())
#     to_date = getdate(to_date or nowdate())

#     planned = frappe.db.count(
#         "Sales Visit Log",
#         filters={"salesman": salesman, "visit_date": ["between", [from_date, to_date]]},
#     )

#     # Use trackers by date(check_in_time) because visit_log mapping might be missing.
#     tracker = frappe.db.sql(
#         """
#         select
#             count(*) as attempted,
#             sum(case when check_out_time is not null then 1 else 0 end) as completed,
#             sum(
#                 case
#                     when check_in_time is not null and check_out_time is not null
#                     then timestampdiff(minute, check_in_time, check_out_time)
#                     else 0
#                 end
#             ) as total_duration_min,
#             avg(location_accuracy) as avg_accuracy
#         from `tabCheck-in Tracker`
#         where docstatus < 2
#           and salesman = %(salesman)s
#           and date(check_in_time) between %(from_date)s and %(to_date)s
#         """,
#         {"salesman": salesman, "from_date": from_date, "to_date": to_date},
#         as_dict=True,
#     )[0] if planned or True else {}

#     attempted = int(tracker.get("attempted") or 0)
#     completed = int(tracker.get("completed") or 0)
#     total_duration_min = int(tracker.get("total_duration_min") or 0)
#     avg_accuracy = float(tracker.get("avg_accuracy") or 0)

#     missed = max(planned - completed, 0)
#     completion_pct = (completed / planned * 100) if planned else 0
#     avg_duration_min = (total_duration_min / completed) if completed else 0

#     return {
#         "salesman": salesman,
#         "from_date": str(from_date),
#         "to_date": str(to_date),
#         "planned_visits": planned,
#         "attempted_visits": attempted,
#         "completed_visits": completed,
#         "missed_visits": missed,
#         "completion_pct": completion_pct,
#         "total_duration_min": total_duration_min,
#         "avg_duration_min": avg_duration_min,
#         "avg_accuracy_m": avg_accuracy,
#     }


# @frappe.whitelist()
# def get_team_summary(from_date=None, to_date=None, territory=None):
#     """
#     Supervisor view (all salesmen) summary.
#     Planned from SVL; actual from trackers.
#     """
#     from_date = getdate(from_date or nowdate())
#     to_date = getdate(to_date or nowdate())

#     planned_filters = {"visit_date": ["between", [from_date, to_date]]}
#     if territory:
#         # Sales Visit Log doesn't have territory; we infer via Journey Plan Template if needed later.
#         # For now, territory filter is not applied here.
#         pass

#     planned_total = frappe.db.count("Sales Visit Log", filters=planned_filters)

#     actual = frappe.db.sql(
#         """
#         select
#             count(*) as attempted,
#             sum(case when check_out_time is not null then 1 else 0 end) as completed,
#             sum(
#                 case
#                     when check_in_time is not null and check_out_time is not null
#                     then timestampdiff(minute, check_in_time, check_out_time)
#                     else 0
#                 end
#             ) as total_duration_min,
#             avg(location_accuracy) as avg_accuracy
#         from `tabCheck-in Tracker`
#         where docstatus < 2
#           and date(check_in_time) between %(from_date)s and %(to_date)s
#         """,
#         {"from_date": from_date, "to_date": to_date},
#         as_dict=True,
#     )[0]

#     attempted = int(actual.get("attempted") or 0)
#     completed = int(actual.get("completed") or 0)
#     total_duration_min = int(actual.get("total_duration_min") or 0)
#     avg_accuracy = float(actual.get("avg_accuracy") or 0)

#     missed = max(planned_total - completed, 0)
#     completion_pct = (completed / planned_total * 100) if planned_total else 0
#     avg_duration_min = (total_duration_min / completed) if completed else 0

#     return {
#         "from_date": str(from_date),
#         "to_date": str(to_date),
#         "planned_visits": planned_total,
#         "attempted_visits": attempted,
#         "completed_visits": completed,
#         "missed_visits": missed,
#         "completion_pct": completion_pct,
#         "total_duration_min": total_duration_min,
#         "avg_duration_min": avg_duration_min,
#         "avg_accuracy_m": avg_accuracy,
#     }
