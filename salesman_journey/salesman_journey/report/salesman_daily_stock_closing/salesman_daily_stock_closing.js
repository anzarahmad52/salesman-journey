frappe.query_reports["Salesman Daily Stock Closing"] = {
  "filters": [
    {
      fieldname: "date_range",
      label: __("Date Range"),
      fieldtype: "DateRange",
      default: [frappe.datetime.month_start(), frappe.datetime.get_today()],
      reqd: 1
    },
    // Optional single-date fallback (used only if Date Range is empty)
    // {
    //   fieldname: "posting_date",
    //   label: __("Date (fallback)"),
    //   fieldtype: "Date",
    //   default: "",
    //   reqd: 0
    // },
    {
      fieldname: "warehouse",
      label: __("Warehouse"),
      fieldtype: "Link",
      options: "Warehouse",
      reqd: 1
    },
    // NEW: Item-wise search
    {
      fieldname: "item_code",
      label: __("Item"),
      fieldtype: "Link",
      options: "Item",
      reqd: 0
    },
    {
      fieldname: "salesman_user",
      label: __("Salesman (User)"),
      fieldtype: "Link",
      options: "User",
      // Filter to users who have the "Sales User" role
      get_query: () => ({
        query: "salesman_journey.salesman_journey.report.salesman_daily_stock_closing.salesman_daily_stock_closing.sales_user_query"
      })
    },
    {
      fieldname: "include_vouchers",
      label: __("Include voucher-wise sales"),
      fieldtype: "Check",
      default: 1
    },
    {
      fieldname: "only_movement",
      label: __("Show only items with movement"),
      fieldtype: "Check",
      default: 0
    }
  ]
};
