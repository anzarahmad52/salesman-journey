import frappe
import json
from frappe.utils import getdate, add_days, today, nowdate, now_datetime, cint
from collections import defaultdict
from datetime import timedelta, date
from frappe import _

# def _require_supervisor():
#     """Check if current user has supervisor permissions"""
#     if not frappe.has_permission("Sales Invoice", "read"):
#         frappe.throw(_("Insufficient permissions"))

def _require_supervisor():
    roles = set(frappe.get_roles())
    if not roles & {"Sales Supervisor", "System Manager"}:
        frappe.throw(_("Only Sales Supervisor can perform this action."), frappe.PermissionError)


# def _salesmen_under_perm():
#     """
#     Return list of salesman users filtered by supervisor's territory permissions.
#     Uses User Permissions for territory assignments (standard ERPNext approach).
#     """
#     # Get current supervisor's permitted territories
#     supervisor_territories = []
#     try:
#         from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
#         supervisor_territories = get_permitted_documents("Territory")
#     except Exception:
#         pass
    
#     # Build territory filter condition for User Permissions
#     territory_condition = ""
#     territory_params = []
#     if supervisor_territories:
#         placeholders = ', '.join(['%s'] * len(supervisor_territories))
#         territory_condition = f"""
#             AND EXISTS (
#                 SELECT 1 FROM `tabUser Permission` up_terr
#                 WHERE up_terr.user = u.name 
#                 AND up_terr.allow = 'Territory'
#                 AND up_terr.for_value IN ({placeholders})
#             )
#         """
#         territory_params = supervisor_territories
    
#     query = f"""
#         SELECT DISTINCT
#             u.name AS user,
#             CONCAT_WS(' ', u.first_name, u.last_name) AS full_name,
#             u.email,
#             u.mobile_no,
#             u.enabled,
            
#             /* Get Employee name if linked */
#             (SELECT e.employee_name FROM `tabEmployee` e 
#              WHERE e.user_id = u.name LIMIT 1) AS employee_name,
            
#             /* Get Employee ID if linked */
#             (SELECT e.name FROM `tabEmployee` e 
#              WHERE e.user_id = u.name LIMIT 1) AS employee_id,

#             /* Primary warehouse from User Permissions */
#             (SELECT up.for_value
#                FROM `tabUser Permission` up
#               WHERE up.user = u.name AND up.allow = 'Warehouse'
#               ORDER BY up.creation ASC
#               LIMIT 1) AS primary_warehouse,

#             /* All warehouses from User Permissions as comma-separated */
#             (SELECT GROUP_CONCAT(DISTINCT up.for_value SEPARATOR ', ')
#                FROM `tabUser Permission` up
#               WHERE up.user = u.name AND up.allow = 'Warehouse') AS all_warehouses,

#             /* Primary territory from User Permissions */
#             (SELECT up2.for_value
#                FROM `tabUser Permission` up2
#               WHERE up2.user = u.name AND up2.allow = 'Territory'
#               ORDER BY up2.creation ASC
#               LIMIT 1) AS route,
              
#             /* All territories from User Permissions as comma-separated */
#             (SELECT GROUP_CONCAT(DISTINCT up2.for_value SEPARATOR ', ')
#                FROM `tabUser Permission` up2
#               WHERE up2.user = u.name AND up2.allow = 'Territory') AS all_routes

#         FROM `tabUser` u
#         WHERE u.enabled = 1
#           AND EXISTS (
#               SELECT 1 FROM `tabHas Role` hr
#                WHERE hr.parent = u.name AND hr.role = 'Sales User'
#           )
#           {territory_condition}
#         ORDER BY u.first_name, u.last_name
#     """
    
#     # Get basic salesman data
#     salesmen = frappe.db.sql(query, territory_params, as_dict=True)
    
#     # Get customers by territory for each salesman
#     for salesman in salesmen:
#         # Get salesman's territories
#         salesman_territories = []
#         if salesman.get('all_routes'):
#             salesman_territories = [t.strip() for t in salesman['all_routes'].split(',')]
#         elif salesman.get('route'):
#             salesman_territories = [salesman['route']]
        
#         # Get customers in those territories
#         customer_details = []
#         customer_count = 0
        
#         if salesman_territories:
#             # Get customers from all assigned territories
#             customer_details = frappe.db.sql("""
#                 SELECT 
#                     c.name as customer_code,
#                     c.customer_name,
#                     c.territory,
#                     c.customer_group,
#                     c.disabled,
#                     c.customer_type
#                 FROM `tabCustomer` c
#                 WHERE c.territory IN ({})
#                 AND c.disabled = 0
#                 ORDER BY c.customer_name
#             """.format(', '.join(['%s'] * len(salesman_territories))), 
#             salesman_territories, as_dict=True)
            
#             customer_count = len(customer_details)
        
#         # Add customer data to salesman record
#         # salesman['customers'] = customer_details
#         # salesman['customer_count'] = customer_count
#         salesman['active_customers'] = customer_details  # All are active since we filter disabled=0
#         salesman['active_customer_count'] = customer_count
        
#         # Create comma-separated customer list for backward compatibility
#         salesman['all_customers'] = ', '.join([c['customer_code'] for c in customer_details])
    
#     return salesmen

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

def _get_date_range(filter_type, from_date=None, to_date=None):
    """Get date range based on filter type"""
    if filter_type == "Today":
        return today(), today()
    elif filter_type == "Yesterday":
        yesterday = add_days(today(), -1)
        return yesterday, yesterday
    elif filter_type == "Week":
        start_of_week = add_days(today(), -getdate(today()).weekday())
        return start_of_week, today()
    elif filter_type == "Month":
        start_of_month = getdate(today()).replace(day=1)
        return start_of_month, today()
    elif filter_type == "Custom" and from_date and to_date:
        return getdate(from_date), getdate(to_date)
    else:
        return today(), today()

@frappe.whitelist()
def supervisor_total_sales(filter="Today", from_date=None, to_date=None, salesmen=None, territories=None):
    """Get total sales data for supervisor dashboard"""
    start_date, end_date = _get_date_range(filter, from_date, to_date)
    
    conditions = []
    values = {"start_date": start_date, "end_date": end_date}
    
    if salesmen:
        if isinstance(salesmen, str):
            salesmen = json.loads(salesmen)
        conditions.append("si.custom_salesman IN %(salesmen)s")
        values["salesmen"] = salesmen
    
    if territories:
        if isinstance(territories, str):
            territories = json.loads(territories)
        conditions.append("si.territory IN %(territories)s")
        values["territories"] = territories
    
    where_clause = " AND " + " AND ".join(conditions) if conditions else ""
    
    query = f"""
        SELECT 
            COALESCE(SUM(si.net_total), 0) as net_sales,
            COUNT(si.name) as invoice_count
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 
            AND si.posting_date BETWEEN %(start_date)s AND %(end_date)s
            {where_clause}
    """
    
    result = frappe.db.sql(query, values, as_dict=True)[0]
    
    return {
        "from_date": start_date,
        "to_date": end_date,
        "net_sales": result.net_sales or 0,
        "invoice_count": result.invoice_count or 0
    }

@frappe.whitelist()
def supervisor_collections(filter="Today", from_date=None, to_date=None, salesmen=None, territories=None):
    """Get collections data for supervisor dashboard"""
    start_date, end_date = _get_date_range(filter, from_date, to_date)
    
    conditions = []
    values = {"start_date": start_date, "end_date": end_date}
    
    if salesmen:
        if isinstance(salesmen, str):
            salesmen = json.loads(salesmen)
        conditions.append("pe.custom_salesman IN %(salesmen)s")
        values["salesmen"] = salesmen
    
    if territories:
        if isinstance(territories, str):
            territories = json.loads(territories)
        conditions.append("pe.custom_territory IN %(territories)s")
        values["territories"] = territories
    
    where_clause = " AND " + " AND ".join(conditions) if conditions else ""
    
    query = f"""
        SELECT 
            COALESCE(SUM(pe.paid_amount), 0) as collections,
            COUNT(pe.name) as payment_count
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1 
            AND pe.posting_date BETWEEN %(start_date)s AND %(end_date)s
            AND pe.payment_type = 'Receive'
            {where_clause}
    """
    
    result = frappe.db.sql(query, values, as_dict=True)[0]
    
    return {
        "from_date": start_date,
        "to_date": end_date,
        "collections": result.collections or 0,
        "payment_count": result.payment_count or 0
    }

# @frappe.whitelist()
# def supervisor_today_visits_orders(doctype_name=None, salesman_field="salesman", date_field="visit_date",
#                                    filter="Today", from_date=None, to_date=None, salesmen=None, territories=None):
#     """Get visits and orders data for supervisor dashboard"""
#     start_date, end_date = _get_date_range(filter, from_date, to_date)
    
#     # If no specific doctype for visits, just get orders data
#     if not doctype_name:
#         visits_count = 0
#     else:
#         # Try to get visits from specified doctype
#         try:
#             conditions = []
#             values = {"start_date": start_date, "end_date": end_date}
            
#             if salesmen:
#                 if isinstance(salesmen, str):
#                     salesmen = json.loads(salesmen)
#                 conditions.append(f"t.{salesman_field} IN %(salesmen)s")
#                 values["salesmen"] = salesmen
            
#             if territories:
#                 if isinstance(territories, str):
#                     territories = json.loads(territories)
#                 conditions.append("t.territory IN %(territories)s")
#                 values["territories"] = territories
            
#             where_clause = " AND " + " AND ".join(conditions) if conditions else ""
            
#             visits_query = f"""
#                 SELECT COUNT(*) as visits_count
#                 FROM `tab{doctype_name}` t
#                 WHERE t.docstatus != 2 
#                     AND DATE(t.{date_field}) BETWEEN %(start_date)s AND %(end_date)s
#                     {where_clause}
#             """
            
#             visits_result = frappe.db.sql(visits_query, values, as_dict=True)[0]
#             visits_count = visits_result.visits_count or 0
#         except Exception:
#             # If doctype or field doesn't exist, default to 0
#             visits_count = 0
    
#     # Get orders data from Sales Orders using correct field names
#     orders_conditions = []
#     values = {"start_date": start_date, "end_date": end_date}
    
#     if salesmen:
#         if isinstance(salesmen, str):
#             salesmen = json.loads(salesmen)
#         # Check if custom_salesman field exists, otherwise use standard fields
#         orders_conditions.append("(so.custom_salesman IN %(salesmen)s OR so.owner IN %(salesmen)s)")
#         values["salesmen"] = salesmen
    
#     if territories:
#         if isinstance(territories, str):
#             territories = json.loads(territories)
#         orders_conditions.append("so.territory IN %(territories)s")
#         values["territories"] = territories
    
#     orders_where = " AND " + " AND ".join(orders_conditions) if orders_conditions else ""
    
#     orders_query = f"""
#         SELECT 
#             COUNT(so.name) as orders_count,
#             COALESCE(SUM(so.net_total), 0) as orders_amount
#         FROM `tabSales Order` so
#         WHERE so.docstatus = 1 
#             AND so.transaction_date BETWEEN %(start_date)s AND %(end_date)s
#             {orders_where}
#     """
    
#     orders_result = frappe.db.sql(orders_query, values, as_dict=True)[0]
    
#     return {
#         "from_date": start_date,
#         "to_date": end_date,
#         "visits_count": visits_count,
#         "orders_count": orders_result.orders_count or 0,
#         "orders_amount": orders_result.orders_amount or 0
#     }
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
    
@frappe.whitelist()
def get_supervisor_stock_balance():
    """
    Get stock balance for all salesmen under the supervisor's territory.
    
    Returns:
        dict: {
            "total_value": float,  # Total stock value across all salesmen
            "warehouses": list,   # List of all warehouses with stock
            "salesmen": [         # List of salesmen with their stock details
                {
                    "user_id": str,
                    "full_name": str,
                    "total_value": float,
                    "warehouses": [
                        {
                            "name": str,
                            "total_value": float,
                            "items": [
                                {
                                    "item_code": str,
                                    "item_name": str,
                                    "qty": float,
                                    "value": float
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    """
    _require_supervisor()
    
    # Get all salesmen under supervisor
    salesmen = _salesmen_under_perm()
    if not salesmen:
        return {
            "total_value": 0,
            "warehouses": [],
            "salesmen": []
        }
    
    result = {
        "total_value": 0,
        "warehouses": set(),
        "salesmen": []
    }
    
    # Import the salesman function to reuse its logic
    from salesman_journey.api.salesman import get_salesman_stock_balance
    
    for salesman in salesmen:
        try:
            # Get stock balance for each salesman
            stock_data = get_salesman_stock_balance(salesman.user)
            
            if not stock_data or "error" in stock_data:
                continue
                
            # Add warehouses to the global set
            for wh in stock_data.get("warehouses", []):
                result["warehouses"].add(wh["name"])
            
            # Add salesman data
            salesman_data = {
                "user_id": salesman.user,
                "full_name": frappe.get_value("User", salesman.user, "full_name") or salesman.user,
                "total_value": stock_data.get("total_value", 0),
                "warehouses": stock_data.get("warehouses", [])
            }
            
            result["salesmen"].append(salesman_data)
            result["total_value"] += stock_data.get("total_value", 0)
            
        except Exception as e:
            frappe.log_error(
                title=f"Error getting stock balance for salesman {salesman.user}",
                message=frappe.get_traceback()
            )
    
    # Convert set to list for JSON serialization
    result["warehouses"] = list(result["warehouses"])
    
    return result

@frappe.whitelist()
def supervisor_get_consolidated_stock_balance(warehouses=None, item_code=None, page=1, page_len=50, include_zero=0):
    """
    Get consolidated stock balance for all salesmen under supervisor's territory.
    
    Args:
        warehouses: JSON list of warehouse names (optional)
        item_code: filter by item (optional)
        page, page_len: pagination (ints)
        include_zero: '0' or '1' (exclude zero rows by default)
    """
    _require_supervisor()
    
    # Get all salesmen under supervisor
    salesmen = _salesmen_under_perm()
    if not salesmen:
        return {
            "total": 0,
            "rows": [],
            "page": cint(page),
            "page_len": cint(page_len),
            "summary": {
                "total_items": 0,
                "total_warehouses": 0,
                "total_stock_value": 0,
                "salesman_count": 0
            }
        }
    
    # Get all warehouses from all salesmen
    all_warehouses = set()
    salesman_warehouses = {}
    
    for salesman in salesmen:
        try:
            # Get warehouse permissions for each salesman
            from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
            whs = get_permitted_documents("Warehouse", user=salesman.user) or []
            if whs:
                all_warehouses.update(whs)
                salesman_warehouses[salesman.user] = whs
        except Exception as e:
            frappe.log_error(f"Error getting warehouses for salesman {salesman.user}: {str(e)}")
    
    # Apply warehouse filter if provided
    if warehouses:
        try:
            wh_list = json.loads(warehouses) if isinstance(warehouses, str) else warehouses
            if isinstance(wh_list, list):
                all_warehouses = all_warehouses & set(wh_list)
        except Exception:
            pass
    
    if not all_warehouses:
        return {
            "total": 0,
            "rows": [],
            "page": cint(page),
            "page_len": cint(page_len),
            "summary": {
                "total_items": 0,
                "total_warehouses": 0,
                "total_stock_value": 0,
                "salesman_count": 0
            }
        }
    
    # Build base query
    where = ["b.warehouse IN ({})".format(", ".join(["%s"] * len(all_warehouses)))]
    params = list(all_warehouses)
    
    if item_code:
        where.append("b.item_code = %s")
        params.append(item_code)
    
    if not cint(include_zero):
        where.append("(b.actual_qty <> 0 OR b.reserved_qty <> 0 OR b.planned_qty <> 0)")
    
    # Add pagination
    offset = (cint(page) - 1) * cint(page_len)
    params.extend([cint(page_len), offset])
    
    # Main query to get stock data
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
            (b.actual_qty * b.valuation_rate) as stock_value,
            (
                SELECT GROUP_CONCAT(DISTINCT up.user SEPARATOR ', ')
                FROM `tabUser Permission` up
                WHERE up.allow = 'Warehouse' 
                AND up.for_value = b.warehouse
                AND up.user IN ({','.join(['%s']*len(salesman_warehouses))})
            ) as salesmen
        FROM `tabBin` b
        LEFT JOIN `tabItem` i ON i.name = b.item_code
        LEFT JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE {" AND ".join(where)}
        ORDER BY b.warehouse, b.item_code
        LIMIT %s OFFSET %s
    """
    
    # Add salesman users to params for the subquery
    params.extend(salesman_warehouses.keys())
    
    # Execute query
    rows = frappe.db.sql(query, params, as_dict=True)
    
    # Get total count for pagination
    count_query = f"""
        SELECT COUNT(DISTINCT CONCAT(b.warehouse, b.item_code)) as total
        FROM `tabBin` b
        WHERE {" AND ".join(where)}
    """
    total = frappe.db.sql(count_query, params[:-2], as_dict=True)[0].get('total', 0)
    
    # Calculate summary statistics
    summary = {
        "total_items": len(set(row["item_code"] for row in rows)),
        "total_warehouses": len(set(row["warehouse"] for row in rows)),
        "total_stock_value": sum(float(row.get("stock_value") or 0) for row in rows),
        "salesman_count": len(salesman_warehouses)
    }
    
    # Add salesman names to each row
    for row in rows:
        if row.get('salesmen'):
            salesman_names = []
            for user_id in row['salesmen'].split(', '):
                full_name = frappe.get_value('User', user_id, 'full_name') or user_id
                salesman_names.append(full_name)
            row['salesman_names'] = ', '.join(salesman_names)
    
    return {
        "total": total,
        "rows": rows,
        "page": cint(page),
        "page_len": cint(page_len),
        "summary": summary,
        "total_warehouses": len(all_warehouses),
        "total_salesmen": len(salesman_warehouses)
    }

@frappe.whitelist()
def create_material_request_supervisor(data=None, docname=None):
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

    # If docname is provided, it's an update operation
    if docname and frappe.db.exists("Material Request", docname):
        doc = frappe.get_doc("Material Request", docname)
        
        # Check if document is already submitted
        if doc.docstatus == 1:
            frappe.throw(_("Cannot update a submitted Material Request. Please cancel it first."))
            
        # Update the document
        doc.items = []  # Clear existing items
    else:
        # Create new document
        doc = frappe.new_doc("Material Request")
        doc.material_request_type = "Material Transfer"
        doc.set_warehouse = target_warehouse

    # Update common fields
    doc.schedule_date = data.get("required_by") or nowdate()

    # Add/update items
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

    # Save the document
    doc.save(ignore_permissions=True)
    
    # Only submit if it's a new document or if explicitly requested
    if not docname or data.get("submit", True):
        doc.submit()
        message = "Material Request submitted" if doc.docstatus == 1 else "Material Request saved as draft"
    else:
        message = "Material Request updated"

    return {
        "message": message,
        "name": doc.name,
        "docstatus": doc.docstatus
    }