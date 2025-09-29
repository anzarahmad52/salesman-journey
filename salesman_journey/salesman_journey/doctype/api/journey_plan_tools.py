import frappe

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
        f"select name, customer_name from `tabCustomer` {where}",
        params,
        as_dict=True,
    )
    return [{"value": r.name, "label": r.customer_name or r.name} for r in rows]


@frappe.whitelist()
def get_template_rows(source_template):
    """Return Route Day rows from another Journey Plan Template."""
    if not source_template:
        return []

    return frappe.get_all(
        "Route Day",
        filters={"parent": source_template, "parenttype": "Journey Plan Template"},
        fields=["customer", "day_of_week", "time_slot", "expected_duration"],
        order_by="day_of_week asc, time_slot asc",
    )
