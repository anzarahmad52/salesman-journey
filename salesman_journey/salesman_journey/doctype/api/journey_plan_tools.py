import frappe
from frappe.utils import getdate, nowdate


@frappe.whitelist()
def get_customers(territory=None, customer_group=None, search_txt=None, limit=500):
    """Return customers filtered by territory / customer group / search text (value,label)."""
    params = {}
    where = "where docstatus < 2 and disabled = 0"

    if territory:
        where += " and territory = %(territory)s"
        params["territory"] = territory

    if customer_group:
        where += " and customer_group = %(customer_group)s"
        params["customer_group"] = customer_group

    if search_txt:
        where += " and (name like %(st)s or customer_name like %(st)s)"
        params["st"] = f"%{search_txt}%"

    limit = int(limit or 500)
    where += f" order by customer_name limit {limit}"

    rows = frappe.db.sql(
        f"""
        select name, customer_name
        from `tabCustomer`
        {where}
        """,
        params,
        as_dict=True,
    )

    return [{"value": r.name, "label": r.customer_name or r.name} for r in rows]


@frappe.whitelist()
def get_template_rows(source_template):
    """
    Return Route Day rows from another Journey Plan Template.
    USED when copying template → MUST include week_no.
    """
    if not source_template:
        return []

    return frappe.get_all(
        "Route Day",
        filters={
            "parent": source_template,
            "parenttype": "Journey Plan Template"
        },
        fields=[
            "week_no",
            "customer",
            "day_of_week",
            "time_slot",
            "expected_duration"
        ],
        order_by="week_no asc, day_of_week asc, time_slot asc",
    )


@frappe.whitelist()
def get_active_template(salesman=None, on_date=None):
    """
    Return the best active Journey Plan Template for a salesman for a given date.

    NOTE: Journey Plan Template is NOT submittable now, so docstatus is always 0.
    We rely on auto status:
      - status = 'Active'
      - is_disabled = 0
      - start_date <= date
      - end_date is null OR end_date >= date
    """
    salesman = salesman or frappe.session.user
    d = getdate(on_date or nowdate())

    rows = frappe.get_all(
        "Journey Plan Template",
        filters={
            "salesman": salesman,
            "status": "Active",
            "is_disabled": 0
        },
        fields=[
            "name",
            "start_date",
            "end_date",
            "territory",
            "cycle_weeks",
            "cycle_anchor_date"
        ],
        order_by="start_date desc",
        limit=20,
    )

    # pick the first template matching date window
    for r in rows:
        sd = getdate(r.start_date) if r.start_date else None
        ed = getdate(r.end_date) if r.end_date else None

        if sd and d < sd:
            continue
        if ed and d > ed:
            continue

        return {"template": r.name, "meta": r}

    return {"template": None, "meta": None}


@frappe.whitelist()
def get_today_route(template_name=None, for_date=None, salesman=None):
    """
    Return today's visit list based on:
    - Journey Plan Template
    - Rotating week_no
    - Day of week

    Usage for App:
      1) call get_active_template()
      2) pass template_name to get_today_route()
    Or just call get_today_route without template_name, it will auto-pick active template.
    """
    visit_date = getdate(for_date or nowdate())
    day_name = visit_date.strftime("%A")

    # auto pick active template if not provided
    if not template_name:
        active = get_active_template(salesman=salesman, on_date=str(visit_date))
        template_name = active.get("template")

    if not template_name:
        return {
            "date": str(visit_date),
            "day": day_name,
            "week_no": None,
            "template": None,
            "customers": [],
            "message": "No active Journey Plan Template found for this date."
        }

    doc = frappe.get_doc("Journey Plan Template", template_name)
    week_no = doc.get_week_no_for_date(visit_date)

    rows = frappe.get_all(
        "Route Day",
        filters={
            "parent": template_name,
            "parenttype": "Journey Plan Template",
            "day_of_week": day_name,
            "week_no": week_no,
        },
        fields=[
            "customer",
            "time_slot",
            "expected_duration",
        ],
        order_by="time_slot asc",
    )

    return {
        "date": str(visit_date),
        "day": day_name,
        "week_no": week_no,
        "template": template_name,
        "customers": rows,
    }
