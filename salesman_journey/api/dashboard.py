import frappe
import json
from frappe.utils import getdate, add_days, today, nowdate
from collections import defaultdict
from frappe.utils import getdate, add_days, today, nowdate, now_datetime
from datetime import timedelta
from frappe import _
from frappe.utils import cint
from datetime import date, timedelta

@frappe.whitelist()
def sales_by_day(filter=None):
    from frappe.utils import nowdate, now_datetime, add_days, getdate
    today = nowdate()

    if filter == "Today":
        results = frappe.db.sql("""
            SELECT HOUR(posting_time) AS hour,
                   SUM(grand_total) AS total
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND posting_date = %s
            GROUP BY HOUR(posting_time)
            ORDER BY hour
        """, (today,), as_dict=True)

    
        return [
            {"date": f"{int(row['hour']):02d}:00", "total": row["total"]}
            for row in results
        ]


    from frappe.utils import add_days
    end_date = today

    if filter == "Month":
        start_date = add_days(today, -29)
    else:  # Default = Week
        start_date = add_days(today, -6)

    results = frappe.db.sql("""
        SELECT posting_date AS date, SUM(grand_total) AS total
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s
        GROUP BY posting_date
        ORDER BY posting_date
    """, (start_date, end_date), as_dict=True)

    return results

@frappe.whitelist()
def sales_by_territory():
    results = frappe.db.sql("""
        SELECT si.territory, SUM(si.grand_total) AS total
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY si.territory
    """, as_dict=True)
    return results
    
@frappe.whitelist()
def supervisor_sales_by_territory(days=30, from_date=None, to_date=None):
    """
    Returns sales by territory for all territories under supervisor's supervision.
    
    Args:
        days (int): Number of days to look back (default: 30)
        from_date (str): Start date (YYYY-MM-DD), overrides days if provided
        to_date (str): End date (YYYY-MM-DD), defaults to today if not provided
    
    Returns:
        dict: {
            "message": [
                {"territory": "R1", "total": 1147.7},
                {"territory": "R12", "total": 632.5},
                ...
            ]
        }
    """
    from frappe.utils import getdate, add_days, today
    
    # Get date range
    if not to_date:
        to_date = today()
    if not from_date:
        from_date = add_days(to_date, -int(days))
    
    # Get supervisor's permitted territories
    try:
        from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
        permitted_territories = get_permitted_documents("Territory")
    except Exception:
        permitted_territories = []
    
    if not permitted_territories:
        return {"message": []}
    
    # Prepare placeholders for SQL query
    placeholders = ", ".join(["%s"] * len(permitted_territories))
    params = permitted_territories + [from_date, to_date]
    
    # Get sales by territory
    results = frappe.db.sql(f"""
        SELECT 
            si.territory, 
            ROUND(SUM(si.grand_total), 1) as total
        FROM `tabSales Invoice` si
        WHERE 
            si.territory IN ({placeholders})
            AND si.docstatus = 1 
            AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.territory
        ORDER BY total DESC
    """.format(placeholders=placeholders), params, as_dict=True)
    
    return results

@frappe.whitelist()
def sales_by_item_group():
    results = frappe.db.sql("""
        SELECT sii.item_group, SUM(sii.amount) AS total
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1 AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY sii.item_group
    """, as_dict=True)
    return results

@frappe.whitelist()
def visit_plan_by_day():
    results = frappe.db.sql("""
        SELECT DATE(visit_time) AS date, COUNT(*) AS count
        FROM `tabSales Visit Log`
        WHERE visit_time >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY DATE(visit_time) ORDER BY DATE(visit_time)
    """, as_dict=True)
    return results

@frappe.whitelist()
def sales_vs_returns_by_month():
    from dateutil.relativedelta import relativedelta

    user = frappe.session.user
    result = []

    for i in range(5):
        month_start = (getdate(nowdate()) - relativedelta(months=i)).replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)

        sales = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Order`
            WHERE owner=%s AND docstatus=1 AND transaction_date BETWEEN %s AND %s
        """, (user, month_start, month_end))[0][0] or 0

        returns = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE owner=%s AND is_return=1 AND docstatus=1 AND posting_date BETWEEN %s AND %s
        """, (user, month_start, month_end))[0][0] or 0

        result.append({
            "month": month_start.strftime('%b'),
            "sales": sales,
            "returns": returns,
        })

    return result[::-1]
@frappe.whitelist()
def supervisor_sales_vs_returns_by_month():
    """
    Returns monthly sales vs returns data for all salespeople under the supervisor's supervision.
    Aggregates data from all salespeople in the supervisor's territory.
    """
    from dateutil.relativedelta import relativedelta
    
    # Get all salespeople under supervisor's supervision
    sales_team = _salesmen_under_perm()
    sales_team_emails = [salesman['email'] for salesman in sales_team if salesman.get('email')]
    
    if not sales_team_emails:
        return []
    
    result = []
    placeholders = ', '.join(['%s'] * len(sales_team_emails))
    
    for i in range(5):  # Last 5 months including current
        month_start = (getdate(nowdate()) - relativedelta(months=i)).replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
        
        # Get total sales for all salespeople
        sales = frappe.db.sql(f"""
            SELECT COALESCE(SUM(grand_total), 0) 
            FROM `tabSales Order`
            WHERE owner IN ({placeholders}) 
            AND docstatus = 1 
            AND transaction_date BETWEEN %s AND %s
        """, sales_team_emails + [month_start, month_end])[0][0] or 0
        
        # Get total returns for all salespeople
        returns = frappe.db.sql(f"""
            SELECT COALESCE(SUM(grand_total), 0) 
            FROM `tabSales Invoice`
            WHERE owner IN ({placeholders}) 
            AND is_return = 1 
            AND docstatus = 1 
            AND posting_date BETWEEN %s AND %s
        """, sales_team_emails + [month_start, month_end])[0][0] or 0
        
        result.append({
            "month": month_start.strftime('%b %Y'),
            "sales": sales,
            "returns": returns,
            "net_sales": sales - abs(returns)  # Add net sales (sales minus returns)
        })
    
    # Return in chronological order (oldest first)
    return result

@frappe.whitelist()
def customer_annual_billing(customer):
    return frappe.db.sql("""
        SELECT SUM(grand_total) FROM `tabSales Invoice`
        WHERE customer = %s AND docstatus = 1
        AND posting_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 12 MONTH) AND CURDATE()
    """, customer)[0][0] or 0

@frappe.whitelist()
def customer_total_unpaid(customer):
    return frappe.db.sql("""
        SELECT SUM(outstanding_amount) FROM `tabSales Invoice`
        WHERE customer = %s AND docstatus = 1
    """, customer)[0][0] or 0

@frappe.whitelist()
def get_customer_dashboard_info(customer):
    return {
        "Opportunity": frappe.db.count("Opportunity", {"customer": customer}),
        "Quotation": frappe.db.count("Quotation", {"customer": customer}),
        "Sales Order": frappe.db.count("Sales Order", {"customer": customer}),
        "Delivery Note": frappe.db.count("Delivery Note", {"customer": customer}),
        "Sales Invoice": frappe.db.count("Sales Invoice", {"customer": customer}),
        "Payment Entry": frappe.db.count("Payment Entry", {"party": customer}),
        "Bank Account": frappe.db.count("Bank Account", {"party": customer}),
        "Pricing Rule": frappe.db.count("Pricing Rule", {"customer": customer}),
        "Dunning": frappe.db.count("Dunning", {"customer": customer}),
    }

@frappe.whitelist()
def quick_stats():
    user = frappe.session.user
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

    try:
        permitted_item_groups = get_permitted_documents("Item Group")
    except Exception as e:
        frappe.log_error("Item Group permission error", str(e))
        permitted_item_groups = []

    if permitted_item_groups:
        formatted = "', '".join(permitted_item_groups)
        product_count = frappe.db.sql(f"""
            SELECT COUNT(*) FROM `tabItem`
            WHERE disabled = 0 AND item_group IN ('{formatted}')
        """)[0][0]
    else:
        product_count = frappe.db.count("Item", {"disabled": 0})

    try:
        permitted_customer_groups = get_permitted_documents("Customer Group")
    except Exception as e:
        frappe.log_error("Customer Group permission error", str(e))
        permitted_customer_groups = []

    if permitted_customer_groups:
        formatted = "', '".join(permitted_customer_groups)
        customer_count = frappe.db.sql(f"""
            SELECT COUNT(*) FROM `tabCustomer`
            WHERE disabled = 0 AND customer_group IN ('{formatted}')
        """)[0][0]
    else:
        customer_count = frappe.db.count("Customer", {"disabled": 0})

    orders_today = frappe.db.count("Sales Order", {
        "docstatus": 1,
        "transaction_date": frappe.utils.nowdate(),
        "owner": user
    })

    deliveries = frappe.db.count("Delivery Note", {
        "docstatus": 1,
        "posting_date": frappe.utils.nowdate(),
        "owner": user
    })

    return {
        "products": product_count,
        "customers": customer_count,
        "orders_today": orders_today,
        "deliveries": deliveries
    }

@frappe.whitelist()
def sales_by_item():
    user = frappe.session.user

    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
    try:
        permitted_item_groups = get_permitted_documents("Item Group")
    except Exception as e:
        frappe.log_error("sales_by_item: permission error", str(e))
        permitted_item_groups = []

    if not permitted_item_groups:
        return []

    formatted = "', '".join(permitted_item_groups)

    results = frappe.db.sql(f"""
        SELECT sii.item_name, SUM(sii.amount) AS total
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
        AND sii.item_group IN ('{formatted}')
        AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY sii.item_name
        ORDER BY total DESC
        LIMIT 10
    """, as_dict=True)

    return results

# @frappe.whitelist()
# def recent_sales_orders():
#     return frappe.db.sql("""
#         SELECT name, customer, status, grand_total
#         FROM `tabSales Order`
#         WHERE docstatus != 0
#         AND status != 'Completed'
#         ORDER BY creation DESC
#         LIMIT 5
#     """, as_dict=True)

@frappe.whitelist()
def recent_sales_orders():
    user = frappe.session.user
    return frappe.db.sql("""
        SELECT name, customer, status, grand_total
        FROM `tabSales Order`
        WHERE docstatus != 0
        AND status != 'Completed'
        AND owner = %s
        ORDER BY creation DESC
        LIMIT 5
    """, (user,), as_dict=True)
    
@frappe.whitelist()
def recent_sales_orders_by_salesman():
    user = frappe.session.user
    return frappe.db.sql("""
        SELECT name, customer, status, grand_total
        FROM `tabSales Order`
        WHERE docstatus != 0
        AND status != 'Completed'
        AND owner = %s
        ORDER BY creation DESC
        LIMIT 5
    """, (user,), as_dict=True)

# @frappe.whitelist()
# def item_stock_balance():
#     from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
#     from frappe.utils import flt

#     user = frappe.session.user
#     permitted_items = get_permitted_documents("Item")

#     condition = ""
#     if permitted_items:
#         formatted_items = "', '".join(permitted_items)
#         condition = f"AND item.name IN ('{formatted_items}')"

#     data = frappe.db.sql(f"""
#         SELECT 
#             item.name as item_code,
#             item.item_name,
#             item.image,
#             SUM(bin.actual_qty) AS stock_qty
#         FROM `tabBin` bin
#         JOIN `tabItem` item ON bin.item_code = item.name
#         WHERE bin.actual_qty > 0 {condition}
#         GROUP BY item.name
#         ORDER BY stock_qty DESC
#         LIMIT 50
#     """, as_dict=True)

#     stock_map = {}
#     for row in data:
#         code = row.get("item_code")
#         name = (row.get("item_name") or "").strip()
#         qty = flt(row.get("stock_qty") or 0)
#         image = row.get("image") or ""

#         if code:
#             stock_map[code] = {
#                 "item_code": code,
#                 "item_name": name,
#                 "stock_qty": qty,
#                 "image": image
#             }

#     return list(stock_map.values())

@frappe.whitelist()
def item_stock_balance():
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
    from frappe.utils import flt

    user = frappe.session.user
    permitted_items = get_permitted_documents("Item")
    permitted_warehouses = get_permitted_documents("Warehouse")

    # Build item condition
    item_condition = ""
    if permitted_items:
        formatted_items = "', '".join(permitted_items)
        item_condition = f"AND item.name IN ('{formatted_items}')"

    # Build warehouse condition for salesman filtering
    warehouse_condition = ""
    if permitted_warehouses:
        formatted_warehouses = "', '".join(permitted_warehouses)
        warehouse_condition = f"AND bin.warehouse IN ('{formatted_warehouses}')"

    data = frappe.db.sql(f"""
        SELECT 
            item.name as item_code,
            item.item_name,
            item.image,
            SUM(bin.actual_qty) AS stock_qty
        FROM `tabBin` bin
        JOIN `tabItem` item ON bin.item_code = item.name
        WHERE bin.actual_qty > 0 {item_condition} {warehouse_condition}
        GROUP BY item.name
        ORDER BY stock_qty DESC
        LIMIT 50
    """, as_dict=True)

    stock_map = {}
    for row in data:
        code = row.get("item_code")
        name = (row.get("item_name") or "").strip()
        qty = flt(row.get("stock_qty") or 0)
        image = row.get("image") or ""

        if code:
            stock_map[code] = {
                "item_code": code,
                "item_name": name,
                "stock_qty": qty,
                "image": image
            }

    return list(stock_map.values())

@frappe.whitelist()
def get_item_list():
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

    permitted_item_groups = get_permitted_documents("Item Group")

    if not permitted_item_groups:
        return []

    formatted = "', '".join(permitted_item_groups)

    return frappe.db.sql(f"""
        SELECT 
            i.name,
            i.item_name,
            i.item_group,
            i.stock_uom,
            i.image,  -- Include image field
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


@frappe.whitelist()
def get_supervisor_item_list():
    """
    Get list of items with stock information for supervisor's view.
    Includes stock from all warehouses under the supervisor's territory.
    """
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
    
    # Debug: Log the current user and roles
    current_user = frappe.session.user
    user_roles = frappe.get_roles()
    frappe.log_error(f"Current user: {current_user}, Roles: {user_roles}", "Supervisor Item List Debug")
    
    # Get all salesmen under supervisor's territory
    salesmen = _salesmen_under_perm()
    frappe.log_error(f"Found {len(salesmen)} salesmen under supervisor", "Supervisor Item List Debug")
    
    if not salesmen:
        frappe.log_error("No salesmen found under supervisor", "Supervisor Item List Debug")
        return {
            'items': [],
            'summary': {
                'total_items': 0,
                'total_stock': 0,
                'total_value': 0.0,
                'warehouse_count': 0,
                'salesman_count': 0
            }
        }
    
    # Get all warehouses accessible by these salesmen
    warehouse_list = []
    for salesman in salesmen:
        try:
            username = salesman.get('user') if isinstance(salesman, dict) else salesman
            # Debug: Log the salesman being processed
            frappe.log_error(f"Processing salesman: {username}", "Supervisor Item List Debug")
            
            # Get warehouses for each salesman
            warehouses = get_permitted_documents("Warehouse", user=username) or []
            frappe.log_error(f"Warehouses for {username}: {warehouses}", "Supervisor Item List Debug")
            
            warehouse_list.extend(warehouses)
        except Exception as e:
            frappe.log_error(f"Error getting warehouses for salesman {username}: {str(e)}", "Supervisor Item List Error")
    
    # Remove duplicates while preserving order
    seen = set()
    warehouse_list = [x for x in warehouse_list if not (x in seen or seen.add(x))]
    frappe.log_error(f"Final warehouse list: {warehouse_list}", "Supervisor Item List Debug")
    
    if not warehouse_list:
        frappe.log_error("No warehouses found for any salesman", "Supervisor Item List Debug")
        return {
            'items': [],
            'summary': {
                'total_items': 0,
                'total_stock': 0,
                'total_value': 0.0,
                'warehouse_count': 0,
                'salesman_count': len(salesmen)
            }
        }
    
    # Get all item groups visible to supervisor
    permitted_item_groups = get_permitted_documents("Item Group") or []
    frappe.log_error(f"Permitted item groups: {permitted_item_groups}", "Supervisor Item List Debug")
    
    if not permitted_item_groups:
        frappe.log_error("No item groups found for supervisor", "Supervisor Item List Debug")
        return {
            'items': [],
            'summary': {
                'total_items': 0,
                'total_stock': 0,
                'total_value': 0.0,
                'warehouse_count': len(warehouse_list),
                'salesman_count': len(salesmen)
            }
        }
    
    # Debug: Log the SQL query parameters
    frappe.log_error(f"SQL Params - Warehouses: {warehouse_list}, Item Groups: {permitted_item_groups}", "Supervisor Item List Debug")
    
    # Get items with stock information using parameterized query
    items = frappe.db.sql("""
        SELECT 
            i.name,
            i.item_name,
            i.item_group,
            i.stock_uom,
            i.image,
            ip.price_list_rate AS price,
            SUM(IFNULL(b.actual_qty, 0)) AS actual_qty,
            GROUP_CONCAT(DISTINCT b.warehouse SEPARATOR ', ') AS warehouses,
            COUNT(DISTINCT b.warehouse) AS warehouse_count
        FROM `tabItem` i
        LEFT JOIN `tabItem Price` ip 
            ON ip.item_code = i.name 
            AND ip.price_list = 'Standard Selling'
            AND ip.selling = 1
        LEFT JOIN `tabBin` b ON b.item_code = i.name
            AND b.warehouse IN %(warehouses)s
        WHERE i.disabled = 0
        AND i.item_group IN %(item_groups)s
        GROUP BY i.name
        HAVING actual_qty > 0
        ORDER BY i.item_name
        LIMIT 1000
    """, {
        'warehouses': warehouse_list,
        'item_groups': tuple(permitted_item_groups)
    }, as_dict=1)
    
    frappe.log_error(f"Found {len(items)} items in query", "Supervisor Item List Debug")
    
    # Calculate summary statistics
    total_items = len(items)
    total_stock = sum((item.actual_qty or 0) for item in items)
    total_value = sum(((item.actual_qty or 0) * (item.price or 0)) for item in items)
    
    return {
        'items': items,
        'summary': {
            'total_items': total_items,
            'total_stock': total_stock,
            'total_value': float(total_value) if total_value else 0.0,
            'warehouse_count': len(warehouse_list),
            'salesman_count': len(salesmen)
        }
    }

@frappe.whitelist()
def get_item_detail(item_code):
    item = frappe.get_doc("Item", item_code)
    item_price = frappe.db.get_value("Item Price", {
        "item_code": item_code,
        "price_list": "Standard Selling"
    }, "price_list_rate")

    stock_qty = frappe.db.sql("""
        SELECT SUM(actual_qty) FROM `tabBin`
        WHERE item_code = %s
    """, (item_code,))[0][0] or 0

    return {
        "name": item.name,
        "item_name": item.item_name,
        "description": item.description,
        "stock_uom": item.stock_uom,
        "item_group": item.item_group,
        "image": item.image,
        "price": item_price,
        "stock_qty": stock_qty,
    }
@frappe.whitelist()
def get_item_stock_ledger(item_code):
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
    permitted_warehouses = get_permitted_documents("Warehouse")
    if not permitted_warehouses:
        return []  
    formatted_warehouses = "', '".join(permitted_warehouses)
    return frappe.db.sql(f"""
        SELECT posting_date, warehouse, actual_qty, qty_after_transaction, voucher_type, voucher_no
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
        AND warehouse IN ('{formatted_warehouses}')
        ORDER BY posting_date DESC, creation DESC
        LIMIT 20
    """, item_code, as_dict=True)
# @frappe.whitelist()
# def get_material_requests():
#     from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
#     user = frappe.session.user
#     permitted_warehouses = get_permitted_documents("Warehouse")
#     if not permitted_warehouses:
#         return []
#     placeholders = ', '.join(['%s'] * len(permitted_warehouses))
#     results = frappe.db.sql(f"""
#         SELECT 
#             name, material_request_type, schedule_date, status, per_ordered, per_received, docstatus, transaction_date,
#             set_warehouse, company
#         FROM `tabMaterial Request`
#         WHERE docstatus < 2
#         AND status != 'Cancelled'
#         AND set_warehouse IN ({placeholders})
#         ORDER BY creation DESC
#         LIMIT 50
#     """, tuple(permitted_warehouses), as_dict=True)
#     return results

@frappe.whitelist()
def get_material_requests():
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
    user = frappe.session.user
    permitted_warehouses = get_permitted_documents("Warehouse")
    if not permitted_warehouses:
        return []
    
    placeholders = ', '.join(['%s'] * len(permitted_warehouses))
    
    # Get material requests with related stock entries and pending status
    material_requests = frappe.db.sql(f"""
        SELECT 
            mr.name, 
            mr.material_request_type, 
            mr.schedule_date, 
            mr.status, 
            mr.per_ordered, 
            mr.per_received, 
            mr.docstatus,
            mr.transaction_date,
            mr.set_warehouse, 
            mr.company,
            GROUP_CONCAT(DISTINCT sed.parent) as stock_entries,
            GROUP_CONCAT(DISTINCT se.docstatus) as stock_entry_docstatuses,
            CASE 
                WHEN COUNT(se.name) = 0 THEN 'No Stock Entries'
                WHEN SUM(CASE WHEN se.docstatus = 1 THEN 1 ELSE 0 END) = 0 THEN 'Draft'
                WHEN SUM(CASE WHEN se.docstatus = 1 THEN 1 ELSE 0 END) > 0 
                     AND SUM(CASE WHEN se.docstatus = 0 THEN 1 ELSE 0 END) > 0 THEN 'Partially Received'
                WHEN SUM(CASE WHEN se.docstatus = 1 THEN 1 ELSE 0 END) = COUNT(se.name) THEN 'Completed'
                ELSE 'Pending'
            END as stock_status
        FROM 
            `tabMaterial Request` mr
        LEFT JOIN 
            `tabStock Entry Detail` sed
            ON sed.material_request = mr.name
        LEFT JOIN
            `tabStock Entry` se
            ON se.name = sed.parent
            AND se.docstatus < 2
            AND se.purpose = 'Material Transfer'
        WHERE 
            mr.docstatus < 2
            AND mr.status != 'Cancelled'
            AND mr.set_warehouse IN ({placeholders})
        GROUP BY 
            mr.name
        ORDER BY 
            mr.creation DESC
        LIMIT 50
    """, tuple(permitted_warehouses), as_dict=True)
    
    # Process the results to format stock entry information
    for mr in material_requests:
        if mr.stock_entries:
            # Convert comma-separated values to lists
            mr.stock_entries = mr.stock_entries.split(',') if mr.stock_entries else []
            mr.stock_entry_docstatuses = [int(d) for d in mr.stock_entry_docstatuses.split(',')] if mr.stock_entry_docstatuses else []
        else:
            mr.stock_entries = []
            mr.stock_entry_docstatuses = []
            mr.stock_status = 'No Stock Entries'
    
    return material_requests


@frappe.whitelist()
def get_material_request_detail(name):
    if not name:
        frappe.throw("Material Request name is required")
    doc = frappe.get_doc("Material Request", name)
    return {
        "name": doc.name,
        "material_request_type": doc.material_request_type,
        "transaction_date": doc.transaction_date,
        "schedule_date": doc.schedule_date,
        "set_warehouse": doc.set_warehouse,
        "company": doc.company,
        "status": doc.status,
        "per_ordered": doc.per_ordered,
        "per_received": doc.per_received,
        "docstatus": doc.docstatus,
        "items": [
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "uom": item.uom
            }
            for item in doc.items
        ]
    }
@frappe.whitelist()
def supervisor_summary():
    from frappe.utils import today, add_days

    try:
        # Total sales in last 7 days
        total_sales = frappe.db.sql("""
            SELECT SUM(grand_total)
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """)[0][0] or 0

        # Total collections in last 7 days
        total_collections = frappe.db.sql("""
            SELECT SUM(paid_amount)
            FROM `tabPayment Entry`
            WHERE docstatus = 1 AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """)[0][0] or 0

        # Active salesmen in last 7 days (distinct owners of sales invoices)
        active_salesmen = frappe.db.sql("""
            SELECT COUNT(DISTINCT owner)
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """)[0][0] or 0

        # Sales visits in the last 7 days
        visits = frappe.db.count("Sales Visit Log", {
            "visit_time": ["between", [add_days(today(), -7), today()]]
        })

        # Orders in the last 7 days
        orders = frappe.db.count("Sales Order", {
            "docstatus": 1,
            "transaction_date": ["between", [add_days(today(), -7), today()]]
        })

        return {
            "total_sales": total_sales,
            "total_collections": total_collections,
            "active_salesmen": active_salesmen,
            "visits": visits,
            "orders": orders
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "supervisor_summary error")
        return {
            "total_sales": 0,
            "total_collections": 0,
            "active_salesmen": 0,
            "visits": 0,
            "orders": 0,
            "error": str(e)
        }
import frappe
from frappe import _
from frappe.utils import nowdate

@frappe.whitelist()
def create_material_request(data=None):
    import json

    if isinstance(data, str):
        data = json.loads(data)

    if not data:
        frappe.throw(_("No data received"))

    user = frappe.session.user

    # Get Warehouse from User Permissions
    target_warehouse = frappe.db.get_value("User Permission", {
        "user": user,
        "allow": "Warehouse"
    }, "for_value")

    if not target_warehouse:
        frappe.throw(_("No Warehouse permission found for this user."))

    # Get Cost Center from User Permissions
    cost_center = frappe.db.get_value("User Permission", {
        "user": user,
        "allow": "Cost Center"
    }, "for_value")

    if not cost_center:
        frappe.throw(_("No Cost Center permission found for this user."))

    # Create Material Request
    doc = frappe.new_doc("Material Request")
    doc.material_request_type = "Material Transfer"
    doc.set_warehouse = target_warehouse
    doc.schedule_date = data.get("required_by") or nowdate()

    for item in data.get("items", []):
        if not item.get("item_code") or not item.get("qty"):
            continue

        doc.append("items", {
            "item_code": item.get("item_code"),
            "item_name": item.get("item_name") or "",
            "qty": float(item.get("qty")),
            "uom": item.get("uom") or "Nos",
            "schedule_date": doc.schedule_date,
            "warehouse": target_warehouse,
            "cost_center": cost_center,
        })

    doc.insert(ignore_permissions=True)
    #doc.submit()
    return {"message": "Material Request created", "name": doc.name, "status": "Draft"}


@frappe.whitelist()
def get_defaults():
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

    user = frappe.session.user

    # Require user-permitted Warehouse
    warehouse = None
    permitted_warehouses = get_permitted_documents("Warehouse")
    if permitted_warehouses:
        warehouse = permitted_warehouses[0]
    else:
        frappe.throw(_("No Warehouse permission found for this user."))

    # Require user-permitted Cost Center
    cost_center = None
    permitted_cost_centers = get_permitted_documents("Cost Center")
    if permitted_cost_centers:
        cost_center = permitted_cost_centers[0]
    else:
        frappe.throw(_("No Cost Center permission found for this user."))

    return {
        "user": user,
        "warehouse": warehouse,
        "cost_center": cost_center,
    }
@frappe.whitelist()
def get_extended_stats():
    user = frappe.session.user

    payment_count = frappe.get_all(
        "Payment Entry",
        filters={"docstatus": 1},
        fields=["name"],
        ignore_permissions=False
    )

    invoice_count = frappe.get_all(
        "Sales Invoice",
        filters={"docstatus": 1},
        fields=["name"],
        ignore_permissions=False
    )

    return {
        "payments": len(payment_count),
        "invoices": len(invoice_count)
    }
@frappe.whitelist()
def invoice_vs_payment_by_day():
    from frappe.utils import nowdate, add_days
    today = nowdate()
    start_date = add_days(today, -6)

    # Invoices
    invoices = frappe.db.sql("""
        SELECT posting_date, SUM(grand_total) AS total
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s
        GROUP BY posting_date
    """, (start_date, today), as_dict=True)

    # Payments
    payments = frappe.db.sql("""
        SELECT posting_date, SUM(paid_amount) AS total
        FROM `tabPayment Entry`
        WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s
        GROUP BY posting_date
    """, (start_date, today), as_dict=True)

    # Merge by date
    date_map = {}
    for row in invoices:
        date_map[row["posting_date"]] = {"date": row["posting_date"], "invoices": row["total"], "payments": 0}
    for row in payments:
        if row["posting_date"] in date_map:
            date_map[row["posting_date"]]["payments"] = row["total"]
        else:
            date_map[row["posting_date"]] = {"date": row["posting_date"], "invoices": 0, "payments": row["total"]}

    return list(date_map.values())
@frappe.whitelist()
def get_customer_dashboard_info(customer):
    result = {}

    # Total Orders
    result["total_orders"] = frappe.db.count("Sales Order", {"customer": customer, "docstatus": 1})

    # Total Invoices
    result["total_invoices"] = frappe.db.count("Sales Invoice", {"customer": customer, "docstatus": 1})

    # Delivered Quantity
    result["delivered_qty"] = frappe.db.sql("""
        SELECT SUM(qty) FROM `tabDelivery Note Item`
        WHERE parent IN (
            SELECT name FROM `tabDelivery Note`
            WHERE docstatus = 1 AND customer = %s
        )
    """, (customer,))[0][0] or 0

    # Last Order Date
    result["last_order_date"] = frappe.db.get_value("Sales Order",
        {"customer": customer, "docstatus": 1},
        "transaction_date", order_by="transaction_date desc") or "-"

    # Last Invoice Date
    result["last_invoice_date"] = frappe.db.get_value("Sales Invoice",
        {"customer": customer, "docstatus": 1},
        "posting_date", order_by="posting_date desc") or "-"

    # Average Order Value
    total_order_amount = frappe.db.sql("""
        SELECT SUM(grand_total) FROM `tabSales Order`
        WHERE customer = %s AND docstatus = 1
    """, (customer,))[0][0] or 0

    if result["total_orders"] > 0:
        result["average_order_value"] = round(total_order_amount / result["total_orders"], 2)
    else:
        result["average_order_value"] = 0

    # Top 3 Sold Items
    result["top_items"] = frappe.db.sql("""
        SELECT item_name, SUM(qty) as total_qty
        FROM `tabSales Invoice Item`
        WHERE parent IN (
            SELECT name FROM `tabSales Invoice`
            WHERE docstatus = 1 AND customer = %s
        )
        GROUP BY item_name
        ORDER BY total_qty DESC
        LIMIT 3
    """, (customer,), as_dict=True)

    return result

@frappe.whitelist()
def get_new_events():
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    is_supervisor = "Sales Supervisor" in roles

    events = {
        "new_order": False,
        "order_name": None,
        "new_visit": False,
        "customer": None,
        "stock_update": False,
        "new_customer": False,
        "customer_name": None,
        "payment_received": False,
        "amount": None,
    }

    time_limit = now_datetime() - timedelta(minutes=30)
    time_filter = [">", time_limit]

    allowed_companies = _user_permissions(user, "Company")
    allowed_territories = _user_permissions(user, "Territory")

    so_filters = {"docstatus": 1, "creation": time_filter}
    if is_supervisor:
        if allowed_companies:
            so_filters["company"] = ["in", allowed_companies]
        if allowed_territories:
            so_filters["territory"] = ["in", allowed_territories]
    else:
        so_filters["owner"] = user

    order = frappe.db.get_value(
        "Sales Order",
        so_filters,
        "name",
        order_by="creation desc"
    )
    if order:
        events["new_order"] = True
        events["order_name"] = order

    # ---------------- Visit Plan (optional) ----------------
    # If you later want to enable this, keep same role rules:
    # vp_filters = {"status": "Planned", "creation": time_filter}
    # if is_supervisor:
    #     if allowed_territories:
    #         vp_filters["territory"] = ["in", allowed_territories]
    # else:
    #     vp_filters["owner"] = user
    #
    # visit_customer = frappe.db.get_value(
    #     "Sales Visit Log", vp_filters, "customer", order_by="creation desc"
    # )
    # if visit_customer:
    #     events["new_visit"] = True
    #     events["customer"] = visit_customer

    # ---------------- Stock Entry ----------------
    se_filters = {"docstatus": 1, "creation": time_filter}
    if is_supervisor:
        if allowed_companies:
            se_filters["company"] = ["in", allowed_companies]
        # (Stock Entry doesn't have territory; skip)
    else:
        se_filters["owner"] = user

    if frappe.db.exists("Stock Entry", se_filters):
        events["stock_update"] = True

    # ---------------- New Customer ----------------
    cust_filters = {"creation": time_filter}
    if is_supervisor:
        if allowed_territories:
            cust_filters["territory"] = ["in", allowed_territories]
    else:
        cust_filters["owner"] = user

    customer_name = frappe.db.get_value(
        "Customer", cust_filters, "customer_name", order_by="creation desc"
    )
    if customer_name:
        events["new_customer"] = True
        events["customer_name"] = customer_name

    # ---------------- Payment Entry (Receive) ----------------
    # Note: party on Payment Entry is a Customer; for Sales User we use owner=user.
    if is_supervisor:
        # Start with company filter (simple and indexed)
        pe_filters = {
            "docstatus": 1,
            "creation": time_filter,
            "party_type": "Customer",
            "payment_type": "Receive",
        }
        if allowed_companies:
            pe_filters["company"] = ["in", allowed_companies]

        payment_amount = frappe.db.get_value(
            "Payment Entry",
            pe_filters,
            "paid_amount",
            order_by="creation desc"
        )

        # If territory restrictions exist, join to Customer to enforce territory
        if not payment_amount and allowed_territories:
            rows = frappe.db.sql(
                """
                SELECT pe.paid_amount
                FROM `tabPayment Entry` pe
                JOIN `tabCustomer` c
                    ON c.name = pe.party AND pe.party_type = 'Customer'
                WHERE pe.docstatus = 1
                  AND pe.payment_type = 'Receive'
                  AND pe.creation > %(limit)s
                  AND IFNULL(c.territory,'') IN %(terrs)s
                ORDER BY pe.creation DESC
                LIMIT 1
                """,
                {"limit": time_limit, "terrs": tuple(allowed_territories)},
                as_dict=True,
            )
            if rows:
                payment_amount = rows[0]["paid_amount"]
    else:
        # Sales User: only payments they created
        payment_amount = frappe.db.get_value(
            "Payment Entry",
            {
                "docstatus": 1,
                "creation": time_filter,
                "party_type": "Customer",
                "payment_type": "Receive",
                "owner": user,
            },
            "paid_amount",
            order_by="creation desc",
        )

    if payment_amount:
        events["payment_received"] = True
        events["amount"] = payment_amount

    return events

def _user_permissions(user: str, doctype: str) -> list[str]:
    """Return a list of values from User Permission for `doctype` (e.g., Company, Territory)."""
    return frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": doctype},
        pluck="for_value",
    ) or []

    
@frappe.whitelist()
def create_sales_order(**kwargs):
    try:
        customer = kwargs.get("customer")
        delivery_date = kwargs.get("delivery_date")
        taxes_and_charges = kwargs.get("taxes_and_charges")
        items = kwargs.get("items")

        items = frappe.parse_json(items) if isinstance(items, str) else items

        if not customer:
            frappe.throw(_("Customer is required"))

        if not delivery_date:
            frappe.throw(_("Delivery date is required"))

        if not items or not isinstance(items, list):
            frappe.throw(_("No items provided"))

        valid_items = []

        for item in items:
            item_code = item.get("item_code")
            qty = float(item.get("qty") or 0)

            if not item_code:
                continue

            if qty <= 0:
                continue

            price = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": item_code,
                    "selling": 1,
                    "price_list": "Standard Selling"
                },
                "price_list_rate"
            )

            # if not price:
            #     frappe.throw(_("Missing price for item: {0}").format(item_code))

            valid_items.append({
                "item_code": item_code,
                "qty": qty,
                # "rate": price
            })

        if not valid_items:
            frappe.throw(_("No valid items with rates to create Sales Order."))

        doc = frappe.new_doc("Sales Order")
        doc.customer = customer
        doc.delivery_date = delivery_date
        doc.taxes_and_charges = taxes_and_charges

        for it in valid_items:
            doc.append("items", it)

        if taxes_and_charges:
            tax_template = frappe.get_doc("Sales Taxes and Charges Template", taxes_and_charges)
            doc.taxes = []

            for t in tax_template.taxes:
                doc.append("taxes", {
                    "charge_type": t.charge_type,
                    "account_head": t.account_head,
                    "rate": t.rate,
                    "description": t.description
                })

        doc.calculate_taxes_and_totals()

        doc.insert(ignore_permissions=True)
        doc.submit()

        return {
            "name": doc.name,
            "total": doc.total,
            "net_total": doc.net_total,
            "grand_total": doc.grand_total,
            "total_taxes_and_charges": doc.total_taxes_and_charges,
            "in_words": doc.in_words,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_sales_order Error")
        frappe.throw(_("Failed to create Sales Order: {0}").format(str(e)))

# @frappe.whitelist()
# def create_sales_order(**kwargs):
#     try:

#         if frappe.request and frappe.request.method == "POST":
#             data = frappe.request.get_json() or {}
#         else:
#             data = kwargs

#         customer = data.get("customer")
#         delivery_date = data.get("delivery_date")
#         taxes_and_charges = data.get("taxes_and_charges")
#         items = data.get("items")
#         company = data.get("company")  # optional from app
#         price_list = data.get("price_list")  # optional from app

#         if not customer:
#             frappe.throw(_("Customer is required"))

#         if not delivery_date:
#             frappe.throw(_("Delivery date is required"))

#         if isinstance(items, str):
#             items = frappe.parse_json(items)

#         if not items or not isinstance(items, list):
#             frappe.throw(_("No items provided"))

#         if not company:
#             company = (
#                 frappe.defaults.get_user_default("Company")
#                 or frappe.db.get_single_value("Global Defaults", "default_company")
#             )

#         if not company:
#             frappe.throw(_("Please specify Company"))

#         if not price_list:
#             price_list = frappe.db.get_value("Customer", customer, "default_price_list")

#         if not price_list:
#             price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")

#         if not price_list:
#             price_list = "Standard Selling"

#         valid_items = []

#         for item in items:
#             item_code = (item or {}).get("item_code")
#             qty = flt((item or {}).get("qty") or 0)
#             rate = flt((item or {}).get("rate") or 0)  # app can send rate

#             if not item_code:
#                 continue

#             if qty <= 0:
#                 continue
#             if rate <= 0:
#                 rate = flt(
#                     frappe.db.get_value(
#                         "Item Price",
#                         {
#                             "item_code": item_code,
#                             "price_list": price_list,
#                             "selling": 1,
#                             "company": company,
#                         },
#                         "price_list_rate",
#                     )
#                     or 0
#                 )

#             if rate <= 0:
#                 frappe.throw(
#                     _("Missing rate for item {0} in Price List {1}").format(item_code, price_list)
#                 )

#             valid_items.append({
#                 "item_code": item_code,
#                 "qty": qty,
#                 "rate": rate,
#             })

#         if not valid_items:
#             frappe.throw(_("No valid items with rates to create Sales Order."))

#         doc = frappe.new_doc("Sales Order")
#         doc.customer = customer
#         doc.delivery_date = delivery_date
#         doc.company = company
#         doc.taxes_and_charges = taxes_and_charges
#         doc.selling_price_list = price_list

#         for it in valid_items:
#             doc.append("items", it)

#         doc.set_missing_values()

#         if taxes_and_charges:
#             try:
#                 tax_template = frappe.get_doc("Sales Taxes and Charges Template", taxes_and_charges)
#             except frappe.DoesNotExistError:
#                 frappe.throw(_("Tax template {0} does not exist").format(taxes_and_charges))

#             doc.set("taxes", [])
#             for t in tax_template.taxes:
#                 doc.append("taxes", {
#                     "charge_type": t.charge_type,
#                     "account_head": t.account_head,
#                     "rate": t.rate,
#                     "description": t.description,
#                     "row_id": t.row_id if hasattr(t, "row_id") else None,
#                 })

#         doc.calculate_taxes_and_totals()

#         doc.insert(ignore_permissions=True)
#         doc.submit()

#         frappe.db.commit()

#         return {
#             "status": "success",
#             "name": doc.name,
#             "company": doc.company,
#             "price_list": doc.selling_price_list,
#             "total": doc.total,
#             "net_total": doc.net_total,
#             "grand_total": doc.grand_total,
#             "total_taxes_and_charges": doc.total_taxes_and_charges,
#             "in_words": doc.in_words,
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "create_sales_order Error")
#         frappe.throw(_("Failed to create Sales Order: {0}").format(str(e)))


@frappe.whitelist()
def get_user_profile_data():
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)

    cost_centers = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Cost Center"
        },
        pluck="for_value"
    )

    # Optional: get only first if single allowed
    default_cost_center = cost_centers[0] if cost_centers else None

    return {
        "full_name": user_doc.full_name,
        "email": user_doc.email,
        "roles": [role.role for role in user_doc.roles],
        "territories": frappe.get_all(
            "User Permission",
            filters={"user": user, "allow": "Territory"},
            pluck="for_value"
        ),
        "cost_centers": cost_centers,
        "default_cost_center": default_cost_center,
        # Add anything else needed
    }
@frappe.whitelist()
def get_payment_account(mode_of_payment):
    account = frappe.db.get_value("Mode of Payment Account",
        {"parent": mode_of_payment}, ["default_account"], as_dict=True)
    if not account:
        frappe.throw("No default account configured for this Mode of Payment")
    
    account_currency = frappe.db.get_value("Account", account.default_account, "account_currency")
    
    return {
        "paid_to": account.default_account,
        "currency": account_currency
    }
@frappe.whitelist()
def get_customer_type_options():
    try:
        docfield = frappe.get_doc("DocField", {"parent": "Customer", "fieldname": "customer_type"})
        return docfield.options.split("\n")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_customer_type_options_error")
        frappe.throw("Unable to fetch Customer Type options. Please contact Administrator.")
@frappe.whitelist()
def visit_plan_summary(filter="Day"):
    from frappe.utils import nowdate
    today = nowdate()

    if filter == "Day":
        condition = "visit_date = %(today)s"
    elif filter == "Week":
        condition = "visit_date >= DATE_SUB(%(today)s, INTERVAL 7 DAY)"
    elif filter == "Month":
        condition = "visit_date >= DATE_SUB(%(today)s, INTERVAL 30 DAY)"
    else:
        condition = "1=1"

    results = frappe.db.sql(f"""
        SELECT visit_date, status, COUNT(*) AS count
        FROM `tabSales Visit Log`
        WHERE docstatus = 1 AND {condition}
        GROUP BY visit_date, status
        ORDER BY visit_date ASC
    """, {"today": today}, as_dict=True)

    return results
import frappe

@frappe.whitelist()
def get_sales_invoice_by_order(sales_order):
    """
    Returns the first submitted Sales Invoice linked to the given Sales Order.
    """
    return frappe.get_all(
        "Sales Invoice",
        filters={"sales_order": sales_order, "docstatus": 1},
        fields=["name"],
        limit=1
    )
@frappe.whitelist()
def get_item_sales(filter=None):
    from frappe.utils import getdate, nowdate, add_days
    conditions = "si.docstatus = 1"
    today = nowdate()

    if filter == "Today":
        conditions += f" AND si.posting_date = '{today}'"
    elif filter == "Week":
        start = add_days(today, -7)
        conditions += f" AND si.posting_date BETWEEN '{start}' AND '{today}'"
    elif filter == "Month":
        start = add_days(today, -30)
        conditions += f" AND si.posting_date BETWEEN '{start}' AND '{today}'"

    results = frappe.db.sql(f"""
        SELECT sii.item_name, SUM(sii.amount) AS total
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        WHERE {conditions}
        GROUP BY sii.item_name
        ORDER BY total DESC
        LIMIT 10
    """, as_dict=True)

    return results

@frappe.whitelist()
def get_pending_stock_entries(user=None):
    """Fetch stock entries assigned to the salesman's warehouse"""
    if not user:
        user = frappe.session.user

    salesman_warehouse = frappe.db.get_value(
        "User Permission",
        {"user": user, "allow": "Warehouse"},
        "for_value"
    )

    if not salesman_warehouse:
        frappe.throw(_("No warehouse is assigned to this user."))

    stock_entries = frappe.db.sql("""
        SELECT DISTINCT se.name, se.posting_date, se.purpose, se.from_warehouse, se.to_warehouse
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.purpose = 'Material Transfer'
        AND se.docstatus = 0
        AND sed.t_warehouse = %s
        AND NOT EXISTS (
            SELECT 1 FROM `tabStock Acceptance`
            WHERE stock_entry = se.name
            AND target_warehouse = %s
        )
        ORDER BY se.creation DESC
    """, (salesman_warehouse, salesman_warehouse), as_dict=True)

    return stock_entries

@frappe.whitelist()
def accept_stock(stock_entry, remarks=None):

    if not frappe.db.exists("Stock Entry", stock_entry):
        frappe.throw(_("Stock Entry {0} not found").format(stock_entry))

    doc = frappe.get_doc("Stock Entry", stock_entry)


    salesman_warehouse = frappe.db.get_value(
        "User Permission",
        {"user": frappe.session.user, "allow": "Warehouse"},
        "for_value"
    )
    if not salesman_warehouse:
        frappe.throw(_("No warehouse is assigned to this user."))


    if not any(d.t_warehouse == salesman_warehouse for d in doc.items):
        frappe.throw(_("You are not allowed to accept this stock."))

    if frappe.db.exists("Stock Acceptance", {"stock_entry": stock_entry, "target_warehouse": salesman_warehouse}):
        frappe.throw(_("This stock entry has already been processed for your warehouse."))


    acceptance = frappe.new_doc("Stock Acceptance")
    acceptance.stock_entry = stock_entry
    acceptance.target_warehouse = salesman_warehouse
    acceptance.accepted_by = frappe.session.user
    acceptance.status = "Accepted"
    acceptance.remarks = remarks

    # Append items
    for item in doc.items:
        if item.t_warehouse == salesman_warehouse:
            acceptance.append("item", {   
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "accepted_qty": item.qty,
                "rejected_qty": 0
            })

    acceptance.insert()
    acceptance.submit()

    # Auto-submit stock entry if draft
    if doc.docstatus == 0:
        doc.flags.ignore_permissions = True
        doc.submit()

    return {"status": "success", "message": _("Stock accepted and entry submitted successfully.")}
@frappe.whitelist()
def get_dashboard_data(user=None):
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

    if not user:
        user = frappe.session.user

    # Step 1: Get permitted warehouses
    permitted_warehouses = get_permitted_documents("Warehouse")
    material_requests = []

    if permitted_warehouses:
        placeholders = ', '.join(['%s'] * len(permitted_warehouses))

        # Step 2: Fetch Material Requests
        material_requests = frappe.db.sql(f"""
            SELECT 
                name, material_request_type, schedule_date, status, docstatus, transaction_date,
                set_warehouse, company
            FROM `tabMaterial Request`
            WHERE docstatus < 2
            AND status != 'Cancelled'
            AND set_warehouse IN ({placeholders})
            ORDER BY creation DESC
            LIMIT 50
        """, tuple(permitted_warehouses), as_dict=True)
         
        # Step 3: Get all pending stock entries matching the permitted warehouses
        stock_entries = frappe.db.sql(f"""
            SELECT DISTINCT se.name AS stock_entry_name, se.posting_date, se.purpose, 
                            se.from_warehouse, se.to_warehouse, sed.t_warehouse
            FROM `tabStock Entry` se
            JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
            WHERE se.purpose = 'Material Transfer'
            AND se.docstatus = 0
            AND sed.t_warehouse IN ({placeholders})
            AND NOT EXISTS (
                SELECT 1 FROM `tabStock Acceptance`
                WHERE stock_entry = se.name
                AND target_warehouse = sed.t_warehouse
            )
            ORDER BY se.creation DESC
        """, tuple(permitted_warehouses), as_dict=True)

        # Step 4: Group stock entries by target warehouse
        stock_by_warehouse = {}
        for entry in stock_entries:
            warehouse = entry.get("t_warehouse")
            if warehouse not in stock_by_warehouse:
                stock_by_warehouse[warehouse] = []
            stock_by_warehouse[warehouse].append(entry)

        # Step 5: Add corresponding stock entries to each material request
        for req in material_requests:
            req_warehouse = req.get("set_warehouse")
            req["pending_stock_entries"] = stock_by_warehouse.get(req_warehouse, [])

    return material_requests

# @frappe.whitelist()
# def get_pending_stock_entries(material_request_name: str = None, user: str = None):
#     """
#     Fetch pending stock entries assigned to the user's warehouse,
#     filtered by Material Request name.
#     """
#     if not user:
#         user = frappe.session.user

#     if not material_request_name:
#         frappe.throw(_("Material Request name is required."))

#     # Get user's assigned warehouse
#     salesman_warehouse = frappe.db.get_value(
#         "User Permission",
#         {"user": user, "allow": "Warehouse"},
#         "for_value"
#     )

#     if not salesman_warehouse:
#         frappe.throw(_("No warehouse is assigned to this user."))

#     # Query stock entries linked to the given Material Request and warehouse
#     stock_entries = frappe.db.sql("""
#         SELECT DISTINCT 
#             se.name AS stock_entry_name, 
#             se.posting_date, 
#             se.purpose, 
#             se.from_warehouse, 
#             se.to_warehouse,
#             sed.item_code,
#             sed.qty,
#             sed.material_request,
#             sed.t_warehouse
#         FROM `tabStock Entry` se
#         JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
#         WHERE se.purpose = 'Material Transfer'
#         AND se.docstatus = 0
#         AND sed.t_warehouse = %s
#         AND sed.material_request = %s
#         AND NOT EXISTS (
#             SELECT 1 FROM `tabStock Acceptance`
#             WHERE stock_entry = se.name
#             AND target_warehouse = sed.t_warehouse
#         )
#         ORDER BY se.creation DESC
#     """, (salesman_warehouse, material_request_name), as_dict=True)

#     return stock_entries



# @frappe.whitelist()
# def get_pending_stock_entries(material_request_name: str = None, user: str = None):
#     """
#     Fetch pending and partially received stock entries assigned to the user's warehouse,
#     filtered by Material Request name.
#     """
#     if not user:
#         user = frappe.session.user

#     if not material_request_name:
#         frappe.throw(_("Material Request name is required."))

#     # Get user's assigned warehouse
#     salesman_warehouse = frappe.db.get_value(
#         "User Permission",
#         {"user": user, "allow": "Warehouse"},
#         "for_value"
#     )

#     if not salesman_warehouse:
#         frappe.throw(_("No warehouse is assigned to this user."))

#     # Get all stock entries for the material request and warehouse
#     stock_entries = frappe.db.sql("""
#         SELECT 
#             se.name AS stock_entry_name, 
#             se.posting_date, 
#             se.purpose, 
#             se.from_warehouse, 
#             se.to_warehouse,
#             sed.item_code,
#             sed.qty,
#             sed.material_request,
#             sed.t_warehouse,
#             CASE 
#                 WHEN sa.status = 'Partially Received' THEN 'Partially Received'
#                 WHEN sa.status = 'Draft' THEN 'Draft Acceptance'
#                 ELSE 'Pending'
#             END as status
#         FROM `tabStock Entry` se
#         JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
#         LEFT JOIN (
#             SELECT 
#                 stock_entry, 
#                 target_warehouse,
#                 CASE 
#                     WHEN docstatus = 1 THEN 'Partially Received'
#                     WHEN docstatus = 0 THEN 'Draft'
#                 END as status
#             FROM `tabStock Acceptance`
#             WHERE docstatus < 2
#         ) sa ON sa.stock_entry = se.name AND sa.target_warehouse = sed.t_warehouse
#         WHERE se.purpose = 'Material Transfer'
#         AND se.docstatus = 0
#         AND sed.t_warehouse = %s
#         AND sed.material_request = %s
#         GROUP BY se.name, sed.name
#         ORDER BY se.creation DESC
#     """, (salesman_warehouse, material_request_name), as_dict=True)

#     return stock_entries
    
@frappe.whitelist()
def get_pending_stock_entries(material_request_name: str = None, user: str = None):
    """
    Fetch pending and partially received stock entries assigned to the user's warehouse,
    filtered by Material Request name.
    """
    if not user:
        user = frappe.session.user

    if not material_request_name:
        frappe.throw(_("Material Request name is required."))

    # Get user's assigned warehouse
    salesman_warehouse = frappe.db.get_value(
        "User Permission",
        {"user": user, "allow": "Warehouse"},
        "for_value"
    )

    if not salesman_warehouse:
        frappe.throw(_("No warehouse is assigned to this user."))

    # Get all stock entries for the material request and warehouse
    stock_entries = frappe.db.sql("""
        SELECT 
            se.name AS stock_entry_name, 
            se.posting_date, 
            se.purpose, 
            se.from_warehouse, 
            se.to_warehouse,
            sed.item_code,
            sed.item_name,
            sed.qty,
            sed.docstatus,
            sed.material_request,
            sed.t_warehouse,
            CASE 
                WHEN sa.status = 'Partially Received' THEN 'Partially Received'
                WHEN sa.status = 'Draft' THEN 'Draft Acceptance'
                WHEN se.docstatus = 0 THEN 'Draft'
                ELSE 'Pending'
            END as status
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        LEFT JOIN (
            SELECT 
                stock_entry, 
                target_warehouse,
                CASE 
                    WHEN docstatus = 1 THEN 'Partially Received'
                    WHEN docstatus = 0 THEN 'Draft'
                END as status
            FROM `tabStock Acceptance`
            WHERE docstatus < 2
        ) sa ON sa.stock_entry = se.name AND sa.target_warehouse = sed.t_warehouse
        WHERE se.purpose = 'Material Transfer'
        AND se.docstatus < 2  -- Changed from = 1 to < 2 to include both draft and submitted entries
        AND sed.t_warehouse = %s
        AND sed.material_request = %s
        GROUP BY se.name, sed.name
        ORDER BY se.creation DESC
    """, (salesman_warehouse, material_request_name), as_dict=True)

    return stock_entries


@frappe.whitelist()
def reject_stock(stock_entry, remarks=None):
    if not frappe.db.exists("Stock Entry", stock_entry):
        frappe.throw(_("Stock Entry {0} not found").format(stock_entry))

    doc = frappe.get_doc("Stock Entry", stock_entry)
    salesman_warehouse = frappe.db.get_value(
        "User Permission",
        {"user": frappe.session.user, "allow": "Warehouse"},
        "for_value"
    )
    if not salesman_warehouse:
        frappe.throw(_("No warehouse is assigned to this user."))
    if frappe.db.exists("Stock Acceptance", {"stock_entry": stock_entry, "target_warehouse": salesman_warehouse}):
        frappe.throw(_("This stock entry has already been processed for your warehouse."))
    rejection = frappe.new_doc("Stock Acceptance")
    rejection.stock_entry = stock_entry
    rejection.target_warehouse = salesman_warehouse
    rejection.accepted_by = frappe.session.user
    rejection.status = "Rejected"
    rejection.remarks = remarks or "Rejected by salesman"
    for item in doc.items:
        if item.t_warehouse == salesman_warehouse:
            rejection.append("item", {   
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "accepted_qty": 0,
                "rejected_qty": item.qty
            })

    rejection.insert()
    rejection.submit()

    return {"status": "rejected", "message": _("Stock rejected successfully.")}

def _require_supervisor():
    """Ensure caller has Sales Supervisor (or System Manager) role."""
    roles = set(frappe.get_roles())
    if not roles & {"Sales Supervisor", "System Manager"}:
        frappe.throw(_("Only Sales Supervisor can perform this action."), frappe.PermissionError)

def _resolve_visit_plan_doctype(preferred=None):
    """Return an existing doctype for visit plans/logs."""
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates += [
        "Visit Plan",
        "Sales Visit Log",
        "Salesman Visit Log",
        "Sales Visit Plan",
        "Salesman Visit Plan",
    ]
    seen = set()
    for dt in candidates:
        if dt and dt not in seen and frappe.db.exists("DocType", dt):
            return dt
        seen.add(dt)
    frappe.throw(_("Visit plan/log doctype not found. Pass 'doctype_name' to the API."))

def _field_exists(doctype, fieldname):
    try:
        return bool(frappe.get_meta(doctype).has_field(fieldname))
    except Exception:
        return False


# def _salesmen_under_perm():
#     """
#     Return list of salesman users (no dependency on Sales Person.user_id).
#     Uses role = 'Salesman' + User Permissions to show primary warehouse/route.
#     """
#     return frappe.db.sql("""
#         SELECT
#             u.name AS user,
#             CONCAT_WS(' ', u.first_name, u.last_name) AS full_name,

#             /* If you maintain a mapping from User -> Sales Person name somewhere,
#                you can replace NULL with a subquery to fetch it. */
#             NULL AS salesman_name,

#             (SELECT up.for_value
#                FROM `tabUser Permission` up
#               WHERE up.user = u.name AND up.allow = 'Warehouse'
#               ORDER BY up.creation ASC
#               LIMIT 1) AS primary_warehouse,

#             (SELECT up2.for_value
#                FROM `tabUser Permission` up2
#               WHERE up2.user = u.name AND up2.allow IN ('Territory','Route')
#               ORDER BY up2.creation ASC
#               LIMIT 1) AS route

#         FROM `tabUser` u
#         WHERE u.enabled = 1
#           AND EXISTS (
#               SELECT 1 FROM `tabHas Role` hr
#                WHERE hr.parent = u.name AND hr.role = 'Sales User'
#           )
#         ORDER BY u.first_name, u.last_name
#     """, as_dict=True)

@frappe.whitelist()
def supervisor_list_routes_and_salesmen():
    """
    Sales Supervisor: get visible routes and salesmen.
    If you use a custom Route doctype, replace 'Territory' accordingly.
    """
    _require_supervisor()

    salesmen = _salesmen_under_perm()
    # routes = frappe.get_all(
    #     "Territory",                         
    #     filters={},                          
    #     fields=["name", "parent_territory as parent", "is_group"],
    #     order_by="lft"
    # )
    # return {"salesmen": salesmen, "routes": routes}
    return {"salesmen": salesmen}

@frappe.whitelist()
def supervisor_reassign_visit_plan(
    plan_names=None,
    from_salesman=None,
    to_salesman=None,
    reassign_date=None,
    keep_original_owner=0,      
    doctype_name=None,          
    salesman_field="salesman",  
    date_field="visit_date"     
):
    _require_supervisor()

    if not to_salesman:
        frappe.throw(_("Parameter to_salesman is required."))
    dt = _resolve_visit_plan_doctype(doctype_name)
    if not _field_exists(dt, salesman_field):
        for alt in ("salesman_user", "assigned_to", "sales_person", "salesperson"):
            if _field_exists(dt, alt):
                salesman_field = alt
                break
        else:
            frappe.throw(_("Could not find a salesman field on {0}. Pass 'salesman_field'.").format(dt))

    if not _field_exists(dt, date_field):
        for alt in ("planned_date", "schedule_date", "posting_date", "creation"):
            if _field_exists(dt, alt):
                date_field = alt
                break
    names = None
    if plan_names:
        names = json.loads(plan_names) if isinstance(plan_names, str) else plan_names
        if not isinstance(names, list):
            frappe.throw(_("plan_names must be a JSON list"))

    filters = {}
    if names:
        filters["name"] = ["in", names]
    else:
        if from_salesman:
            filters[salesman_field] = from_salesman
        if reassign_date and _field_exists(dt, date_field):
            filters[date_field] = reassign_date

    fields = ["name"]
    if _field_exists(dt, salesman_field):
        fields.append(f"{salesman_field} as current_salesman")
    if _field_exists(dt, date_field):
        fields.append(f"{date_field} as planned_date")

    plans = frappe.get_all(dt, filters=filters, fields=fields)
    if not plans:
        return {"moved": 0, "details": [], "message": _("No records matched on {0}.").format(dt)}

    moved, details = 0, []
    for p in plans:
        doc = frappe.get_doc(dt, p["name"])
        doc.set(salesman_field, to_salesman)
        try:
            frappe.share.add(dt, doc.name, to_salesman, read=1, write=1, share=0, notify=0)
        except Exception:
            pass

        old_user = p.get("current_salesman")
        if old_user and old_user != to_salesman:
            try:
                frappe.share.remove(dt, doc.name, old_user)
            except Exception:
                pass

        doc.add_comment(
            "Edit",
            text=f"Reassigned by {frappe.session.user} from {old_user} to {to_salesman}"
        )
        doc.save(ignore_permissions=True)

        moved += 1
        details.append({"name": p["name"], "from": old_user, "to": to_salesman})

    return {
        "moved": moved,
        "details": details,
        "message": _("Records reassigned on {0}. Owner not changed by design.").format(dt)
    }


# @frappe.whitelist()
# def supervisor_get_stock_balance(warehouses=None, item_code=None, page=1, page_len=50, include_zero=0):
#     """
#     Stock balance by warehouse (uses `tabBin`), respects standard perms.

#     Args:
#       warehouses: JSON list of warehouse names (optional)
#       item_code: filter by item (optional)
#       page, page_len: pagination (ints)
#       include_zero: '0' or '1' (exclude zero rows by default)
#     """
#     _require_supervisor()
#     wh_list = None
#     if warehouses:
#         try:
#             wh_list = json.loads(warehouses) if isinstance(warehouses, str) else warehouses
#             if not isinstance(wh_list, list):
#                 wh_list = None
#         except Exception:
#             wh_list = None

#     where = ["1=1"]
#     params = []

#     if wh_list and len(wh_list) > 0:
#         where.append("b.warehouse in ({})".format(", ".join(["%s"] * len(wh_list))))
#         params.extend(wh_list)

#     if item_code:
#         where.append("b.item_code = %s")
#         params.append(item_code)

#     if not cint(include_zero):
#         where.append("(b.actual_qty <> 0 OR b.reserved_qty <> 0 OR b.planned_qty <> 0)")

#     offset = (cint(page) - 1) * cint(page_len)
#     query = f"""
#         SELECT
#             b.warehouse,
#             b.item_code,
#             i.item_name,
#             b.actual_qty,
#             b.reserved_qty,
#             b.projected_qty,
#             b.valuation_rate
#         FROM `tabBin` b
#         LEFT JOIN `tabItem` i ON i.name = b.item_code
#         WHERE {" AND ".join(where)}
#         ORDER BY b.warehouse, b.item_code
#         LIMIT %s OFFSET %s
#     """
#     params.extend([cint(page_len), offset])
#     rows = frappe.db.sql(query, params, as_dict=True)

#     count_q = f"SELECT COUNT(*) AS c FROM `tabBin` b WHERE {' AND '.join(where)}"
#     total = frappe.db.sql(count_q, params[:-2], as_dict=True)[0]["c"] if rows else 0

#     return {"total": total, "rows": rows, "page": cint(page), "page_len": cint(page_len)}

def _require_supervisor():
    roles = set(frappe.get_roles())
    if not roles & {"Sales Supervisor", "System Manager"}:
        frappe.throw(_("Only Sales Supervisor can perform this action."), frappe.PermissionError)


@frappe.whitelist()
def supervisor_get_stock_balance(warehouses=None, item_code=None, page=1, page_len=50, include_zero=0, salesman=None):
    """
    Stock balance by warehouse (uses `tabBin`), respects standard perms.
    Can be filtered by salesman to show only warehouses they have access to.

    Args:
      warehouses: JSON list of warehouse names (optional)
      item_code: filter by item (optional)
      page, page_len: pagination (ints)
      include_zero: '0' or '1' (exclude zero rows by default)
      salesman: filter by salesman's warehouse permissions (optional)
    """
    _require_supervisor()
    
    # Handle warehouse filtering
    wh_list = None
    if warehouses:
        try:
            wh_list = json.loads(warehouses) if isinstance(warehouses, str) else warehouses
            if not isinstance(wh_list, list):
                wh_list = None
        except Exception:
            wh_list = None

       # If salesman is provided, filter warehouses by their permissions
    if salesman:
        try:
            # Get warehouse permissions for the specific salesman
            salesman_warehouses = []
            
            try:
                # Try to get permitted warehouses using the standard function
                from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
                salesman_warehouses = get_permitted_documents("Warehouse", user=salesman) or []
            except Exception as perm_error:
                # If get_permitted_documents fails, try alternative approach
                frappe.log_error(f"get_permitted_documents failed for {salesman}: {str(perm_error)}")
                
                # Alternative: Query User Permission table directly
                salesman_warehouses = frappe.db.sql("""
                    SELECT DISTINCT up.for_value
                    FROM `tabUser Permission` up
                    WHERE up.user = %s 
                    AND up.allow = 'Warehouse'
                    AND up.docstatus < 2
                """, [salesman], pluck=True) or []
            
            if salesman_warehouses:
                # If warehouses parameter is also provided, get intersection
                if wh_list:
                    wh_list = list(set(wh_list) & set(salesman_warehouses))
                else:
                    wh_list = salesman_warehouses
                
                # If no warehouses after filtering, return empty result
                if not wh_list:
                    return {"total": 0, "rows": [], "page": cint(page), "page_len": cint(page_len), "salesman": salesman, "message": "No warehouses assigned to this salesman"}
            else:
                # If salesman has no warehouse permissions, return empty result
                return {"total": 0, "rows": [], "page": cint(page), "page_len": cint(page_len), "salesman": salesman, "message": "No warehouse permissions found for this salesman"}
                
        except Exception as e:
            frappe.log_error(f"Error getting warehouse permissions for salesman {salesman}: {str(e)}")
            # Return more detailed error information
            return {
                "total": 0, 
                "rows": [], 
                "page": cint(page), 
                "page_len": cint(page_len), 
                "salesman": salesman, 
                "message": f"Error retrieving salesman permissions: {str(e)}"
            }
    where = ["1=1"]
    params = []

    # Only show stock if we have specific warehouses to filter by
    if wh_list and len(wh_list) > 0:
        where.append("b.warehouse in ({})".format(", ".join(["%s"] * len(wh_list))))
        params.extend(wh_list)
    elif salesman:
        # If salesman is specified but no warehouses found, return empty
        return {"total": 0, "rows": [], "page": cint(page), "page_len": cint(page_len), "salesman": salesman, "message": "No accessible warehouses for this salesman"}

    if item_code:
        where.append("b.item_code = %s")
        params.append(item_code)

    if not cint(include_zero):
        where.append("(b.actual_qty <> 0 OR b.reserved_qty <> 0 OR b.planned_qty <> 0)")

    offset = (cint(page) - 1) * cint(page_len)
    query = f"""
        SELECT
            b.warehouse,
            w.warehouse_name,
            b.item_code,
            i.item_name,
            i.image,
            b.actual_qty,
            b.reserved_qty,
            b.projected_qty,
            b.valuation_rate,
            (b.actual_qty * b.valuation_rate) as stock_value
        FROM `tabBin` b
        LEFT JOIN `tabItem` i ON i.name = b.item_code
        LEFT JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE {" AND ".join(where)}
        ORDER BY b.warehouse, b.item_code
        LIMIT %s OFFSET %s
    """
    params.extend([cint(page_len), offset])
    rows = frappe.db.sql(query, params, as_dict=True)

    count_q = f"SELECT COUNT(*) AS c FROM `tabBin` b WHERE {' AND '.join(where)}"
    total = frappe.db.sql(count_q, params[:-2], as_dict=True)[0]["c"] if rows else 0

    # Calculate summary statistics
    summary = {
        "total_items": len(set(row["item_code"] for row in rows)),
        "total_warehouses": len(set(row["warehouse"] for row in rows)),
        "total_stock_value": sum(float(row.get("stock_value") or 0) for row in rows)
    }

    result = {
        "total": total, 
        "rows": rows, 
        "page": cint(page), 
        "page_len": cint(page_len),
        "summary": summary
    }
    
    if salesman:
        result["salesman"] = salesman
        result["filtered_warehouses"] = wh_list
        result["warehouse_count"] = len(wh_list) if wh_list else 0
    
    return result

def _resolve_visit_plan_doctype(preferred=None):
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates += [
        "Visit Plan",
        "Sales Visit Log",
        "Salesman Visit Log",
        "Sales Visit Plan",
        "Salesman Visit Plan",
    ]
    seen = set()
    for dt in candidates:
        if dt and dt not in seen and frappe.db.exists("DocType", dt):
            return dt
        seen.add(dt)
    frappe.throw(_("Visit plan/log doctype not found. Pass 'doctype_name' to the API."))

def _field_exists(doctype, fieldname):
    try:
        return bool(frappe.get_meta(doctype).has_field(fieldname))
    except Exception:
        return False

def _parse_json_list(value):
    """Accepts JSON string or list; returns list or None."""
    if not value:
        return None
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None

def _date_range_from_filter(filter=None, from_date=None, to_date=None):
    """
    Supported filter values: Today, Week, Month, Year, Range
    If Range, both from_date and to_date are required (YYYY-MM-DD).
    Defaults to Today.
    """
    today = getdate(date.today())
    f = (filter or "Today").lower()

    if f == "today":
        return today, today
    if f == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end
    if f == "month":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1) - timedelta(days=1)
        return start, end
    if f == "year":
        start = getdate(f"{today.year}-01-01")
        end = getdate(f"{today.year}-12-31")
        return start, end
    if f == "range":
        if not (from_date and to_date):
            frappe.throw(_("When filter='Range', pass both from_date and to_date (YYYY-MM-DD)."))
        return getdate(from_date), getdate(to_date)

    return today, today


def _salesmen_under_perm():
    """
    Return list of salesman users filtered by supervisor's territory permissions.
    Uses User Permissions for territory assignments (standard ERPNext approach).
    """
    # Get current supervisor's permitted territories
    supervisor_territories = []
    try:
        from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
        supervisor_territories = get_permitted_documents("Territory")
    except Exception:
        pass
    
    # Build territory filter condition for User Permissions
    territory_condition = ""
    territory_params = []
    if supervisor_territories:
        placeholders = ', '.join(['%s'] * len(supervisor_territories))
        territory_condition = f"""
            AND EXISTS (
                SELECT 1 FROM `tabUser Permission` up_terr
                WHERE up_terr.user = u.name 
                AND up_terr.allow = 'Territory'
                AND up_terr.for_value IN ({placeholders})
            )
        """
        territory_params = supervisor_territories
    
    query = f"""
        SELECT DISTINCT
            u.name AS user,
            CONCAT_WS(' ', u.first_name, u.last_name) AS full_name,
            u.email,
            u.mobile_no,
            u.enabled,
            
            /* Get Employee name if linked */
            (SELECT e.employee_name FROM `tabEmployee` e 
             WHERE e.user_id = u.name LIMIT 1) AS employee_name,
            
            /* Get Employee ID if linked */
            (SELECT e.name FROM `tabEmployee` e 
             WHERE e.user_id = u.name LIMIT 1) AS employee_id,

            /* Primary warehouse from User Permissions */
            (SELECT up.for_value
               FROM `tabUser Permission` up
              WHERE up.user = u.name AND up.allow = 'Warehouse'
              ORDER BY up.creation ASC
              LIMIT 1) AS primary_warehouse,

            /* All warehouses from User Permissions as comma-separated */
            (SELECT GROUP_CONCAT(DISTINCT up.for_value SEPARATOR ', ')
               FROM `tabUser Permission` up
              WHERE up.user = u.name AND up.allow = 'Warehouse') AS all_warehouses,

            /* Primary territory from User Permissions */
            (SELECT up2.for_value
               FROM `tabUser Permission` up2
              WHERE up2.user = u.name AND up2.allow = 'Territory'
              ORDER BY up2.creation ASC
              LIMIT 1) AS route,
              
            /* All territories from User Permissions as comma-separated */
            (SELECT GROUP_CONCAT(DISTINCT up2.for_value SEPARATOR ', ')
               FROM `tabUser Permission` up2
              WHERE up2.user = u.name AND up2.allow = 'Territory') AS all_routes

        FROM `tabUser` u
        WHERE u.enabled = 1
          AND EXISTS (
              SELECT 1 FROM `tabHas Role` hr
               WHERE hr.parent = u.name AND hr.role = 'Sales User'
          )
          {territory_condition}
        ORDER BY u.first_name, u.last_name
    """
    
    # Get basic salesman data
    salesmen = frappe.db.sql(query, territory_params, as_dict=True)
    
    # Get customers by territory for each salesman
    for salesman in salesmen:
        # Get salesman's territories
        salesman_territories = []
        if salesman.get('all_routes'):
            salesman_territories = [t.strip() for t in salesman['all_routes'].split(',')]
        elif salesman.get('route'):
            salesman_territories = [salesman['route']]
        
        # Get customers in those territories
        customer_details = []
        customer_count = 0
        
        if salesman_territories:
            # Get customers from all assigned territories
            customer_details = frappe.db.sql("""
                SELECT 
                    c.name as customer_code,
                    c.customer_name,
                    c.territory,
                    c.customer_group,
                    c.disabled,
                    c.customer_type
                FROM `tabCustomer` c
                WHERE c.territory IN ({})
                AND c.disabled = 0
                ORDER BY c.customer_name
            """.format(', '.join(['%s'] * len(salesman_territories))), 
            salesman_territories, as_dict=True)
            
            customer_count = len(customer_details)
        
        # Add customer data to salesman record
        # salesman['customers'] = customer_details
        # salesman['customer_count'] = customer_count
        salesman['active_customers'] = customer_details  # All are active since we filter disabled=0
        salesman['active_customer_count'] = customer_count
        
        # Create comma-separated customer list for backward compatibility
        salesman['all_customers'] = ', '.join([c['customer_code'] for c in customer_details])
    
    return salesmen
    
def _salesmen_user_list():
    return [r["user"] for r in _salesmen_under_perm()]

@frappe.whitelist()
def supervisor_total_sales(filter="Today", from_date=None, to_date=None,
                           salesmen=None, territories=None):
    """
    Sum of Sales Invoice in company currency (base), net of returns.
    - filter: Today | Week | Month | Year | Range
    - salesmen: JSON list of user emails -> matched to si.owner (override as needed)
    - territories: JSON list of Territory names -> matched via Customer.territory
    """
    _require_supervisor()

    start, end = _date_range_from_filter(filter, from_date, to_date)
    salesman_users = _parse_json_list(salesmen)
    terr_list = _parse_json_list(territories)

    where = ["si.docstatus = 1", "si.posting_date BETWEEN %s AND %s"]
    params = [start, end]
    if salesman_users and len(salesman_users) > 0:
        where.append("si.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        params.extend(salesman_users)

    if terr_list and len(terr_list) > 0:
        where.append("c.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        params.extend(terr_list)

    sql = f"""
        SELECT
            COALESCE(SUM(CASE WHEN si.is_return = 1
                               THEN -si.base_grand_total
                               ELSE  si.base_grand_total END), 0) AS net_sales
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCustomer` c ON c.name = si.customer
        WHERE {" AND ".join(where)}
    """
    net_sales = frappe.db.sql(sql, params, as_dict=True)[0]["net_sales"] or 0.0
    return {"from_date": str(start), "to_date": str(end), "net_sales": net_sales}

@frappe.whitelist()
def supervisor_collections(filter="Today", from_date=None, to_date=None,
                           salesmen=None, territories=None):
    """
    Sum of collections (Payment Entry) in company currency.
    - Uses Payment Entry with payment_type='Receive' and docstatus=1.
    - If 'salesmen' is provided, filters by PE.owner (override to a stricter mapping if you track Salesman on PE).
    - If 'territories' is provided, joins against customer territory when Party Type is Customer.
    """
    _require_supervisor()

    start, end = _date_range_from_filter(filter, from_date, to_date)
    salesman_users = _parse_json_list(salesmen)
    terr_list = _parse_json_list(territories)

    where = ["pe.docstatus = 1", "pe.payment_type = 'Receive'", "pe.posting_date BETWEEN %s AND %s"]
    params = [start, end]

    if salesman_users and len(salesman_users) > 0:
        where.append("pe.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        params.extend(salesman_users)

    join_customer = ""
    if terr_list and len(terr_list) > 0:
        join_customer = "LEFT JOIN `tabCustomer` c ON c.name = pe.party AND pe.party_type = 'Customer'"
        where.append("c.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        params.extend(terr_list)

    sql = f"""
        SELECT COALESCE(SUM(pe.base_received_amount), 0) AS collections
        FROM `tabPayment Entry` pe
        {join_customer}
        WHERE {" AND ".join(where)}
    """
    collections = frappe.db.sql(sql, params, as_dict=True)[0]["collections"] or 0.0
    return {"from_date": str(start), "to_date": str(end), "collections": collections}

# @frappe.whitelist()
# def supervisor_today_visits_orders(doctype_name=None,
#                                    salesman_field="salesman",
#                                    date_field="visit_date",
#                                    filter="Today", from_date=None, to_date=None,
#                                    salesmen=None, territories=None):
#     """
#     KPI block: counts for Visits and Orders in selected period (default Today).
#     - doctype_name: visit/plan doctype; auto-resolves if omitted.
#     - salesman_field/date_field: field names on that doctype (auto-fallbacks are tried).
#     - salesmen: JSON list of user emails -> matched to {salesman_field} on visit log & owner on Sales Order by default.
#     - territories: JSON list of Territory names -> joins Customer.territory for both visits (if field exists) and orders.
#     Returns: { visits_count, orders_count, orders_amount }
#     """
#     _require_supervisor()

#     start, end = _date_range_from_filter(filter, from_date, to_date)
#     dt = _resolve_visit_plan_doctype(doctype_name)

#     if not _field_exists(dt, salesman_field):
#         for alt in ("salesman_user", "assigned_to", "sales_person", "salesperson", "owner"):
#             if _field_exists(dt, alt):
#                 salesman_field = alt
#                 break
#     if not _field_exists(dt, date_field):
#         for alt in ("planned_date", "schedule_date", "posting_date", "creation"):
#             if _field_exists(dt, alt):
#                 date_field = alt
#                 break

#     salesman_users = _parse_json_list(salesmen)
#     terr_list = _parse_json_list(territories)

#     v_where = [f"v.docstatus <> 2", f"v.{date_field} BETWEEN %s AND %s"]
#     v_params = [start, end]

#     if salesman_users and len(salesman_users) > 0:
#         if salesman_field == "owner":
#             v_where.append("v.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
#         else:
#             v_where.append(f"v.{salesman_field} IN ({', '.join(['%s']*len(salesman_users))})")
#         v_params.extend(salesman_users)

#     v_join_cust = ""
#     if terr_list and len(terr_list) > 0 and _field_exists(dt, "customer"):
#         v_join_cust = "LEFT JOIN `tabCustomer` vc ON vc.name = v.customer"
#         v_where.append("vc.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
#         v_params.extend(terr_list)

#     visits_sql = f"""
#         SELECT COUNT(*) AS cnt
#         FROM `tab{dt}` v
#         {v_join_cust}
#         WHERE {" AND ".join(v_where)}
#     """
#     visits_count = frappe.db.sql(visits_sql, v_params, as_dict=True)[0]["cnt"] or 0

#     o_where = ["so.docstatus = 1", "so.transaction_date BETWEEN %s AND %s"]
#     o_params = [start, end]

#     if salesman_users and len(salesman_users) > 0:
#         o_where.append("so.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
#         o_params.extend(salesman_users)

#     o_join_cust = ""
#     if terr_list and len(terr_list) > 0:
#         o_join_cust = "LEFT JOIN `tabCustomer` oc ON oc.name = so.customer"
#         o_where.append("oc.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
#         o_params.extend(terr_list)

#     orders_sql = f"""
#         SELECT
#             COUNT(*) AS orders_count,
#             COALESCE(SUM(so.base_grand_total), 0) AS orders_amount
#         FROM `tabSales Order` so
#         {o_join_cust}
#         WHERE {" AND ".join(o_where)}
#     """
#     orders_row = frappe.db.sql(orders_sql, o_params, as_dict=True)[0]
#     return {
#         "from_date": str(start),
#         "to_date": str(end),
#         "visits_count": cint(orders_row and visits_count or 0),
#         "orders_count": cint(orders_row["orders_count"] or 0),
#         "orders_amount": float(orders_row["orders_amount"] or 0.0),
#     }


@frappe.whitelist()
def supervisor_today_visits_orders(doctype_name=None,
                                   salesman_field="salesman",
                                   date_field="visit_date",
                                   filter="Today", from_date=None, to_date=None,
                                   salesmen=None, territories=None):
    """
    KPI block: counts for Visits and Orders in selected period (default Today).
    - doctype_name: visit/plan doctype; auto-resolves if omitted.
    - salesman_field/date_field: field names on that doctype (auto-fallbacks are tried).
    - salesmen: JSON list of user emails -> matched to {salesman_field} on visit log & owner on Sales Order by default.
      If not provided, will use all salesmen under the supervisor's territory.
    - territories: JSON list of Territory names -> joins Customer.territory for both visits (if field exists) and orders.
    Returns: { visits_count, orders_count, orders_amount, from_date, to_date }
    """
    _require_supervisor()

    # Get date range
    start, end = _date_range_from_filter(filter, from_date, to_date)
    dt = _resolve_visit_plan_doctype(doctype_name)

    # Find appropriate field names
    if not _field_exists(dt, salesman_field):
        for alt in ("salesman_user", "assigned_to", "sales_person", "salesperson", "owner"):
            if _field_exists(dt, alt):
                salesman_field = alt
                break
    if not _field_exists(dt, date_field):
        for alt in ("planned_date", "schedule_date", "posting_date", "creation"):
            if _field_exists(dt, alt):
                date_field = alt
                break

    # Parse input parameters
    salesman_users = _parse_json_list(salesmen)
    terr_list = _parse_json_list(territories)
    
    # If no salesmen provided, get all salesmen under supervisor
    if not salesman_users:
        supervisor_salesmen = _salesmen_under_perm()
        if supervisor_salesmen:
            salesman_users = [user.user for user in supervisor_salesmen]
    
    # Build visit query
    v_where = [f"v.docstatus <> 2", f"v.{date_field} BETWEEN %s AND %s"]
    v_params = [start, end]

    if salesman_users and len(salesman_users) > 0:
        if salesman_field == "owner":
            v_where.append("v.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        else:
            v_where.append(f"v.{salesman_field} IN ({', '.join(['%s']*len(salesman_users))})")
        v_params.extend(salesman_users)

    v_join_cust = ""
    if terr_list and len(territory_list) > 0 and _field_exists(dt, "customer"):
        v_join_cust = "LEFT JOIN `tabCustomer` vc ON vc.name = v.customer"
        v_where.append("vc.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        v_params.extend(terr_list)

    visits_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM `tab{dt}` v
        {v_join_cust}
        WHERE {" AND ".join(v_where)}
    """
    visits_count = frappe.db.sql(visits_sql, v_params, as_dict=True)[0]["cnt"] or 0

    # Build sales order query
    o_where = ["so.docstatus = 1", "so.transaction_date BETWEEN %s AND %s"]
    o_params = [start, end]

    if salesman_users and len(salesman_users) > 0:
        o_where.append("so.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        o_params.extend(salesman_users)

    o_join_cust = ""
    if terr_list and len(terr_list) > 0:
        o_join_cust = "LEFT JOIN `tabCustomer` oc ON oc.name = so.customer"
        o_where.append("oc.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        o_params.extend(terr_list)

    orders_sql = f"""
        SELECT
            COUNT(*) AS orders_count,
            COALESCE(SUM(so.base_grand_total), 0) AS orders_amount
        FROM `tabSales Order` so
        {o_join_cust}
        WHERE {" AND ".join(o_where)}
    """
    orders_row = frappe.db.sql(orders_sql, o_params, as_dict=True)[0]
    
    return {
        "from_date": str(start),
        "to_date": str(end),
        "visits_count": cint(visits_count or 0),
        "orders_count": cint(orders_row["orders_count"] or 0),
        "orders_amount": float(orders_row["orders_amount"] or 0.0),
    }


# @frappe.whitelist()
# def supervisor_kpis(filter="Today", from_date=None, to_date=None,
#                     salesmen=None, territories=None,
#                     doctype_name=None, salesman_field="salesman", date_field="visit_date"):
#     """
#     One call that returns all three blocks (Total Sales, Collections, Visits/Orders).
#     """
#     _require_supervisor()
#     totals = supervisor_total_sales(filter, from_date, to_date, salesmen, territories)
#     colls = supervisor_collections(filter, from_date, to_date, salesmen, territories)
#     v_o = supervisor_today_visits_orders(
#         doctype_name=doctype_name,
#         salesman_field=salesman_field,
#         date_field=date_field,
#         filter=filter, from_date=from_date, to_date=to_date,
#         salesmen=salesmen, territories=territories
#     )
#     return {
#         "range": {"from_date": totals["from_date"], "to_date": totals["to_date"]},
#         "total_sales": totals["net_sales"],
#         "collections": colls["collections"],
#         "visits_count": v_o["visits_count"],
#         "orders_count": v_o["orders_count"],
#         "orders_amount": v_o["orders_amount"]
#     }
@frappe.whitelist()
def supervisor_kpis(filter="Today", from_date=None, to_date=None,
                    salesmen=None, territories=None,
                    doctype_name=None, salesman_field="salesman", date_field="visit_date"):
    """
    One call that returns all three blocks (Total Sales, Collections, Visits/Orders).
    """
    _require_supervisor()
    
    # Get active salesmen count
    active_salesmen = _salesmen_user_list()
    active_salesmen_count = len(active_salesmen)
    
    # Get today's specific metrics
    todays_visits_orders = supervisor_today_visits_orders(
        doctype_name=doctype_name,
        salesman_field=salesman_field,
        date_field=date_field,
        filter="Today", from_date=None, to_date=None,
        salesmen=salesmen, territories=territories
    )
    
    totals = supervisor_total_sales(filter, from_date, to_date, salesmen, territories)
    colls = supervisor_collections(filter, from_date, to_date, salesmen, territories)
    v_o = supervisor_today_visits_orders(
        doctype_name=doctype_name,
        salesman_field=salesman_field,
        date_field=date_field,
        filter=filter, from_date=from_date, to_date=to_date,
        salesmen=salesmen, territories=territories
    )
    return {
        "range": {"from_date": totals["from_date"], "to_date": totals["to_date"]},
        "total_sales": totals["net_sales"],
        "collections": colls["collections"],
        "visits_count": v_o["visits_count"],
        "orders_count": v_o["orders_count"],
        "orders_amount": v_o["orders_amount"],
        "active_salesmen": active_salesmen_count,
        "todays_visits": todays_visits_orders["visits_count"],
        "todays_orders": todays_visits_orders["orders_count"]
    }

@frappe.whitelist()
def supervisor_get_territories():
    """
    Get territories assigned to the current supervisor with detailed information.
    Returns territory hierarchy and metadata.
    """
    _require_supervisor()
    
    # Get supervisor's permitted territories
    supervisor_territories = []
    try:
        from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
        supervisor_territories = get_permitted_documents("Territory")
    except Exception as e:
        frappe.log_error(f"Error getting supervisor territories: {str(e)}")
        return {"territories": [], "error": "Could not fetch territory permissions"}
    
    if not supervisor_territories:
        return {
            "territories": [],
            "message": "No territories assigned to this supervisor",
            "supervisor": frappe.session.user
        }
    
    # Get detailed territory information
    territories = frappe.db.sql("""
        SELECT 
            t.name,
            t.territory_name,
            t.parent_territory,
            t.is_group,
            t.territory_manager,
            t.lft,
            t.rgt,
            
            /* Count of child territories */
            (SELECT COUNT(*) FROM `tabTerritory` ct 
             WHERE ct.parent_territory = t.name) AS child_count,
            
            /* Count of customers in this territory */
            (SELECT COUNT(*) FROM `tabCustomer` c 
             WHERE c.territory = t.name AND c.disabled = 0) AS customer_count,
             
            /* Count of salesmen assigned to this territory */
            (SELECT COUNT(DISTINCT up.user) FROM `tabUser Permission` up
             JOIN `tabUser` u ON u.name = up.user
             WHERE up.allow = 'Territory' 
             AND up.for_value = t.name 
             AND u.enabled = 1
             AND EXISTS (
                 SELECT 1 FROM `tabHas Role` hr 
                 WHERE hr.parent = u.name AND hr.role = 'Salesman'
             )) AS salesman_count
             
        FROM `tabTerritory` t
        WHERE t.name IN ({placeholders})
        ORDER BY t.lft
    """.format(placeholders=', '.join(['%s'] * len(supervisor_territories))), 
    supervisor_territories, as_dict=True)
    
    # Get territory hierarchy (parent-child relationships)
    territory_tree = {}
    for territory in territories:
        territory_tree[territory.name] = {
            **territory,
            "children": []
        }
    
    # Build hierarchy
    root_territories = []
    for territory in territories:
        if territory.parent_territory and territory.parent_territory in territory_tree:
            territory_tree[territory.parent_territory]["children"].append(territory_tree[territory.name])
        else:
            root_territories.append(territory_tree[territory.name])
    
    return {
        "territories": territories,
        "territory_tree": root_territories,
        "total_territories": len(territories),
        "supervisor": frappe.session.user,
        "summary": {
            "total_customers": sum(t.get("customer_count", 0) for t in territories),
            "total_salesmen": sum(t.get("salesman_count", 0) for t in territories),
            "group_territories": len([t for t in territories if t.get("is_group")]),
            "leaf_territories": len([t for t in territories if not t.get("is_group")])
        }
    }
    
@frappe.whitelist()
def get_salesman_territories(salesman_user=None):
    """
    Get territories assigned to a salesman via POS Profile with detailed information.
    If no salesman_user provided, returns territories for current user.
    """
    target_user = salesman_user or frappe.session.user
    current_user = frappe.session.user
    user_roles = set(frappe.get_roles(current_user))
    
    # Permission checks
    if target_user != current_user and not (user_roles & {"Sales Supervisor", "System Manager"}):
        frappe.throw(_("You don't have permission to view territories for other users"))
    
    # Get salesman's territories from POS Profile
    salesman_territories = []
    try:
        salesman_territories = frappe.db.get_all(
            "POS Profile User",
            filters={"user": target_user},
            fields=["parent"],
            ignore_permissions=True
        )
        # Get territory from parent POS Profile
        if salesman_territories:
            profile_names = [p.parent for p in salesman_territories]
            territories_data = frappe.db.get_all(
                "POS Profile",
                filters={"name": ["in", profile_names], "disabled": 0},
                fields=["territory"],
                ignore_permissions=True
            )
            salesman_territories = [t.territory for t in territories_data if t.territory]
        else:
            salesman_territories = []
    except Exception as e:
        frappe.log_error(f"Error getting salesman territories: {str(e)}")
        return {"territories": [], "error": "Could not fetch territory assignments from POS Profile"}
    
    if not salesman_territories:
        return {
            "territories": [],
            "message": "No territories assigned to this salesman via POS Profile",
            "salesman": target_user
        }
    
    # Check supervisor permission for salesman territories (if supervisor role)
    if target_user != current_user and "Sales Supervisor" in user_roles:
        supervisor_territories = []
        try:
            from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
            supervisor_territories = get_permitted_documents("Territory")
        except Exception:
            pass
        
        # Check if there's overlap between supervisor and salesman territories
        if supervisor_territories and not (set(supervisor_territories) & set(salesman_territories)):
            frappe.throw(_("You don't have permission to view territories for this salesman"))
    
    # Get detailed territory information
    territories = frappe.db.sql("""
        SELECT 
            t.name,
            t.territory_name,
            t.parent_territory,
            t.is_group,
            t.territory_manager,
            t.lft,
            t.rgt,
            
            /* Count of customers in this territory */
            (SELECT COUNT(*) FROM `tabCustomer` c 
             WHERE c.territory = t.name AND c.disabled = 0) AS customer_count,
             
            /* Count of active sales orders in this territory (last 30 days) */
            (SELECT COUNT(*) FROM `tabSales Order` so
             JOIN `tabCustomer` c ON c.name = so.customer
             WHERE c.territory = t.name 
             AND so.docstatus = 1
             AND so.transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) AS recent_orders,
             
            /* Total sales in this territory (last 30 days) */
            (SELECT COALESCE(SUM(si.grand_total), 0) FROM `tabSales Invoice` si
             JOIN `tabCustomer` c ON c.name = si.customer
             WHERE c.territory = t.name 
             AND si.docstatus = 1
             AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) AS recent_sales,
             
            /* Count of visits in this territory (last 30 days) */
            (SELECT COUNT(*) FROM `tabSales Visit Log` svl
             JOIN `tabCustomer` c ON c.name = svl.customer
             WHERE c.territory = t.name 
             AND svl.visit_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) AS recent_visits
             
        FROM `tabTerritory` t
        WHERE t.name IN ({placeholders})
        ORDER BY t.lft
    """.format(placeholders=', '.join(['%s'] * len(salesman_territories))), 
    salesman_territories, as_dict=True)
    
    # Get salesman details
    salesman_info = frappe.db.get_value(
        "User", 
        target_user, 
        ["name", "first_name", "last_name", "email", "mobile_no"],
        as_dict=True
    ) or {}
    
    return {
        "territories": territories,
        "total_territories": len(territories),
        "salesman": {
            "user": target_user,
            "full_name": f"{salesman_info.get('first_name', '')} {salesman_info.get('last_name', '')}".strip(),
            "email": salesman_info.get('email'),
            "mobile_no": salesman_info.get('mobile_no')
        },
        "summary": {
            "total_customers": sum(t.get("customer_count", 0) for t in territories),
            "recent_orders": sum(t.get("recent_orders", 0) for t in territories),
            "recent_sales": sum(t.get("recent_sales", 0) for t in territories),
            "recent_visits": sum(t.get("recent_visits", 0) for t in territories),
            "group_territories": len([t for t in territories if t.get("is_group")]),
            "leaf_territories": len([t for t in territories if not t.get("is_group")])
        }
    }

@frappe.whitelist()
def get_pos_profiles(include_disabled=0):
    """
    Get list of POS Profiles with their user assignments and details.
    """
    # Check permissions
    if not frappe.has_permission("POS Profile", "read"):
        frappe.throw(_("You don't have permission to view POS Profiles"))
    
    # Build filters
    filters = {}
    if not int(include_disabled):
        filters["disabled"] = 0
    
    # Get POS Profiles
    pos_profiles = frappe.db.sql("""
        SELECT 
            pp.name,
            pp.company,
            pp.warehouse,
            pp.disabled,
            pp.customer,
            pp.selling_price_list,
            pp.currency,
            pp.creation,
            pp.modified,
            pp.owner,
            
            /* Count of assigned users */
            (SELECT COUNT(*) FROM `tabPOS Profile User` ppu 
             WHERE ppu.parent = pp.name) AS user_count
             
        FROM `tabPOS Profile` pp
        WHERE pp.disabled = %s OR %s = 1
        ORDER BY pp.creation DESC
    """, (0 if not int(include_disabled) else 1, int(include_disabled)), as_dict=True)
    
    # Get user assignments for each profile
    for profile in pos_profiles:
        users = frappe.db.get_all(
            "POS Profile User",
            filters={"parent": profile.name},
            fields=["user"],
            order_by="idx"
        )
        
        # Get user details
        user_details = []
        for user_row in users:
            user_info = frappe.db.get_value(
                "User",
                user_row.user,
                ["name", "first_name", "last_name", "email", "enabled"],
                as_dict=True
            )
            if user_info:
                user_details.append({
                    "user": user_info.name,
                    "full_name": f"{user_info.first_name or ''} {user_info.last_name or ''}".strip(),
                    "email": user_info.email,
                    "enabled": user_info.enabled
                })
        
        profile["users"] = user_details
    
    return {
        "pos_profiles": pos_profiles,
        "total_count": len(pos_profiles),
        "active_count": len([p for p in pos_profiles if not p.disabled]),
        "disabled_count": len([p for p in pos_profiles if p.disabled])
    }

    {{ ... }}
@frappe.whitelist()
def supervisor_salesman_wise_total_sales(filter="Today", from_date=None, to_date=None,
                                        salesmen=None, territories=None):
    """
    Sum of Sales Invoice in company currency (base), net of returns, grouped by salesman.
    Returns a list of salesmen with their individual sales totals.
    """
    _require_supervisor()

    start, end = _date_range_from_filter(filter, from_date, to_date)
    salesman_users = _parse_json_list(salesmen)
    terr_list = _parse_json_list(territories)

    where = ["si.docstatus = 1", "si.posting_date BETWEEN %s AND %s"]
    params = [start, end]
    
    if salesman_users and len(salesman_users) > 0:
        where.append("si.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        params.extend(salesman_users)

    if terr_list and len(terr_list) > 0:
        where.append("c.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        params.extend(terr_list)

    sql = f"""
        SELECT
            si.owner as salesman,
            COALESCE(SUM(CASE WHEN si.is_return = 1
                               THEN -si.base_grand_total
                               ELSE  si.base_grand_total END), 0) AS total_sales
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCustomer` c ON c.name = si.customer
        WHERE {" AND ".join(where)}
        GROUP BY si.owner
        ORDER BY total_sales DESC
    """
    results = frappe.db.sql(sql, params, as_dict=True)
    return results

@frappe.whitelist()
def supervisor_salesman_wise_collections(filter="Today", from_date=None, to_date=None,
                                        salesmen=None, territories=None):
    """
    Sum of collections (Payment Entry) in company currency, grouped by salesman.
    Returns a list of salesmen with their individual collection totals.
    """
    _require_supervisor()

    start, end = _date_range_from_filter(filter, from_date, to_date)
    salesman_users = _parse_json_list(salesmen)
    terr_list = _parse_json_list(territories)

    where = ["pe.docstatus = 1", "pe.payment_type = 'Receive'", "pe.posting_date BETWEEN %s AND %s"]
    params = [start, end]

    if salesman_users and len(salesman_users) > 0:
        where.append("pe.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        params.extend(salesman_users)

    join_customer = ""
    if terr_list and len(terr_list) > 0:
        join_customer = "LEFT JOIN `tabCustomer` c ON c.name = pe.party AND pe.party_type = 'Customer'"
        where.append("c.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        params.extend(terr_list)

    sql = f"""
        SELECT 
            pe.owner as salesman,
            COALESCE(SUM(pe.base_received_amount), 0) AS collections
        FROM `tabPayment Entry` pe
        {join_customer}
        WHERE {" AND ".join(where)}
        GROUP BY pe.owner
        ORDER BY collections DESC
    """
    results = frappe.db.sql(sql, params, as_dict=True)
    return results

@frappe.whitelist()
def supervisor_salesman_wise_visits_orders(doctype_name=None,
                                          salesman_field="salesman",
                                          date_field="visit_date",
                                          filter="Today", from_date=None, to_date=None,
                                          salesmen=None, territories=None):
    """
    KPI block: counts for Visits and Orders in selected period, grouped by salesman.
    Returns a list of salesmen with their individual visit and order counts.
    """
    _require_supervisor()

    start, end = _date_range_from_filter(filter, from_date, to_date)
    dt = _resolve_visit_plan_doctype(doctype_name)

    if not _field_exists(dt, salesman_field):
        for alt in ("salesman_user", "assigned_to", "sales_person", "salesperson", "owner"):
            if _field_exists(dt, alt):
                salesman_field = alt
                break
    if not _field_exists(dt, date_field):
        for alt in ("planned_date", "schedule_date", "posting_date", "creation"):
            if _field_exists(dt, alt):
                date_field = alt
                break

    salesman_users = _parse_json_list(salesmen)
    terr_list = _parse_json_list(territories)

    # Get visits by salesman
    v_where = [f"v.docstatus <> 2", f"v.{date_field} BETWEEN %s AND %s"]
    v_params = [start, end]

    if salesman_users and len(salesman_users) > 0:
        if salesman_field == "owner":
            v_where.append("v.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        else:
            v_where.append(f"v.{salesman_field} IN ({', '.join(['%s']*len(salesman_users))})")
        v_params.extend(salesman_users)

    v_join_cust = ""
    if terr_list and len(terr_list) > 0 and _field_exists(dt, "customer"):
        v_join_cust = "LEFT JOIN `tabCustomer` vc ON vc.name = v.customer"
        v_where.append("vc.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        v_params.extend(terr_list)

    visits_sql = f"""
        SELECT 
            v.{salesman_field} as salesman,
            COUNT(*) AS visits_count
        FROM `tab{dt}` v
        {v_join_cust}
        WHERE {" AND ".join(v_where)}
        GROUP BY v.{salesman_field}
    """
    visits_results = frappe.db.sql(visits_sql, v_params, as_dict=True)

    # Get orders by salesman
    o_where = ["so.docstatus = 1", "so.transaction_date BETWEEN %s AND %s"]
    o_params = [start, end]

    if salesman_users and len(salesman_users) > 0:
        o_where.append("so.owner IN ({})".format(", ".join(["%s"] * len(salesman_users))))
        o_params.extend(salesman_users)

    o_join_cust = ""
    if terr_list and len(terr_list) > 0:
        o_join_cust = "LEFT JOIN `tabCustomer` oc ON oc.name = so.customer"
        o_where.append("oc.territory IN ({})".format(", ".join(["%s"] * len(terr_list))))
        o_params.extend(terr_list)

    orders_sql = f"""
        SELECT
            so.owner as salesman,
            COUNT(*) AS orders_count,
            COALESCE(SUM(so.base_grand_total), 0) AS orders_amount
        FROM `tabSales Order` so
        {o_join_cust}
        WHERE {" AND ".join(o_where)}
        GROUP BY so.owner
    """
    orders_results = frappe.db.sql(orders_sql, o_params, as_dict=True)

    # Combine visits and orders data
    salesman_data = {}
    
    # Add visits data
    for visit in visits_results:
        salesman = visit['salesman']
        if salesman:
            salesman_data[salesman] = {
                'salesman': salesman,
                'visits_count': visit['visits_count'],
                'orders_count': 0,
                'orders_amount': 0.0
            }
    
    # Add orders data
    for order in orders_results:
        salesman = order['salesman']
        if salesman:
            if salesman not in salesman_data:
                salesman_data[salesman] = {
                    'salesman': salesman,
                    'visits_count': 0,
                    'orders_count': 0,
                    'orders_amount': 0.0
                }
            salesman_data[salesman]['orders_count'] = order['orders_count']
            salesman_data[salesman]['orders_amount'] = float(order['orders_amount'])

    return list(salesman_data.values())

@frappe.whitelist()
def supervisor_salesman_wise_kpis(filter="Today", from_date=None, to_date=None,
                                 salesmen=None, territories=None,
                                 doctype_name=None, salesman_field="salesman", date_field="visit_date"):
    """
    Returns KPIs for each salesman under the supervisor.
    Returns a list of salesmen with their individual KPIs: total_sales, collections, visits_count, orders_count, orders_amount.
    
    Parameters:
    - filter: Date filter ("Today", "Week", "Month", "Year", "Range")
    - from_date, to_date: Custom date range (required if filter="Range")
    - salesmen: JSON list of salesman user emails to filter by (e.g., '["user1@example.com", "user2@example.com"]')
    - territories: JSON list of territory names to filter by
    - doctype_name: Visit/plan doctype name (auto-resolves if omitted)
    - salesman_field: Field name for salesman on visit doctype
    - date_field: Date field name on visit doctype
    
    Usage Examples:
    1. All salesmen today: supervisor_salesman_wise_kpis()
    2. Specific salesmen: supervisor_salesman_wise_kpis(salesmen='["john@company.com", "jane@company.com"]')
    3. Date range: supervisor_salesman_wise_kpis(filter="Range", from_date="2024-01-01", to_date="2024-01-31")
    4. Territory filter: supervisor_salesman_wise_kpis(territories='["North", "South"]')
    """
    _require_supervisor()
    
    start, end = _date_range_from_filter(filter, from_date, to_date)
    
    # Parse salesmen filter - if provided, only return data for these salesmen
    salesman_users = _parse_json_list(salesmen)
    
    # Get all KPI data (already filtered by salesmen parameter in underlying functions)
    sales_data = supervisor_salesman_wise_total_sales(filter, from_date, to_date, salesmen, territories)
    collections_data = supervisor_salesman_wise_collections(filter, from_date, to_date, salesmen, territories)
    visits_orders_data = supervisor_salesman_wise_visits_orders(
        doctype_name=doctype_name,
        salesman_field=salesman_field,
        date_field=date_field,
        filter=filter, from_date=from_date, to_date=to_date,
        salesmen=salesmen, territories=territories
    )
    
    # Combine all data by salesman
    salesman_kpis = {}
    
    # Add sales data
    for item in sales_data:
        salesman = item['salesman']
        if salesman:
            salesman_kpis[salesman] = {
                'salesman': salesman,
                'total_sales': float(item['total_sales']),
                'collections': 0.0,
                'visits_count': 0,
                'orders_count': 0,
                'orders_amount': 0.0
            }
    
    # Add collections data
    for item in collections_data:
        salesman = item['salesman']
        if salesman:
            if salesman not in salesman_kpis:
                salesman_kpis[salesman] = {
                    'salesman': salesman,
                    'total_sales': 0.0,
                    'collections': 0.0,
                    'visits_count': 0,
                    'orders_count': 0,
                    'orders_amount': 0.0
                }
            salesman_kpis[salesman]['collections'] = float(item['collections'])
    
    # Add visits and orders data
    for item in visits_orders_data:
        salesman = item['salesman']
        if salesman:
            if salesman not in salesman_kpis:
                salesman_kpis[salesman] = {
                    'salesman': salesman,
                    'total_sales': 0.0,
                    'collections': 0.0,
                    'visits_count': 0,
                    'orders_count': 0,
                    'orders_amount': 0.0
                }
            salesman_kpis[salesman]['visits_count'] = item['visits_count']
            salesman_kpis[salesman]['orders_count'] = item['orders_count']
            salesman_kpis[salesman]['orders_amount'] = float(item['orders_amount'])
    
    # Convert to list and sort by total_sales descending
    result = list(salesman_kpis.values())
    result.sort(key=lambda x: x['total_sales'], reverse=True)
    
    return {
        "range": {"from_date": str(start), "to_date": str(end)},
        "salesmen_kpis": result,
        "filtered_by_salesmen": salesman_users if salesman_users else None,
        "total_salesmen": len(result)
    }
@frappe.whitelist()
def item_stock_balance_by_salesman(salesman=None):
    """
    Get item stock balance filtered by salesman permissions.
    If salesman is provided, filter by their warehouse permissions.
    If no salesman provided, use current user's permissions.
    """
    from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
    from frappe.utils import flt

    user = frappe.session.user
    target_user = salesman or user
    
    # Get permitted items for the target user
    permitted_items = get_permitted_documents("Item", user=target_user)
    
    # Get permitted warehouses for the target user
    permitted_warehouses = get_permitted_documents("Warehouse", user=target_user)

    # Build item condition
    item_condition = ""
    if permitted_items:
        formatted_items = "', '".join(permitted_items)
        item_condition = f"AND item.name IN ('{formatted_items}')"

    # Build warehouse condition
    warehouse_condition = ""
    if permitted_warehouses:
        formatted_warehouses = "', '".join(permitted_warehouses)
        warehouse_condition = f"AND bin.warehouse IN ('{formatted_warehouses}')"

    data = frappe.db.sql(f"""
        SELECT 
            item.name as item_code,
            item.item_name,
            item.image,
            bin.warehouse,
            wh.warehouse_name,
            SUM(bin.actual_qty) AS stock_qty
        FROM `tabBin` bin
        JOIN `tabItem` item ON bin.item_code = item.name
        LEFT JOIN `tabWarehouse` wh ON bin.warehouse = wh.name
        WHERE bin.actual_qty > 0 
        {item_condition}
        {warehouse_condition}
        GROUP BY item.name, bin.warehouse
        ORDER BY stock_qty DESC
        LIMIT 100
    """, as_dict=True)

    # Group by item and sum quantities across warehouses
    stock_map = {}
    for row in data:
        code = row.get("item_code")
        name = (row.get("item_name") or "").strip()
        qty = flt(row.get("stock_qty") or 0)
        image = row.get("image") or ""
        warehouse = row.get("warehouse") or ""
        warehouse_name = row.get("warehouse_name") or ""

        if code:
            if code not in stock_map:
                stock_map[code] = {
                    "item_code": code,
                    "item_name": name,
                    "stock_qty": 0,
                    "image": image,
                    "warehouses": []
                }
            
            stock_map[code]["stock_qty"] += qty
            stock_map[code]["warehouses"].append({
                "warehouse": warehouse,
                "warehouse_name": warehouse_name,
                "qty": qty
            })

    # Convert to list and sort by total stock quantity
    result = list(stock_map.values())
    result.sort(key=lambda x: x['stock_qty'], reverse=True)
    
    # Limit to top 50 items
    result = result[:50]

    return {
        "salesman": target_user,
        "total_items": len(result),
        "items": result
    }

    {{ ... }}
@frappe.whitelist()
def supervisor_salesman_wise_sales_orders(filter="Today", from_date=None, to_date=None, 
                                        salesmen=None, territories=None, status=None):
    """
    Get salesman wise sales orders for supervisor with proper territory and permission filtering.
    
    Args:
        filter: "Today", "Week", "Month", or "Custom"
        from_date: Start date for custom filter
        to_date: End date for custom filter
        salesmen: JSON list of salesman user emails (optional)
        territories: JSON list of Territory names (optional)
        status: Filter by sales order status (optional)
    
    Returns:
        List of sales orders grouped by salesman with totals
    """
    _require_supervisor()
    
    start, end = _date_range_from_filter(filter, from_date, to_date)
    salesman_users = _parse_json_list(salesmen)
    territory_list = _parse_json_list(territories)
    
    # Build conditions
    conditions = ["so.docstatus = 1"]
    params = []
    
    # Date filter
    conditions.append("so.transaction_date BETWEEN %s AND %s")
    params.extend([start, end])
    
    # Status filter
    if status:
        conditions.append("so.status = %s")
        params.append(status)
    
    # Salesman filter (based on owner or custom salesman field)
    if salesman_users:
        placeholders = ', '.join(['%s'] * len(salesman_users))
        conditions.append(f"so.owner IN ({placeholders})")
        params.extend(salesman_users)
    else:
        # Get all salesmen under supervisor's territory permissions
        permitted_salesmen = _salesmen_user_list()
        if permitted_salesmen:
            placeholders = ', '.join(['%s'] * len(permitted_salesmen))
            conditions.append(f"so.owner IN ({placeholders})")
            params.extend(permitted_salesmen)
    
    # Territory filter
    if territory_list:
        placeholders = ', '.join(['%s'] * len(territory_list))
        conditions.append(f"c.territory IN ({placeholders})")
        params.extend(territory_list)
    
    where_clause = " AND ".join(conditions)
    
    # Main query to get salesman wise sales orders
    query = f"""
        SELECT 
            so.owner as salesman,
            u.full_name as salesman_name,
            COUNT(so.name) as total_orders,
            SUM(so.grand_total) as total_amount,
            SUM(CASE WHEN so.status = 'Draft' THEN 1 ELSE 0 END) as draft_orders,
            SUM(CASE WHEN so.status = 'On Hold' THEN 1 ELSE 0 END) as on_hold_orders,
            SUM(CASE WHEN so.status = 'To Deliver and Bill' THEN 1 ELSE 0 END) as to_deliver_and_bill_orders,
            SUM(CASE WHEN so.status = 'To Bill' THEN 1 ELSE 0 END) as to_bill_orders,
            SUM(CASE WHEN so.status = 'To Deliver' THEN 1 ELSE 0 END) as to_deliver_orders,
            SUM(CASE WHEN so.status = 'Completed' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN so.status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
            SUM(CASE WHEN so.status = 'Closed' THEN 1 ELSE 0 END) as closed_orders,
            AVG(so.grand_total) as avg_order_value
        FROM `tabSales Order` so
        LEFT JOIN `tabCustomer` c ON so.customer = c.name
        LEFT JOIN `tabUser` u ON so.owner = u.name
        WHERE {where_clause}
        GROUP BY so.owner, u.full_name
        ORDER BY total_amount DESC
    """
    
    salesman_summary = frappe.db.sql(query, params, as_dict=True)
    
    # Get detailed orders for each salesman
    detailed_query = f"""
        SELECT 
            so.name,
            so.customer,
            so.customer_name,
            so.transaction_date,
            so.delivery_date,
            so.status,
            so.grand_total,
            so.owner as salesman,
            u.full_name as salesman_name,
            c.territory
        FROM `tabSales Order` so
        LEFT JOIN `tabCustomer` c ON so.customer = c.name
        LEFT JOIN `tabUser` u ON so.owner = u.name
        WHERE {where_clause}
        ORDER BY so.owner, so.transaction_date DESC
    """
    
    detailed_orders = frappe.db.sql(detailed_query, params, as_dict=True)
    
    # Group detailed orders by salesman
    orders_by_salesman = {}
    for order in detailed_orders:
        salesman = order['salesman']
        if salesman not in orders_by_salesman:
            orders_by_salesman[salesman] = []
        orders_by_salesman[salesman].append(order)
    
    # Combine summary with detailed orders
    result = []
    for summary in salesman_summary:
        salesman = summary['salesman']
        summary['orders'] = orders_by_salesman.get(salesman, [])
        result.append(summary)
    
    # Calculate overall totals
    overall_totals = {
        'total_salesmen': len(result),
        'total_orders': sum(s['total_orders'] for s in result),
        'total_amount': sum(s['total_amount'] for s in result),
        'avg_orders_per_salesman': sum(s['total_orders'] for s in result) / len(result) if result else 0,
        'from_date': str(start),
        'to_date': str(end)
    }
    
    return {
        'salesman_data': result,
        'totals': overall_totals
    }

@frappe.whitelist()
def get_salesman_visit_logs(date=None, salesman=None, fields=None):
    """
    Get visit logs for a specific salesman
    
    Args:
        date (str): Date in YYYY-MM-DD format (default: today)
        salesman (str): Email of the salesman (default: current user)
        fields (list): List of fields to fetch (default: ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order"])
        
    Returns:
        list: List of visit logs matching the criteria
    """
    if not date:
        date = today()
    
    if not salesman:
        salesman = frappe.session.user
    
    if not fields:
        fields = ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order"]
    
    # Validate fields to prevent SQL injection
    valid_fields = ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order", 
                   "customer_name", "status", "company", "territory", "contact_person", "contact_mobile", "remarks"]
    fields = [f for f in fields if f in valid_fields]
    
    if not fields:
        frappe.throw("No valid fields specified")
    
    visit_doctype = _resolve_visit_plan_doctype()
    
    # Build filters
    filters = [
        ["visit_date", "=", date],
        ["salesman", "=", salesman],
        ["docstatus", "!=", 2]  # Exclude cancelled
    ]
    
    # Get visit logs
    visit_logs = frappe.get_all(
        visit_doctype,
        fields=fields,
        filters=filters,
        order_by="visit_date asc"
    )
    
    return visit_logs

# @frappe.whitelist()
# def get_supervisor_visit_logs(date=None, salesmen=None, fields=None):
#     """
#     Get visit logs for all salesmen under a supervisor
    
#     Args:
#         date (str): Date in YYYY-MM-DD format (default: today)
#         salesmen (list): List of salesman emails to filter by (default: all salesmen under supervisor)
#         fields (list): List of fields to fetch (default: ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order"])
        
#     Returns:
#         list: List of visit logs matching the criteria
#     """
#     # Ensure user has supervisor permissions
#     _require_supervisor()
    
#     if not date:
#         date = today()
    
#     if not fields:
#         fields = ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order", 
#                  "customer_name", "status", "company", "territory"]
    
#     # Validate fields to prevent SQL injection
#     valid_fields = ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order",
#                    "customer_name", "status", "company", "territory", "contact_person", "contact_mobile", "remarks"]
#     fields = [f for f in fields if f in valid_fields]
    
#     if not fields:
#         frappe.throw("No valid fields specified")
    
#     # Get list of salesmen if not provided
#     if not salesmen:
#         salesmen = [user[0] for user in _salesmen_under_perm()]
    
#     if not salesmen:
#         return []
    
#     visit_doctype = _resolve_visit_plan_doctype()
    
#     # Build filters
#     filters = [
#         ["visit_date", "=", date],
#         ["salesman", "in", salesmen],
#         ["docstatus", "!=", 2]  # Exclude cancelled
#     ]
    
#     # Get visit logs
#     visit_logs = frappe.get_all(
#         visit_doctype,
#         fields=fields,
#         filters=filters,
#         order_by="salesman, visit_date asc"
#     )
    
#     return visit_logs


@frappe.whitelist()
def get_supervisor_visit_logs(date=None, salesmen=None, fields=None):
    """
    Get visit logs for all salesmen under a supervisor
    
    Args:
        date (str): Date in YYYY-MM-DD format (default: today)
        salesmen (list): List of salesman emails to filter by (default: all salesmen under supervisor)
        fields (list): List of fields to fetch (default: ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order"])
        
    Returns:
        list: List of visit logs matching the criteria
    """
    # Ensure user has supervisor permissions
    _require_supervisor()
    
    if not date:
        date = today()
    
    if not fields:
        fields = ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order"]
    
    # Validate fields to prevent SQL injection
    valid_fields = ["name", "customer", "salesman", "outcome", "visit_date", "next_visit_date", "linked_order",
                    "status", "company", "territory", "contact_person", "contact_mobile", "remarks"]
    fields = [f for f in fields if f in valid_fields]
    
    if not fields:
        frappe.throw("No valid fields specified")
    
    # Get list of salesmen if not provided
    if not salesmen:
        salesmen = [user.user for user in _salesmen_under_perm()]
    
    if not salesmen:
        return []
    
    visit_doctype = _resolve_visit_plan_doctype()
    
    # Build filters
    filters = [
        ["visit_date", "=", date],
        ["salesman", "in", salesmen],
        ["docstatus", "!=", 2]  # Exclude cancelled
    ]
    
    # Get visit logs
    visit_logs = frappe.get_all(
        visit_doctype,
        fields=fields,
        filters=filters,
        order_by="salesman, visit_date asc"
    )
    
    return visit_logs



@frappe.whitelist()
def get_supervisor_collections(filter=None, from_date=None, to_date=None, salesman=None):
    """
    Get collections (invoices) for salesmen under the current supervisor.
    
    Args:
        filter: Date filter ("Today", "This Week", "This Month", "This Year", "Custom")
        from_date: Start date for custom filter (YYYY-MM-DD)
        to_date: End date for custom filter (YYYY-MM-DD)
        salesman: Email of specific salesman to filter by (optional)
        
    Returns:
        List of invoices with details
    """
    _require_supervisor()
    
    # Get date range based on filter
    start_date, end_date = _date_range_from_filter(filter, from_date, to_date)
    
    # Get all salesmen under supervisor
    all_salesmen = _salesmen_under_perm()
    
    if not all_salesmen:
        return []
    
    # If specific salesman is provided, validate they are under supervisor
    if salesman:
        if not any(s['email'] == salesman for s in all_salesmen):
            frappe.throw("You don't have permission to view this salesman's data")
        salesman_emails = [salesman]
    else:
        salesman_emails = [s['email'] for s in all_salesmen]
    
    # Build the query to get invoices
    filters = [
        ["docstatus", "=", 1],
        ["posting_date", "between", [start_date, end_date]],
        ["owner", "in", salesman_emails]
    ]
    
    # Get invoices with required fields
    invoices = frappe.get_all(
        "Sales Invoice",
        fields=[
            "name",
            "customer",
            "posting_date",
            "grand_total",
            "status",
            "is_return",
            "due_date",
            "outstanding_amount",
            "owner as salesman_email"
        ],
        filters=filters,
        order_by="posting_date desc"
    )
    
    # Create a lookup for salesman details
    salesman_lookup = {s['email']: s for s in all_salesmen}
    
    # Format the response
    result = []
    for inv in invoices:
        salesman_info = salesman_lookup.get(inv.salesman_email, {})
        
        result.append({
            'invoice_id': inv.name,
            'customer': inv.customer,
            'date': str(inv.posting_date),
            'amount': inv.grand_total,
            'status': inv.status,
            'is_return': 1 if inv.is_return else 0,
            'due_date': str(inv.due_date) if inv.due_date else None,
            'outstanding_amount': inv.outstanding_amount,
            'salesman_email': inv.salesman_email,
            'salesman_name': salesman_info.get('full_name', inv.salesman_email)
        })
    
    return result

@frappe.whitelist()
def get_supervisor_dashboard(days=30, from_date=None, to_date=None):
    """
    Returns a comprehensive dashboard for supervisors with multiple reports in one view.
    
    Args:
        days (int): Number of days to look back (default: 30)
        from_date (str): Start date (YYYY-MM-DD), overrides days if provided
        to_date (str): End date (YYYY-MM-DD), defaults to today if not provided
    
    Returns:
        dict: {
            "summary": {
                "total_sales": 10000,
                "total_returns": 500,
                "net_sales": 9500,
                "total_orders": 150,
                "unique_customers": 45,
                "avg_order_value": 63.33
            },
            "reports": {
                "sales_by_territory": [...],
                "sales_by_salesperson": [...],
                "top_customers": [...],
                "top_products": [...]
            }
        }
    """
    from frappe.utils import getdate, add_days, today, flt
    
    # Get date range
    if not to_date:
        to_date = today()
    if not from_date:
        from_date = add_days(to_date, -int(days))
    
    # Get supervisor's permitted territories
    try:
        from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
        permitted_territories = get_permitted_documents("Territory")
    except Exception:
        permitted_territories = []
    
    if not permitted_territories:
        return {"summary": {}, "reports": {}}
    
    # Prepare placeholders for SQL queries
    placeholders = ", ".join(["%s"] * len(permitted_territories))
    params = permitted_territories + [from_date, to_date]
    
    # 1. Sales by Territory
    sales_by_territory = frappe.db.sql(f"""
        SELECT 
            si.territory, 
            COUNT(DISTINCT si.name) as order_count,
            ROUND(SUM(si.grand_total), 2) as total_sales,
            ROUND(SUM(si.total_taxes_and_charges), 2) as total_tax,
            ROUND(SUM(si.discount_amount), 2) as total_discount
        FROM `tabSales Invoice` si
        WHERE 
            si.territory IN ({placeholders})
            AND si.docstatus = 1 
            AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.territory
        ORDER BY total_sales DESC
    """, params, as_dict=1)
    
    # 2. Sales by Salesperson
    sales_by_salesperson = frappe.db.sql(f"""
        SELECT 
            si.owner as salesperson,
            COUNT(DISTINCT si.name) as order_count,
            ROUND(SUM(si.grand_total), 2) as total_sales,
            COUNT(DISTINCT si.customer) as customer_count
        FROM `tabSales Invoice` si
        WHERE 
            si.territory IN ({placeholders})
            AND si.docstatus = 1 
            AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.owner
        ORDER BY total_sales DESC
    """, params, as_dict=1)
    
    # 3. Top Customers
    top_customers = frappe.db.sql(f"""
        SELECT 
            si.customer,
            si.customer_name,
            COUNT(DISTINCT si.name) as order_count,
            ROUND(SUM(si.grand_total), 2) as total_spent
        FROM `tabSales Invoice` si
        WHERE 
            si.territory IN ({placeholders})
            AND si.docstatus = 1 
            AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.customer
        ORDER BY total_spent DESC
        LIMIT 10
    """, params, as_dict=1)
    
    # 4. Top Products
    top_products = frappe.db.sql(f"""
        SELECT 
            sii.item_code,
            sii.item_name,
            SUM(sii.qty) as total_quantity,
            ROUND(SUM(sii.amount), 2) as total_amount
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE 
            si.territory IN ({placeholders})
            AND si.docstatus = 1 
            AND si.posting_date BETWEEN %s AND %s
        GROUP BY sii.item_code
        ORDER BY total_amount DESC
        LIMIT 10
    """, params, as_dict=1)
    
    # Calculate summary metrics
    total_sales = sum(flt(r.get('total_sales', 0)) for r in sales_by_territory)
    total_orders = sum(r.get('order_count', 0) for r in sales_by_territory)
    unique_customers = len(set(c['customer'] for c in top_customers))
    
    return {
        "summary": {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "unique_customers": unique_customers,
            "avg_order_value": round(total_sales / total_orders, 2) if total_orders else 0,
            "from_date": from_date,
            "to_date": to_date
        },
        "reports": {
            "sales_by_territory": sales_by_territory,
            "sales_by_salesperson": sales_by_salesperson,
            "top_customers": top_customers,
            "top_products": top_products
        }
    }

@frappe.whitelist()
def approve_or_submit_material_request(docname, action="submit"):
    """
    Approve or submit a material request as supervisor
    
    Args:
        docname (str): Name of the Material Request document
        action (str): Action to perform - 'submit' or 'approve'
        
    Returns:
        dict: Status and message
    """
    # Validate action
    action = action.lower()
    if action not in ["submit", "approve"]:
        frappe.throw(_("Invalid action. Must be either 'submit' or 'approve'."))
    
    # Check if document exists
    if not frappe.db.exists("Material Request", docname):
        frappe.throw(_(f"Material Request {docname} does not exist."))
    
    doc = frappe.get_doc("Material Request", docname)
    
    # Check permissions - ensure user has permission for the warehouse
    user_warehouses = frappe.get_all("User Permission",
        filters={
            "user": frappe.session.user,
            "allow": "Warehouse"
        },
        pluck="for_value"
    )
    
    if not user_warehouses:
        frappe.throw(_("You don't have permission to any warehouse."))
    
    if doc.set_warehouse not in user_warehouses:
        frappe.throw(_(f"You don't have permission for warehouse {doc.set_warehouse}."))
    
    # Perform action based on current status
    if action == "submit":
        if doc.docstatus == 0:  # Draft
            try:
                doc.submit()
                return {
                    "status": "success",
                    "message": _("Material Request {0} has been submitted successfully").format(docname),
                    "docstatus": doc.docstatus
                }
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Material Request Submit Error")
                frappe.throw(_(f"Error submitting Material Request: {str(e)}"))
        else:
            frappe.throw(_("Only draft Material Requests can be submitted."))
    
    elif action == "approve":
        if doc.docstatus == 1:  # Submitted
            try:
                # Check if already approved
                if doc.status == "Stopped" or doc.status == "Cancelled":
                    frappe.throw(_("Cannot approve a stopped or cancelled Material Request."))
                
                if doc.status == "Approved":
                    return {
                        "status": "info",
                        "message": _("Material Request {0} is already approved").format(docname),
                        "docstatus": doc.docstatus
                    }
                
                # Update status to approved
                doc.status = "Approved"
                doc.save(ignore_permissions=True)
                
                # Add a comment for audit trail
                doc.add_comment("Workflow", _("Approved by {0}").format(frappe.session.user))
                
                return {
                    "status": "success",
                    "message": _("Material Request {0} has been approved successfully").format(docname),
                    "docstatus": doc.docstatus
                }
                
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Material Request Approval Error")
                frappe.throw(_(f"Error approving Material Request: {str(e)}"))
        else:
            frappe.throw(_("Only submitted Material Requests can be approved."))
    
    return {
        "status": "error",
        "message": _("No action taken")
    }

@frappe.whitelist()
def get_sales_order_details(sales_order_name):
    """
    Get detailed information about a specific sales order.
    
    Args:
        sales_order_name (str): Name of the sales order to retrieve
        
    Returns:
        dict: Sales order details including items, customer info, and totals
    """
    try:
        # Check if user has permission to access the sales order
        if not frappe.has_permission("Sales Order", "read", sales_order_name):
            frappe.throw(_("You don't have permission to access this sales order"), frappe.PermissionError)
            
        # Get the sales order document
        sales_order = frappe.get_doc("Sales Order", sales_order_name)
        
        # Prepare the response
        details = {
            "name": sales_order.name,
            "customer": sales_order.customer,
            "customer_name": sales_order.customer_name,
            "transaction_date": sales_order.transaction_date,
            "delivery_date": sales_order.delivery_date,
            "status": sales_order.status,
            "total_qty": sales_order.total_qty,
            "base_total": sales_order.base_total,
            "base_net_total": sales_order.base_net_total,
            "base_grand_total": sales_order.base_grand_total,
            "company": sales_order.company,
            "currency": sales_order.currency,
            "conversion_rate": sales_order.conversion_rate,
            "items": [],
            "taxes": []
        }
        
        # Add item details
        for item in sales_order.items:
            details["items"].append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor,
                "warehouse": item.warehouse
            })
            
        # Add tax details if any
        for tax in sales_order.taxes:
            details["taxes"].append({
                "charge_type": tax.charge_type,
                "account_head": tax.account_head,
                "description": tax.description,
                "rate": tax.rate,
                "tax_amount": tax.tax_amount,
                "total": tax.total
            })
            
        # Get any linked sales invoice if exists
        linked_invoice = get_sales_invoice_by_order(sales_order.name)
        if linked_invoice:
            details["linked_invoice"] = linked_invoice
            
        return {
            "status": "success",
            "data": details
        }
        
    except frappe.DoesNotExistError:
        frappe.throw(_("Sales Order {0} does not exist").format(sales_order_name))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to fetch sales order details")
        frappe.throw(_("Failed to fetch sales order details: {0}").format(str(e)))



def get_item_loadings(warehouse, date, salesman_user):
    """
    Get loading details from Stock Ledger Entry for the given warehouse and date
    
    Args:
        warehouse (str): Warehouse name
        date (str): Date in YYYY-MM-DD format
        salesman_user (str): Salesman email
        
    Returns:
        dict: {item_code: [{"voucher_no": str, "qty": float, "date": str, "voucher_type": str}, ...]}
    """
    from frappe.utils import get_datetime
    
    # Get the start and end of the day
    start_date = f"{date} 00:00:00"
    end_date = f"{date} 23:59:59"
    
    # Query Stock Ledger Entry for loading transactions
    entries = frappe.db.sql("""
        SELECT 
            item_code,
            voucher_no,
            voucher_type,
            posting_date,
            posting_time,
            qty_after_transaction,
            actual_qty as qty
        FROM `tabStock Ledger Entry`
        WHERE warehouse = %(warehouse)s
        AND posting_datetime BETWEEN %(start_date)s AND %(end_date)s
        AND voucher_type = 'Stock Entry'
        AND actual_qty > 0  # Only positive quantities (incoming)
        AND docstatus = 1   # Only submitted documents
        AND exists (
            SELECT 1 FROM `tabStock Entry` se 
            WHERE se.name = voucher_no 
            AND se.purpose = 'Material Transfer'
            AND (se.owner = %(salesman_user)s OR se.modified_by = %(salesman_user)s)
        )
        ORDER BY posting_date, posting_time, name
    """, {
        'warehouse': warehouse,
        'start_date': start_date,
        'end_date': end_date,
        'salesman_user': salesman_user
    }, as_dict=1)
    
    # Group by item_code
    item_loadings = {}
    for entry in entries:
        if entry.item_code not in item_loadings:
            item_loadings[entry.item_code] = []
            
        item_loadings[entry.item_code].append({
            "voucher_no": entry.voucher_no,
            "qty": float(entry.qty),
            "date": f"{entry.posting_date} {entry.posting_time}",
            "voucher_type": entry.voucher_type
        })
    
    return item_loadings

@frappe.whitelist()
def get_salesman_daily_closing_inventory(date=None, warehouse=None, salesman_user=None, include_vouchers=0, only_movement=0):
    """
    Get daily closing inventory for a salesman
    
    Args:
        date (str): Date in YYYY-MM-DD format (default: today)
        warehouse (str): Warehouse to filter by (required)
        salesman_user (str): Email of the salesman (default: current user)
        include_vouchers (int): Whether to include voucher details (0 or 1, default: 0)
        only_movement (int): Whether to show only items with movement (0 or 1, default: 0)
        
    Returns:
        dict: {
            "date": "YYYY-MM-DD",
            "warehouse": "Warehouse Name",
            "salesman_user": "user@example.com",
            "items": [
                {
                    "item_code": "ITEM-001",
                    "item_name": "Sample Item",
                    "uom": "Nos",
                    "opening_qty": 10.0,        # Opening stock at the start of the day
                    "loading_request_qty": 5.0,  # Quantity requested in loading requests
                    "sold_qty": 3.0,            # Total quantity sold (out_qty)
                    "in_qty": 5.0,              # Total incoming quantity
                    "out_qty": 3.0,             # Total outgoing quantity
                    "closing_qty": 12.0,         # Closing stock at the end of the day
                    "opening_value": 1000.0,     # Value of opening stock
                    "closing_value": 1200.0,     # Value of closing stock
                    "sales_amount": 0.0          # Total sales amount
                }
            ],
            "summary": {
                "total_items": 1,
                "total_opening_value": 1000.0,
                "total_loading_request_qty": 5.0,
                "total_sold_qty": 3.0,
                "total_in_qty": 5.0,
                "total_out_qty": 3.0,
                "total_closing_value": 1200.0
            }
        }
    """
    from frappe.utils import getdate, today
    from salesman_journey.salesman_journey.report.salesman_daily_stock_closing.salesman_daily_stock_closing import execute
    
    # Set default values
    if not date:
        date = today()
    
    if not warehouse:
        frappe.throw("Warehouse is required")
    
    if not salesman_user:
        salesman_user = frappe.session.user
    
    # Prepare filters for the report
    filters = {
        "warehouse": warehouse,
        "salesman_user": salesman_user,
        "include_vouchers": int(include_vouchers),
        "only_movement": int(only_movement),
        "posting_date": date
    }
    
    try:
        # Execute the report to get the data
        columns, data = execute(filters)
        
        # Get loading request quantities for the day
        loading_requests = get_loading_requests(warehouse, date, salesman_user)
        
        # Get loading details from Stock Ledger Entry
        item_loadings = get_item_loadings(warehouse, date, salesman_user)

        # Process the data for the API response
        items = []
        total_opening_qty = 0.0
        total_opening_value = 0.0
        total_loading_request_qty = 0.0
        total_sold_qty = 0.0
        total_in_qty = 0.0
        total_out_qty = 0.0
        total_closing_value = 0.0
        
        for row in data:
            if row.get("section") == "SUMMARY":
                item_code = row.get("item_code", "")
                out_qty = float(row.get("out_qty", 0))
                
                # Get loading request quantity for this item
                loading_request_qty = loading_requests.get(item_code, 0.0)
                
            
                # Get loading details for this item
                loadings = item_loadings.get(item_code, [])
                
                
                item = {
                    "item_code": item_code,
                    "item_name": row.get("item_name", ""),
                    "uom": row.get("uom", ""),
                    "opening_qty": float(row.get("opening_qty", 0)),
                    "loading_request_qty": loading_request_qty,
                    "sold_qty": out_qty,  # Assuming all out_qty is sold quantity
                    "in_qty": float(row.get("in_qty", 0)),
                    "out_qty": out_qty,
                    "closing_qty": float(row.get("closing_qty", 0)),
                    "opening_value": float(row.get("opening_value", 0)),
                    "sales_amount": float(row.get("sales_amount", 0)),
                    "loadings": loadings 
                }
                
                # Calculate closing value using the same rate as opening
                closing_value = item["closing_qty"] * (item["opening_value"] / item["opening_qty"]) if item["opening_qty"] else 0
                item["closing_value"] = closing_value
                
                items.append(item)
                
                # Update totals
                total_opening_qty += item["opening_qty"]
                total_opening_value += item["opening_value"]
                total_loading_request_qty += loading_request_qty
                total_sold_qty += out_qty
                total_in_qty += item["in_qty"]
                total_out_qty += out_qty
                total_closing_value += closing_value
        
        # Prepare the response
        response = {
            "date": str(getdate(date)),
            "warehouse": warehouse,
            "salesman_user": salesman_user,
            "items": items,
            "summary": {
                "total_items": len(items),
                "total_opening_value": total_opening_value,
                "total_opening_qty": total_opening_qty,
                "total_loading_request_qty": total_loading_request_qty,
                "total_sold_qty": total_sold_qty,
                "total_in_qty": total_in_qty,
                "total_out_qty": total_out_qty,
                "total_closing_value": total_closing_value
            }
        }
        
        return response
        
    except Exception as e:
        frappe.log_error(f"Error in get_salesman_daily_closing_inventory: {str(e)}")
        frappe.throw(f"Failed to get daily closing inventory: {str(e)}")

def get_item_loadings(warehouse, date, salesman_user):
    """
    Get loading details from Stock Ledger Entry for the given warehouse and date
    
    Args:
        warehouse (str): Warehouse name
        date (str): Date in YYYY-MM-DD format
        salesman_user (str): Salesman email
        
    Returns:
        dict: {item_code: [{"voucher_no": str, "qty": float, "date": str, "voucher_type": str}, ...]}
    """
    from frappe.utils import get_datetime
    
    # Get the start and end of the day
    start_date = f"{date} 00:00:00"
    end_date = f"{date} 23:59:59"
    
    # Query Stock Ledger Entry for loading transactions
    entries = frappe.db.sql("""
        SELECT 
            item_code,
            voucher_no,
            voucher_type,
            posting_date,
            posting_time,
            qty_after_transaction,
            actual_qty as qty
        FROM `tabStock Ledger Entry`
        WHERE warehouse = %(warehouse)s
        AND posting_datetime BETWEEN %(start_date)s AND %(end_date)s
        AND voucher_type = 'Stock Entry'
        AND actual_qty > 0  # Only positive quantities (incoming)
        AND docstatus = 1   # Only submitted documents
        AND exists (
            SELECT 1 FROM `tabStock Entry` se 
            WHERE se.name = voucher_no 
            AND se.purpose = 'Material Transfer'
            AND (se.owner = %(salesman_user)s OR se.modified_by = %(salesman_user)s)
        )
        ORDER BY posting_date, posting_time, name
    """, {
        'warehouse': warehouse,
        'start_date': start_date,
        'end_date': end_date,
        'salesman_user': salesman_user
    }, as_dict=1)
    
    # Group by item_code
    item_loadings = {}
    for entry in entries:
        if entry.item_code not in item_loadings:
            item_loadings[entry.item_code] = []
            
        item_loadings[entry.item_code].append({
            "voucher_no": entry.voucher_no,
            "qty": float(entry.qty),
            "date": f"{entry.posting_date} {entry.posting_time}",
            "voucher_type": entry.voucher_type
        })
    
    return item_loadings
    
def get_loading_requests(warehouse, date, salesman_user):
    """
    Get total loading request quantities by item for the given warehouse and date
    
    Args:
        warehouse (str): Warehouse name
        date (str): Date in YYYY-MM-DD format
        salesman_user (str): Salesman email
        
    Returns:
        dict: {item_code: total_quantity}
    """
    loading_requests = {}
    
    # Query Material Request with Material Request Type = "Material Transfer"
    # that are linked to the salesman and warehouse
    requests = frappe.db.sql("""
        SELECT mri.item_code, SUM(mri.qty) as total_qty
        FROM `tabMaterial Request Item` mri
        INNER JOIN `tabMaterial Request` mr ON mri.parent = mr.name
        WHERE mr.material_request_type = 'Material Transfer'
        AND mr.docstatus = 1  # Submitted documents
        AND mr.owner = %(salesman_user)s
        AND mri.warehouse = %(warehouse)s
        AND DATE(mr.transaction_date) = %(date)s
        GROUP BY mri.item_code
    """, {
        'warehouse': warehouse,
        'date': date,
        'salesman_user': salesman_user
    }, as_dict=1)
    
    # Convert to dictionary for easy lookup
    for req in requests:
        loading_requests[req.item_code] = float(req.total_qty)
    
    return loading_requests

@frappe.whitelist()
def get_financial_closing_summary(date=None, salesman=None):
    """
    Get financial closing summary with cash and MADA transfers for a specific date.
    
    Args:
        date (str): Date in YYYY-MM-DD format (default: today)
        salesman (str): Email of the salesman to filter by (default: current user)
        
    Returns:
        dict: {
            "date": "2023-01-01",
            "total_sales": 10000.0,
            "cash_total": 6000.0,
            "mada_total": 4000.0,
            "invoices": [
                {"name": "SINV-0001", "total": 5000.0, "is_pos": 1, "payment_type": "Cash"},
                ...
            ]
        }
    """
    from frappe.utils import getdate, today, flt
    
    # Set default date to today if not provided
    date = getdate(date) if date else getdate(today())
    
    # Set default salesman to current user if not provided
    if not salesman:
        salesman = frappe.session.user
            # Get all sales invoices with their payment modes
    invoices = frappe.db.sql("""
        SELECT 
            si.name, 
            si.grand_total, 
            si.is_pos,
            sip.mode_of_payment
        FROM 
            `tabSales Invoice` si
        LEFT JOIN 
            `tabSales Invoice Payment` sip ON sip.parent = si.name
        WHERE 
            si.docstatus = 1 
            AND si.posting_date = %s 
            AND si.owner = %s
        ORDER BY 
            si.posting_date, si.posting_time, si.name
    """, (date, salesman), as_dict=1)
    
    # Initialize totals and invoice dictionary
    result = {
        "date": date.strftime("%Y-%m-%d"),
        "total_sales": 0.0,
        "cash_total": 0.0,
        "mada_total": 0.0,
        "temp_credit_total": 0.0,
        "invoices": {}
    }
        # Process each payment entry
    for inv in invoices:
        if inv.name not in result["invoices"]:
            result["invoices"][inv.name] = {
                "name": inv.name,
                "total": flt(inv.grand_total),
                "is_pos": inv.is_pos,
                "payment_types": set(),
                "payment_type": "Not Specified"
            }
        
        # Add payment type to the set of payment types for this invoice
        if inv.mode_of_payment:
            result["invoices"][inv.name]["payment_types"].add(inv.mode_of_payment.lower())
    
    # Process each invoice to determine payment type and update totals
    for inv_name, inv_data in result["invoices"].items():
        payment_types = inv_data.pop("payment_types")
        
        # Determine payment type
        if inv_data["is_pos"]:
            if any("mada" in pt for pt in payment_types):
                result["mada_total"] += flt(inv_data["total"])
                inv_data["payment_type"] = "MADA"
            else:
                result["cash_total"] += flt(inv_data["total"])
                inv_data["payment_type"] = "Cash"
        else:
            # For non-POS invoices, set payment type to temp_credit
            inv_data["payment_type"] = "Temp Credit"
            result["temp_credit_total"] += flt(inv_data["total"])

        # Convert set to list for JSON serialization
        inv_data["payment_modes"] = list(payment_types) if payment_types else ["Not Specified"]
    
    # Convert invoice dictionary to list
    result["invoices"] = list(result["invoices"].values())
    
    # Calculate total sales
    result["total_sales"] = result["cash_total"] + result["mada_total"] + result["temp_credit_total"]
    

    return result







