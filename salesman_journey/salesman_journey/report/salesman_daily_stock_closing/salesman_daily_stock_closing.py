# Salesman Journey - Script Report: Salesman Daily Stock Closing
# All-in-one: report logic + whitelisted sales_user_query for Link filter
import frappe
from frappe.utils import getdate, add_days

def execute(filters=None):
    filters = frappe._dict(filters or {})
    _validate_filters(filters)

    # Date handling: inclusive end (use exclusive upper bound for SQL)
    date_from, date_to = resolve_date_range(filters)
    day_start = getdate(date_from)
    day_end = add_days(getdate(date_to), 1)  # exclusive

    warehouse = filters.warehouse
    item_code = (filters.get("item_code") or "").strip()
    salesman_user = (filters.salesman_user or "").strip()
    include_vouchers = int(filters.get("include_vouchers") or 0)
    only_movement = int(filters.get("only_movement") or 0)

    sales_persons = resolve_sales_persons_for_user(salesman_user) if salesman_user else []

    # Opening qty up to start of range
    opening = get_opening_qty_by_item(warehouse, day_start, item_code=item_code)

    # Movement within [day_start, day_end)
    in_out = get_in_out_qty_by_item(warehouse, day_start, day_end, item_code=item_code)

    # Opening valuation rate per item (last known rate before range start)
    opening_rates = get_opening_valuation_rate_by_item(warehouse, day_start, item_code=item_code)

    rows = []
    all_items = set(opening.keys()) | set(in_out.keys())
    for item in sorted(all_items):
        op = float(opening.get(item, 0.0))
        in_qty = float(in_out.get(item, {}).get("in_qty", 0.0))
        out_qty = float(in_out.get(item, {}).get("out_qty", 0.0))
        closing = op + in_qty - out_qty

        if only_movement and not (in_qty or out_qty):
            continue

        rate = float(opening_rates.get(item, 0.0))
        opening_value = op * rate

        item_name, stock_uom = get_item_meta(item)
        rows.append({
            "section": "SUMMARY",
            "item_code": item,
            "item_name": item_name,
            "uom": stock_uom,
            "voucher_no": "",
            "customer": "",
            "opening_qty": op,
            "opening_value": opening_value,   # NEW
            "in_qty": in_qty,
            "out_qty": out_qty,
            "closing_qty": closing,
            "sales_amount": 0.0
        })

    voucher_rows = []
    if include_vouchers:
        voucher_rows = get_voucher_wise_sales(
            warehouse=warehouse,
            day_start=day_start,
            day_end=day_end,
            sales_persons=sales_persons,
            salesman_user=salesman_user,
            item_code=item_code
        )
        rows.extend(voucher_rows)

    columns = get_columns(has_voucher_rows=bool(voucher_rows))
    return columns, rows


# ----------------------------
# Helpers & data access
# ----------------------------

def _validate_filters(f):
    if not f.get("warehouse"):
        frappe.throw("Please select Warehouse.")
    if not f.get("date_range") and not f.get("posting_date"):
        frappe.throw("Please select Date Range (or a single Date).")

def resolve_date_range(f):
    """Return (from_date, to_date) as YYYY-MM-DD strings."""
    if f.get("date_range"):
        dr = f.get("date_range")
        if isinstance(dr, (list, tuple)) and len(dr) == 2 and dr[0] and dr[1]:
            return str(getdate(dr[0])), str(getdate(dr[1]))
    if f.get("posting_date"):
        d = getdate(f.get("posting_date"))
        return str(d), str(d)
    today = getdate()
    return str(today), str(today)

def get_item_meta(item_code):
    rec = frappe.db.get_value("Item", item_code, ["item_name", "stock_uom"], as_dict=True)
    return (rec.item_name if rec else item_code, rec.stock_uom if rec else "")

def get_opening_qty_by_item(warehouse, before_date, item_code=None):
    """Sum actual_qty per item for the warehouse strictly before before_date (00:00:00)."""
    cond = " AND item_code = %(item)s " if item_code else ""
    sql = f"""
        SELECT item_code, COALESCE(SUM(actual_qty), 0) AS opening_qty
        FROM `tabStock Ledger Entry`
        WHERE warehouse = %(wh)s
          AND posting_date < %(before_date)s
          {cond}
        GROUP BY item_code
    """
    params = {"wh": warehouse, "before_date": str(before_date)}
    if item_code:
        params["item"] = item_code
    data = frappe.db.sql(sql, params, as_dict=True)
    return {d.item_code: float(d.opening_qty or 0) for d in data}

def get_in_out_qty_by_item(warehouse, start_date, end_date, item_code=None):
    """Sum IN/OUT actual_qty within [start_date, end_date) per item for the warehouse."""
    cond = " AND item_code = %(item)s " if item_code else ""
    sql = f"""
        SELECT
            item_code,
            SUM(CASE WHEN actual_qty > 0 THEN actual_qty ELSE 0 END) AS in_qty,
            SUM(CASE WHEN actual_qty < 0 THEN -actual_qty ELSE 0 END) AS out_qty
        FROM `tabStock Ledger Entry`
        WHERE warehouse = %(wh)s
          AND posting_date >= %(start)s
          AND posting_date < %(end)s
          {cond}
        GROUP BY item_code
    """
    params = {"wh": warehouse, "start": str(start_date), "end": str(end_date)}
    if item_code:
        params["item"] = item_code
    data = frappe.db.sql(sql, params, as_dict=True)
    return {d.item_code: {"in_qty": float(d.in_qty or 0), "out_qty": float(d.out_qty or 0)} for d in data}

def get_opening_valuation_rate_by_item(warehouse, before_date, item_code=None):
    """
    Get the **last known valuation_rate** per item in this warehouse BEFORE `before_date`.
    Used to compute Opening Value = Opening Qty * valuation_rate.
    """
    cond = " AND s0.item_code = %(item)s " if item_code else ""
    # Use (posting_date, posting_time) to find the latest row before the boundary
    sql = f"""
        SELECT s1.item_code, COALESCE(s1.valuation_rate, 0) AS valuation_rate
        FROM `tabStock Ledger Entry` s1
        INNER JOIN (
            SELECT s0.item_code,
                   MAX(CONCAT(s0.posting_date, ' ', IFNULL(s0.posting_time, '00:00:00'))) AS max_ts
            FROM `tabStock Ledger Entry` s0
            WHERE s0.warehouse = %(wh)s
              AND s0.posting_date < %(before_date)s
              {cond}
            GROUP BY s0.item_code
        ) t ON t.item_code = s1.item_code
           AND CONCAT(s1.posting_date, ' ', IFNULL(s1.posting_time, '00:00:00')) = t.max_ts
        WHERE s1.warehouse = %(wh)s
    """
    params = {"wh": warehouse, "before_date": str(before_date)}
    if item_code:
        params["item"] = item_code
    data = frappe.db.sql(sql, params, as_dict=True)
    return {d.item_code: float(d.valuation_rate or 0) for d in data}

def resolve_sales_persons_for_user(user_id):
    """Map a User -> Sales Person(s) using Employee link(s) if present."""
    if not user_id:
        return []
    sales_persons = []
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, ["name"], as_dict=True)
    if not emp:
        return sales_persons
    sp = frappe.db.get_value("Employee", emp.name, "sales_person")
    if sp:
        sales_persons.append(sp)
    extra = frappe.db.get_all("Sales Person", {"employee": emp.name}, pluck="name")
    for s in extra:
        if s not in sales_persons:
            sales_persons.append(s)
    return sales_persons

# def resolve_sales_persons_for_user(user_id):
#     """Map a User -> Sales Person(s) using Employee link(s) if present."""
#     if not user_id:
#         return []

#     sales_persons = []

#     emp = frappe.db.get_value("Employee", {"user_id": user_id}, ["name"], as_dict=True)
#     if not emp:
#         return sales_persons

#     # Safe: only fetch sales_person if column exists
#     if frappe.db.has_column("Employee", "sales_person"):
#         sp = frappe.db.get_value("Employee", emp.name, "sales_person")
#         if sp:
#             sales_persons.append(sp)

#     # Extra link from Sales Person table
#     extra = frappe.db.get_all("Sales Person", {"employee": emp.name}, pluck="name")
#     for s in extra:
#         if s not in sales_persons:
#             sales_persons.append(s)

#     return sales_persons

def get_voucher_wise_sales(warehouse, day_start, day_end, sales_persons, salesman_user, item_code=None):
    """
    Submitted non-return Sales Invoices in date range for this warehouse.
    Warehouse condition: item.warehouse OR invoice.set_warehouse
    Salesman priority: Sales Team.sales_person -> si.owner -> none
    Optional item filter: sii.item_code
    """
    wh_filter = "(sii.warehouse = %(wh)s OR si.set_warehouse = %(wh)s)"
    date_filter = "si.posting_date >= %(start)s AND si.posting_date < %(end)s"
    item_filter = " AND sii.item_code = %(item)s " if item_code else ""
    base_where = f"si.docstatus = 1 AND si.is_return = 0 AND {date_filter} AND {wh_filter}{item_filter}"
    params = {"wh": warehouse, "start": str(day_start), "end": str(day_end)}
    if item_code:
        params["item"] = item_code

    salesman_filter = ""
    if sales_persons:
        salesman_filter = " AND st.sales_person IN %(sps)s "
        params["sps"] = tuple(sales_persons)
    elif salesman_user:
        salesman_filter = " AND si.owner = %(owner)s "
        params["owner"] = salesman_user

    sql = f"""
        SELECT
            sii.parent AS voucher_no,
            si.customer,
            sii.item_code,
            sii.item_name,
            sii.uom,
            (sii.qty) AS qty_out,
            COALESCE(sii.base_net_amount, sii.base_amount) AS amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabSales Team` st ON st.parent = si.name AND st.parenttype = 'Sales Invoice'
        WHERE {base_where}
        {salesman_filter}
        ORDER BY sii.parent ASC, sii.idx ASC
    """
    data = frappe.db.sql(sql, params, as_dict=True)
    return [{
        "section": "VOUCHER (SALES)",
        "item_code": d.item_code,
        "item_name": d.item_name,
        "uom": d.uom,
        "voucher_no": d.voucher_no,
        "customer": d.customer,
        "opening_qty": 0.0,
        "opening_value": 0.0,  # voucher rows don't contribute to opening value
        "in_qty": 0.0,
        "out_qty": float(d.qty_out or 0),
        "closing_qty": 0.0,
        "sales_amount": float(d.amount or 0)
    } for d in data]

def get_columns(has_voucher_rows=False):
    return [
        {"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 140},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 80},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Opening Qty", "fieldname": "opening_qty", "fieldtype": "Float", "precision": "2", "width": 110},
        {"label": "Opening Value (Base)", "fieldname": "opening_value", "fieldtype": "Currency", "width": 160},  # NEW
        {"label": "In Qty", "fieldname": "in_qty", "fieldtype": "Float", "precision": "2", "width": 100},
        {"label": "Out Qty", "fieldname": "out_qty", "fieldtype": "Float", "precision": "2", "width": 100},
        {"label": "Closing Qty", "fieldname": "closing_qty", "fieldtype": "Float", "precision": "2", "width": 110},
        {"label": "Sales Amount (Base)", "fieldname": "sales_amount", "fieldtype": "Currency", "width": 160}
    ]


# ----------------------------
# Whitelisted link query in same module
# ----------------------------
@frappe.whitelist()
def sales_user_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Link field query for User filtered to those who have the 'Sales User' role.
    Ensures user is enabled. Supports name/full_name search.
    """
    txt = (txt or "").strip()
    like_txt = f"%{txt}%"
    return frappe.db.sql(
        """
        SELECT u.name, u.full_name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE
            hr.role = 'Sales User'
            AND u.enabled = 1
            AND (u.name LIKE %(like)s OR u.full_name LIKE %(like)s)
        GROUP BY u.name
        ORDER BY
            (CASE WHEN u.full_name LIKE %(starts)s THEN 0 ELSE 1 END),
            u.full_name ASC
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "like": like_txt,
            "starts": f"{txt}%",
            "start": int(start or 0),
            "page_len": int(page_len or 20),
        },
    )
