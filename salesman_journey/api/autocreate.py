
import frappe
from frappe.utils import nowdate, getdate

@frappe.whitelist()
def create_sales_visit_logs_for_today():
    today = getdate(nowdate())
    weekday = today.strftime("%A")

    templates = frappe.get_all(
        "Journey Plan Template",
        filters={"status": "Active"},
        fields=["name", "salesman", "start_date", "end_date"]
    )

    for tpl in templates:
        if tpl.start_date and tpl.end_date and not (tpl.start_date <= today <= tpl.end_date):
            continue

        route_days = frappe.get_all(
            "Route Day",
            filters={"parent": tpl.name, "day_of_week": weekday},
            fields=["customer"]
        )

        for rd in route_days:
            exists = frappe.db.exists("Sales Visit Log", {
                "salesman": tpl.salesman,
                "customer": rd.customer,
                "visit_date": today
            })
            if not exists:
                doc = frappe.new_doc("Sales Visit Log")
                doc.salesman = tpl.salesman
                doc.customer = rd.customer
                doc.visit_date = today
                doc.journey_plan = tpl.name
                doc.insert()
