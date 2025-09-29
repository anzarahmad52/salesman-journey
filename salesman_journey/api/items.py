import frappe

@frappe.whitelist()
def get_item_list():
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

    permitted_item_groups = get_permitted_documents("Item Group")

    if not permitted_item_groups:
        return []

    formatted = "', '".join(permitted_item_groups)

    return frappe.db.sql(f"""
        SELECT 
            i.name, i.item_name, i.item_group, i.stock_uom,
            ip.price_list_rate AS price,
            COALESCE(SUM(b.actual_qty), 0) AS actual_qty
        FROM `tabItem` i
        LEFT JOIN `tabItem Price` ip 
            ON ip.item_code = i.name AND ip.price_list = 'Standard Selling'
        LEFT JOIN `tabBin` b ON b.item_code = i.name
        WHERE i.disabled = 0
        AND i.item_group IN ('{formatted}')
        GROUP BY i.name
        ORDER BY i.item_name
        LIMIT 100
    """, as_dict=True)
