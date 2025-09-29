import frappe
from frappe.utils import now_datetime

ALERT_TYPE = "MATERIAL_REQUEST"  # tag via subject prefix, not a field


def _create_notification_log(for_user: str, doc):
    # Use only stock fields of Notification Log on v15
    frappe.get_doc({
        "doctype": "Notification Log",
        # "subject": f"[{ALERT_TYPE}] Material Request {doc.name}",
        "subject": f" New Loading Request {doc.name}",
        #"status": f"{doc.status or 'Draft'}",
        "document_type": doc.doctype,
        "document_name": doc.name,
        "for_user": for_user,
        "type": "Alert",
    }).insert(ignore_permissions=True)


def _eligible_supervisors(doc):
    """
    Return user IDs of Sales Supervisors who are permitted to see this MR.

    Strategy:
      • Primary filter by User Permissions on Warehouse (doc.set_warehouse) if present.
      • Otherwise fallback to Company permission.
      • Optional: pick up default territory from Selling Settings (if you use territory perms).
    """
    supervisors = [d.parent for d in frappe.get_all(
        "Has Role", filters={"role": "Sales Supervisor"}, fields=["parent"]
    )]

    mr_warehouse = getattr(doc, "set_warehouse", None)
    mr_company = getattr(doc, "company", None)

    # Optional: if you use Territory permissions, read from Selling Settings
    mr_territory = getattr(doc, "custom_territory", None)
    if not mr_territory:
        try:
            mr_territory = frappe.db.get_single_value("Selling Settings", "default_territory")
        except Exception:
            mr_territory = None

    allowed = []
    for user in supervisors:
        ok = False

        # Warehouse-based permission
        if mr_warehouse and frappe.db.exists(
            "User Permission", {"user": user, "allow": "Warehouse", "for_value": mr_warehouse}
        ):
            ok = True

        # Territory-based (optional)
        if not ok and mr_territory and frappe.db.exists(
            "User Permission", {"user": user, "allow": "Territory", "for_value": mr_territory}
        ):
            ok = True

        # Company-based fallback
        if not ok and mr_company and frappe.db.exists(
            "User Permission", {"user": user, "allow": "Company", "for_value": mr_company}
        ):
            ok = True

        # Final guard: actual doc permission
        if ok and frappe.has_permission(doc=doc, ptype="read", user=user):
            allowed.append(user)

    return list(set(allowed))


@frappe.whitelist()
def on_mr_created(doc, method=None):
    """Hook: after_insert / on_submit → create alerts for creator + eligible supervisors."""
    if isinstance(doc, str):
        doc = frappe.get_doc("Material Request", doc)

    # Creator (salesman)
    creator = doc.owner
    _create_notification_log(creator, doc)

    # Supervisors (filtered)
    for sup in _eligible_supervisors(doc):
        _create_notification_log(sup, doc)

    # Optional realtime (web desk)
    frappe.publish_realtime(
        event="material_request_created",
        message={"name": doc.name, "doctype": "Material Request"},
        after_commit=True
    )


@frappe.whitelist()
def get_new_material_request_alerts(last_check=None):
    """
    Return Notification Log entries for current user since last_check,
    scoped to document_type = 'Material Request'.
    """
    user = frappe.session.user
    filters = {
        "for_user": user,
        "document_type": "Material Request",
    }
    if last_check:
        filters["creation"] = [">", last_check]

    rows = frappe.get_all(
        "Notification Log",
        filters=filters,
        fields=[
            "name", "subject", "document_type", "document_name",
            "creation"
        ],
        order_by="creation asc",
        limit_page_length=200
    )

    enriched = []
    for r in rows:
        d = frappe.get_value(
            r["document_type"],
            r["document_name"],
            ["material_request_type", "status", "company", "transaction_date", "schedule_date"],
            as_dict=True,
        )
        enriched.append({
            **r,
            "material_request_type": d.material_request_type if d else None,
            "status": d.status if d else None,
            "company": d.company if d else None,
            "transaction_date": d.transaction_date if d else None,
            "schedule_date": d.schedule_date if d else None,
        })

    return {"timestamp": now_datetime(), "alerts": enriched}


@frappe.whitelist()
def mark_mr_alerts_seen(names=None):
    """
    Mark Notification Log rows as seen/read for the current user.
    Handles both 'seen' and 'read' depending on ERPNext version.
    """
    if not names:
        return
    if isinstance(names, str):
        names = frappe.parse_json(names)  # handle JSON string input from Postman

    for n in names:
        try:
            nl = frappe.get_doc("Notification Log", n)
            if nl.for_user == frappe.session.user:
                # Try both, depending on schema
                if hasattr(nl, "seen"):
                    nl.seen = 1
                if hasattr(nl, "read"):
                    nl.read = 1
                nl.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "mark_mr_alerts_seen")
