// /home/frappe/frappe-bench/apps/salesman_journey/salesman_journey/salesman_journey/report/customer_coverage/customer_coverage.js

frappe.query_reports["Customer Coverage"] = {
  filters: [
    {
      fieldname: "date_from",
      label: __("From Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.month_start()
    },
    {
      fieldname: "date_to",
      label: __("To Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today()
    },
    {
      fieldname: "salesman",
      label: __("Salesman"),
      fieldtype: "Link",
      options: "User"
    },
    {
      fieldname: "territory",
      label: __("Territory"),
      fieldtype: "Link",
      options: "Territory"
    },
    {
      fieldname: "customer_group",
      label: __("Customer Group"),
      fieldtype: "Link",
      options: "Customer Group"
    },
    {
      fieldname: "show_only_not_visited",
      label: __("Show Only Not Visited"),
      fieldtype: "Check",
      default: 0
    },
    {
      fieldname: "group_by",
      label: __("Chart Group By"),
      fieldtype: "Select",
      options: ["Territory", "Salesman"],
      default: "Territory"
    }
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    // Colorize "Visited?" column
    if (column.fieldname === "visited" && data) {
      const isVisited = !!data.visited;

      // show Yes/No text with color (instead of checkbox only)
      const text = isVisited ? __("Visited") : __("Not Visited");
      const color = isVisited ? "green" : "red";

      return `<span style="font-weight:600;color:${color};">${text}</span>`;
    }

    // Optionally colorize visit_count if zero
    if (column.fieldname === "visit_count" && data) {
      const v = Number(data.visit_count || 0);
      if (v === 0) {
        return `<span style="color:#999;">${value}</span>`;
      }
    }

    return value;
  }
};
