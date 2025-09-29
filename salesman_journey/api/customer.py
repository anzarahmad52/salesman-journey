import frappe

@frappe.whitelist()
def get_customer_map_link(customer):
    if not customer:
        frappe.throw("Customer is required")

    lat, lon = frappe.db.get_value("Customer", customer, ["latitude", "longitude"])

    if not lat or not lon:
        return ""

    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
