import frappe
from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

@frappe.whitelist()
def get_salesman_customers(salesman_user=None):
    """
    Get all customers assigned to a specific salesman based on territory permissions.
    If no salesman_user is provided, uses the current user.
    
    Args:
        salesman_user (str, optional): Email/username of the salesman. Defaults to current user.
    
    Returns:
        list: List of customer records with details
    """
    # Use current user if no salesman specified
    if not salesman_user:
        salesman_user = frappe.session.user
    
    # Validate that the user exists and is enabled
    user_exists = frappe.db.exists("User", {"name": salesman_user, "enabled": 1})
    if not user_exists:
        frappe.throw(f"User {salesman_user} not found or disabled")
    
    # Check if user has Sales User role
    has_sales_role = frappe.db.exists("Has Role", {
        "parent": salesman_user,
        "role": "Sales User"
    })
    if not has_sales_role:
        frappe.throw(f"User {salesman_user} does not have Sales User role")
    
    # Get salesman's assigned territories from User Permissions
    try:
        salesman_territories = frappe.get_all(
            "User Permission",
            filters={
                "user": salesman_user,
                "allow": "Territory"
            },
            pluck="for_value"
        )
    except Exception:
        salesman_territories = []
    
    if not salesman_territories:
        return []
    
    # Get customers in the salesman's territories
    customers = frappe.db.sql("""
        SELECT 
            c.name as customer_code,
            c.customer_name,
            c.territory,
            c.customer_group,
            c.customer_type,
            c.mobile_no,
            c.email_id,
            c.latitude,
            c.longitude,
            c.disabled,
            c.creation,
            c.modified
        FROM `tabCustomer` c
        WHERE c.territory IN ({})
        AND c.disabled = 0
        ORDER BY c.customer_name
    """.format(', '.join(['%s'] * len(salesman_territories))), 
    salesman_territories, as_dict=True)
    
    return {
        "salesman": salesman_user,
        "territories": salesman_territories,
        "customer_count": len(customers),
        "customers": customers
    }

@frappe.whitelist()
def get_current_user_customers():
    """
    Convenience method to get customers for the current logged-in user.
    
    Returns:
        list: List of customer records for current user
    """
    return get_salesman_customers()

# @frappe.whitelist()
# def get_salesman_profile(salesman_user=None):
#     """
#     Get comprehensive profile information for a salesman.
#     If no salesman_user is provided, uses the current user.
    
#     Args:
#         salesman_user (str, optional): Email/username of the salesman. Defaults to current user.
    
#     Returns:
#         dict: Salesman profile with user details, territories, permissions, and stats
#     """
#     # Use current user if no salesman specified
#     if not salesman_user:
#         salesman_user = frappe.session.user
    
#     # Validate that the user exists and is enabled
#     user_exists = frappe.db.exists("User", {"name": salesman_user, "enabled": 1})
#     if not user_exists:
#         frappe.throw(f"User {salesman_user} not found or disabled")
    
#     # Check if user has Sales User role
#     has_sales_role = frappe.db.exists("Has Role", {
#         "parent": salesman_user,
#         "role": "Sales User"
#     })
#     if not has_sales_role:
#         frappe.throw(f"User {salesman_user} does not have Sales User role")
    
#     # Get user document
#     user_doc = frappe.get_doc("User", salesman_user)
    
#     # Get user roles
#     roles = frappe.get_roles(salesman_user)
    
#     # Helper to fetch user permissions for any linked DocType
#     def get_user_permissions_for(doctype):
#         return frappe.get_all(
#             "User Permission",
#             filters={"user": salesman_user, "allow": doctype},
#             pluck="for_value"
#         )
    
#     # Get territories and customer count
#     territories = get_user_permissions_for("Territory")
#     customer_count = 0
#     if territories:
#         customer_count = frappe.db.count("Customer", {
#             "territory": ["in", territories],
#             "disabled": 0
#         })
    
#     # Get recent sales stats (last 30 days)
#     from frappe.utils import add_days, nowdate
#     thirty_days_ago = add_days(nowdate(), -30)
    
#     sales_stats = frappe.db.sql("""
#         SELECT 
#             COUNT(*) as invoice_count,
#             COALESCE(SUM(grand_total), 0) as total_sales
#         FROM `tabSales Invoice` si
#         LEFT JOIN `tabCustomer` c ON c.name = si.customer
#         WHERE si.docstatus = 1 
#         AND si.posting_date >= %s
#         AND si.owner = %s
#         AND (c.territory IN ({}) OR %s = 1)
#     """.format(', '.join(['%s'] * len(territories)) if territories else ''), 
#     [thirty_days_ago, salesman_user] + territories + [1 if not territories else 0], 
#     as_dict=True)[0] if territories else {"invoice_count": 0, "total_sales": 0}
    
#     return {
#         "user": salesman_user,
#         "full_name": user_doc.full_name or f"{user_doc.first_name} {user_doc.last_name or ''}".strip(),
#         "first_name": user_doc.first_name,
#         "last_name": user_doc.last_name,
#         "email": user_doc.email,
#         "mobile_no": user_doc.mobile_no,
#         "user_image": user_doc.user_image or "",
#         "enabled": user_doc.enabled,
#         "creation": user_doc.creation,
#         "last_login": user_doc.last_login,
#         "roles": roles,
#         "territories": territories,
#         "warehouses": get_user_permissions_for("Warehouse"),
#         "customer_groups": get_user_permissions_for("Customer Group"),
#         "cost_centers": get_user_permissions_for("Cost Center"),
#         "pos_profiles": get_user_permissions_for("POS Profile"),
#         "customer_count": customer_count,
#         "sales_stats_30_days": {
#             "invoice_count": sales_stats["invoice_count"],
#             "total_sales": float(sales_stats["total_sales"] or 0)
#         }
#     }


@frappe.whitelist()
def get_current_user_profile():
    """
    Convenience method to get profile for the current logged-in user.
    
    Returns:
        dict: Current user's salesman profile
    """
    return get_salesman_profile()

@frappe.whitelist()
def get_salesman_stock_balance(salesman_user=None, warehouse=None):
    """
    Get stock balance for a salesman across their permitted warehouses.
    If no salesman_user is provided, uses the current user.
    
    Args:
        salesman_user (str, optional): Email/username of the salesman. Defaults to current user.
        warehouse (str, optional): Specific warehouse to filter by. If not provided, shows all permitted warehouses.
    
    Returns:
        dict: Stock balance summary and item-wise details
    """
    # Use current user if no salesman specified
    if not salesman_user:
        salesman_user = frappe.session.user
    
    # Validate that the user exists and is enabled
    user_exists = frappe.db.exists("User", {"name": salesman_user, "enabled": 1})
    if not user_exists:
        frappe.throw(f"User {salesman_user} not found or disabled")
    
    # Check if user has Sales User role
    has_sales_role = frappe.db.exists("Has Role", {
        "parent": salesman_user,
        "role": "Sales User"
    })
    if not has_sales_role:
        frappe.throw(f"User {salesman_user} does not have Sales User role")
    
    # Get salesman's permitted warehouses
    permitted_warehouses = frappe.get_all(
        "User Permission",
        filters={
            "user": salesman_user,
            "allow": "Warehouse"
        },
        pluck="for_value"
    )
    
    if not permitted_warehouses:
        return {
            "salesman": salesman_user,
            "warehouses": [],
            "total_items": 0,
            "total_stock_value": 0,
            "stock_summary": [],
            "item_details": []
        }
    
    # Filter by specific warehouse if provided
    if warehouse:
        if warehouse not in permitted_warehouses:
            frappe.throw(f"User {salesman_user} does not have permission for warehouse {warehouse}")
        permitted_warehouses = [warehouse]
    
    # Get stock balance from Bin table (current stock levels)
    stock_data = frappe.db.sql("""
        SELECT 
            b.item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            b.warehouse,
            w.warehouse_name,
            b.actual_qty,
            b.reserved_qty,
            b.ordered_qty,
            b.planned_qty,
            (b.actual_qty - b.reserved_qty) as available_qty,
            i.valuation_rate,
            (b.actual_qty * COALESCE(i.valuation_rate, 0)) as stock_value
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        INNER JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE b.warehouse IN ({})
        AND b.actual_qty > 0
        AND i.disabled = 0
        ORDER BY b.warehouse, i.item_name
    """.format(', '.join(['%s'] * len(permitted_warehouses))), 
    permitted_warehouses, as_dict=True)
    
    # Calculate summary by warehouse
    warehouse_summary = {}
    total_stock_value = 0
    
    for item in stock_data:
        warehouse_name = item['warehouse']
        if warehouse_name not in warehouse_summary:
            warehouse_summary[warehouse_name] = {
                "warehouse": warehouse_name,
                "warehouse_name": item['warehouse_name'],
                "item_count": 0,
                "total_qty": 0,
                "total_value": 0
            }
        
        warehouse_summary[warehouse_name]["item_count"] += 1
        warehouse_summary[warehouse_name]["total_qty"] += item['actual_qty']
        warehouse_summary[warehouse_name]["total_value"] += item['stock_value']
        total_stock_value += item['stock_value']
    
    return {
        "salesman": salesman_user,
        "warehouses": permitted_warehouses,
        "total_items": len(stock_data),
        "total_stock_value": float(total_stock_value),
        "stock_summary": list(warehouse_summary.values()),
        "item_details": stock_data
    }

@frappe.whitelist()
def get_current_user_stock_balance(warehouse=None):
    """
    Convenience method to get stock balance for the current logged-in user.
    
    Args:
        warehouse (str, optional): Specific warehouse to filter by.
    
    Returns:
        dict: Current user's stock balance
    """
    return get_salesman_stock_balance(warehouse=warehouse)

@frappe.whitelist()
def get_salesman_stock_summary(salesman_user=None):
    """
    Get a quick stock summary for a salesman (warehouse-wise totals only).
    
    Args:
        salesman_user (str, optional): Email/username of the salesman. Defaults to current user.
    
    Returns:
        dict: Stock summary without item details
    """
    full_data = get_salesman_stock_balance(salesman_user)
    return {
        "salesman": full_data["salesman"],
        "warehouses": full_data["warehouses"],
        "total_items": full_data["total_items"],
        "total_stock_value": full_data["total_stock_value"],
        "stock_summary": full_data["stock_summary"]
    }

@frappe.whitelist()
def get_salesman_recent_orders(salesman_user=None, limit=5):
    """
    Get recent sales orders for a salesman.
    
    Args:
        salesman_user (str, optional): Email/username of the salesman. Defaults to current user.
        limit (int, optional): Number of orders to fetch. Defaults to 5.
    
    Returns:
        dict: Recent sales orders with salesman info
    """
    import frappe
    
    if not salesman_user:
        salesman_user = frappe.session.user
    
    # Verify user permissions - only allow access to own data or if user has appropriate role
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    
    if salesman_user != current_user and not any(role in user_roles for role in ['Sales Manager', 'System Manager']):
        frappe.throw("You don't have permission to view this salesman's orders")
    
    orders = frappe.db.sql("""
        SELECT 
            name, 
            customer, 
            status, 
            grand_total,
            transaction_date,
            creation,
            modified
        FROM `tabSales Order`
        WHERE docstatus != 0
        AND status != 'Completed'
        AND owner = %s
        ORDER BY creation DESC
        LIMIT %s
    """, (salesman_user, limit), as_dict=True)
    
    # Get salesman name for display
    salesman_name = frappe.db.get_value("User", salesman_user, "full_name") or salesman_user
    
    # return {
    #     "salesman": salesman_user,
    #     "salesman_name": salesman_name,
    #     "orders_count": len(orders),
    #     "orders": orders
    # }
    return orders

@frappe.whitelist()
def get_salesman_profile(salesman_user=None):
    """
    Get comprehensive profile information for a salesman with detailed metrics.
    If no salesman_user is provided, uses the current user.
    """
    # 1. Initial Setup and Validation
    if not salesman_user:
        salesman_user = frappe.session.user
    
    if not frappe.db.exists("User", {"name": salesman_user, "enabled": 1}):
        frappe.throw(f"User {salesman_user} not found or disabled")
    
    if not frappe.db.exists("Has Role", {"parent": salesman_user, "role": "Sales User"}):
        frappe.throw(f"User {salesman_user} does not have Sales User role")
    
    # 2. Get Basic User Info
    user_doc = frappe.get_doc("User", salesman_user)
    
    # 3. Get Territories and Warehouses
    def get_user_permissions(doctype):
        return frappe.get_all("User Permission",
            filters={"user": salesman_user, "allow": doctype},
            pluck="for_value"
        ) or []
    
    territories = get_user_permissions("Territory")
    warehouses = get_user_permissions("Warehouse")
    
    # 4. Get Metrics
    metrics = {
        "sales": get_sales_metrics(salesman_user, territories),
        "orders": get_order_metrics(salesman_user, territories),
        "collections": get_collection_metrics(salesman_user, territories),
        "stock": get_stock_metrics(warehouses) if warehouses else {},
        "customers": get_customer_metrics(salesman_user, territories)
    }
    
    # 5. Compile Final Response
    return {
        "user": salesman_user,
        "full_name": user_doc.full_name or f"{user_doc.first_name or ''} {user_doc.last_name or ''}".strip(),
        "email": user_doc.email,
        "mobile_no": user_doc.mobile_no,
        "user_image": user_doc.user_image or "",
        "territories": territories,
        "warehouses": warehouses,
        "metrics": metrics,
        "last_updated": frappe.utils.now()
    }

def get_sales_metrics(salesman_user, territories):
    """Get sales-related metrics for the salesman"""
    conditions = [
        ["docstatus", "=", 1],
        ["owner", "=", salesman_user]
    ]
    
    if territories:
        customers = frappe.get_all("Customer", 
            filters={"territory": ["in", territories], "disabled": 0},
            pluck="name"
        )
        if customers:
            conditions.append(["customer", "in", customers])
    
    # Last 30 days sales
    sales_30d = frappe.db.sql("""
        SELECT 
            SUM(grand_total) as amount, 
            COUNT(*) as count
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        AND owner = %(owner)s
        AND posting_date >= %(from_date)s
        {customer_condition}
    """.format(
        customer_condition="AND customer IN %(customers)s" if customers else ""
    ), {
        "owner": salesman_user,
        "from_date": frappe.utils.add_days(frappe.utils.today(), -30),
        "customers": customers
    } if customers else {
        "owner": salesman_user,
        "from_date": frappe.utils.add_days(frappe.utils.today(), -30)
    }, as_dict=1)
    
    sales_30d = sales_30d[0] if sales_30d else {}
    
    # Current month sales
    month_start = frappe.utils.get_first_day(frappe.utils.today())
    current_month = frappe.db.sql("""
        SELECT SUM(grand_total) as amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        AND owner = %(owner)s
        AND posting_date >= %(from_date)s
        {customer_condition}
    """.format(
        customer_condition="AND customer IN %(customers)s" if customers else ""
    ), {
        "owner": salesman_user,
        "from_date": month_start,
        "customers": customers
    } if customers else {
        "owner": salesman_user,
        "from_date": month_start
    }, as_dict=1)
    
    current_month = current_month[0] if current_month else {}
    
    return {
        "last_30_days": {
            "amount": flt(sales_30d.get("amount")),
            "invoices": sales_30d.get("count", 0)
        },
        "current_month": {
            "amount": flt(current_month.get("amount")),
            "target": get_sales_target(salesman_user, frappe.utils.today()[:7])
        },
        "ytd": get_ytd_sales(salesman_user, conditions)
    }

def get_order_metrics(salesman_user, territories):
    """Get order-related metrics"""
    # Build conditions
    conditions = ["docstatus = 1", "owner = %s"]
    values = [salesman_user]
    
    if territories:
        customers = frappe.get_all("Customer", 
            filters={"territory": ["in", territories], "disabled": 0},
            pluck="name"
        )
        if customers:
            placeholders = ", ".join(["%s"] * len(customers))
            conditions.append(f"customer IN ({placeholders})")
            values.extend(customers)
    
    # Get status summary
    status_summary = frappe.db.sql(f"""
        SELECT 
            status,
            COUNT(*) as count,
            SUM(grand_total) as amount
        FROM `tabSales Order`
        WHERE {' AND '.join(conditions)}
        GROUP BY status
    """, values, as_dict=1)
    
    # Get recent orders
    recent_orders = frappe.db.sql(f"""
        SELECT 
            name,
            customer,
            grand_total,
            status,
            transaction_date
        FROM `tabSales Order`
        WHERE {' AND '.join(conditions)}
        ORDER BY transaction_date DESC
        LIMIT 5
    """, values, as_dict=1)
    
    return {
        "status_summary": status_summary,
        "recent_orders": recent_orders
    }

def get_collection_metrics(salesman_user, territories):
    """Get collection and outstanding metrics"""
    # Build conditions for Sales Invoice
    conditions = [
        "docstatus = 1",
        "owner = %s",
        "outstanding_amount > 0"
    ]
    values = [salesman_user]
    
    if territories:
        customers = frappe.get_all("Customer", 
            filters={"territory": ["in", territories], "disabled": 0},
            pluck="name"
        )
        if customers:
            placeholders = ", ".join(["%s"] * len(customers))
            conditions.append(f"customer IN ({placeholders})")
            values.extend(customers)
    
    # Get outstanding amounts
    outstanding = frappe.db.sql(f"""
        SELECT 
            SUM(outstanding_amount) as total_outstanding,
            COUNT(*) as count
        FROM `tabSales Invoice`
        WHERE {' AND '.join(conditions)}
    """, values, as_dict=1)
    
    # Get recent payments
    payment_conditions = ["docstatus = 1", "owner = %s"]
    payment_values = [salesman_user]
    
    if territories and 'customers' in locals() and customers:
        payment_conditions.append(f"party IN ({placeholders})")
        payment_values.extend(customers)
    
    recent_payments = frappe.db.sql(f"""
        SELECT 
            pe.name,
            pe.party as customer,
            pe.posting_date,
            pe.paid_amount
        FROM `tabPayment Entry` pe
        WHERE pe.payment_type = 'Receive'
        AND pe.party_type = 'Customer'
        AND {' AND '.join(payment_conditions)}
        ORDER BY pe.posting_date DESC
        LIMIT 5
    """, payment_values, as_dict=1)
    
    return {
        "outstanding": outstanding[0] if outstanding else {"total_outstanding": 0, "count": 0},
        "recent_payments": recent_payments
    }

def get_stock_metrics(warehouses):
    """Get stock-related metrics"""
    if not warehouses:
        return {}
    
    # Convert warehouses list to tuple for SQL IN clause
    placeholders = ", ".join(["%s"] * len(warehouses))
    
    stock_data = frappe.db.sql(f"""
        SELECT 
            COUNT(DISTINCT b.item_code) as total_items,
            SUM(b.actual_qty * b.valuation_rate) as stock_value,
            SUM(CASE WHEN b.actual_qty <= 0 THEN 1 ELSE 0 END) as out_of_stock,
            SUM(CASE WHEN b.actual_qty > 0 AND b.actual_qty <= i.safety_stock THEN 1 ELSE 0 END) as low_stock
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON b.item_code = i.name
        WHERE b.warehouse IN ({placeholders})
    """, tuple(warehouses), as_dict=1)
    
    return stock_data[0] if stock_data else {
        "total_items": 0,
        "stock_value": 0,
        "out_of_stock": 0,
        "low_stock": 0
    }

def get_customer_metrics(salesman_user, territories):
    """Get customer-related metrics"""
    filters = {"disabled": 0}
    if territories:
        filters["territory"] = ["in", territories]
    
    total_customers = frappe.db.count("Customer", filters)
    
    # New customers this month
    month_start = frappe.utils.get_first_day(frappe.utils.today())
    new_this_month = frappe.db.count("Customer", {
        **filters,
        "creation": [">=", month_start]
    })
    
    return {
        "total_customers": total_customers,
        "new_this_month": new_this_month,
        "top_customers": get_top_customers(salesman_user, territories, 5)
    }

# Helper functions
def get_ytd_sales(salesman_user, conditions):
    """Get year-to-date sales"""
    # Convert conditions to SQL WHERE clause
    where_parts = []
    values = []
    
    # Add YTD condition
    where_parts.append("`posting_date` >= %s")
    values.append(f"{frappe.utils.nowdate()[:4]}-01-01")
    
    # Process other conditions
    for field, operator, value in conditions:
        if operator.lower() == 'in' and isinstance(value, (list, tuple)):
            placeholders = ", ".join(["%s"] * len(value))
            where_parts.append(f"`{field}` IN ({placeholders})")
            values.extend(value)
        else:
            where_parts.append(f"`{field}` {operator} %s")
            values.append(value)
    
    where_clause = " AND ".join(where_parts)
    
    query = f"""
        SELECT 
            COALESCE(SUM(grand_total), 0) as amount, 
            COUNT(*) as count
        FROM `tabSales Invoice`
        WHERE {where_clause}
    """
    
    try:
        ytd = frappe.db.sql(query, values, as_dict=1)
        ytd = ytd[0] if ytd else {"amount": 0, "count": 0}
    except Exception as e:
        frappe.log_error(f"Error in get_ytd_sales: {str(e)}")
        return {"amount": 0, "count": 0}
    
    return {
        "amount": flt(ytd.get("amount")),
        "invoices": ytd.get("count", 0)
    }

def get_recent_orders(salesman_user, limit=5):
    """Get recent sales orders"""
    return frappe.db.get_all("Sales Order",
        filters={"docstatus": 1, "owner": salesman_user},
        fields=["name", "customer", "grand_total", "status", "transaction_date"],
        order_by="transaction_date desc",
        limit=limit,
        as_dict=1
    )

def get_top_customers(salesman_user, territories, limit=5):
    """Get top customers by sales amount"""
    conditions = [
        "docstatus = 1",
        "owner = %s"
    ]
    values = [salesman_user]
    
    if territories:
        customers = frappe.get_all("Customer", 
            filters={"territory": ["in", territories], "disabled": 0},
            pluck="name"
        )
        if customers:
            placeholders = ", ".join(["%s"] * len(customers))
            conditions.append(f"customer IN ({placeholders})")
            values.extend(customers)
    
    top_customers = frappe.db.sql(f"""
        SELECT 
            customer as name,
            customer_name,
            SUM(grand_total) as total_sales,
            COUNT(*) as invoice_count
        FROM `tabSales Invoice`
        WHERE {' AND '.join(conditions)}
        GROUP BY customer, customer_name
        ORDER BY total_sales DESC
        LIMIT %s
    """, values + [limit], as_dict=1)
    
    return top_customers

def get_sales_target(salesman_user, period):
    """Get sales target for the period"""
    # First check what fields exist in the Sales Person table
    target_fields = frappe.db.sql("""
        SHOW COLUMNS FROM `tabSales Person` 
        WHERE Field LIKE '%target%' 
        OR Field LIKE '%monthly%'
    """, as_dict=1)
    
    # Default to 0 if no target field is found
    if not target_fields:
        return 0
        
    # Use the first matching field (you might want to adjust this logic)
    target_field = target_fields[0]['Field']
    
    target = frappe.db.sql(f"""
        SELECT `{target_field}` as monthly_target
        FROM `tabSales Person`
        WHERE user_id = %s
    """, salesman_user, as_dict=1)
    
    return flt(target[0].get("monthly_target")) if target and target[0].get("monthly_target") else 0

def flt(value, precision=2):
    """Helper to format float values"""
    return float(round(float(value or 0), precision))