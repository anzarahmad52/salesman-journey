import frappe
from frappe import _

@frappe.whitelist()
def get_user_profile_data():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    user_doc = frappe.get_doc("User", user)
    full_name = user_doc.full_name or user_doc.first_name
    email = user_doc.email
    image = user_doc.user_image or ""
    roles = frappe.get_roles(user)

    # Helper to fetch user permissions for any linked DocType
    def get_user_permissions_for(doctype):
        return frappe.get_all(
            "User Permission",
            filters={"user": user, "allow": doctype},
            pluck="for_value"
        )

    return {
        "full_name": full_name,
        "email": email,
        "user_image": image,
        "roles": roles,
        "territories": get_user_permissions_for("Territory"),
        "warehouses": get_user_permissions_for("Warehouse"),
        "customer_groups": get_user_permissions_for("Customer Group"),
        "cost_centers": get_user_permissions_for("Cost Center"),
        "pos_profiles": get_user_permissions_for("POS Profile"),
        "doctype_permissions": frappe.permissions.get_user_permissions(user)
    }
