frappe.query_reports["Daily Visit Detail"] = {
  filters: [
    {
      fieldname: "date",
      label: __("Visit Date"),
      fieldtype: "Date",
      default: (() => {
        // ✅ Accept multiple route option keys
        // Visit Calendar may pass: from_date / to_date
        // Report expects: date
        const ro = frappe.route_options || {};
        return (
          ro.date ||
          ro.visit_date ||
          ro.from_date ||
          ro.to_date ||
          frappe.datetime.get_today()
        );
      })(),
      reqd: 1
    },
    {
      fieldname: "salesman",
      label: __("Salesman"),
      fieldtype: "Link",
      options: "User",
      default: (() => {
        const ro = frappe.route_options || {};
        return ro.salesman || "";
      })()
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
      default: (() => {
        const ro = frappe.route_options || {};
        return ro.customer || "";
      })()
    },
    {
      fieldname: "journey_plan",
      label: __("Journey Plan Template"),
      fieldtype: "Link",
      options: "Journey Plan Template",
      default: (() => {
        const ro = frappe.route_options || {};
        return ro.journey_plan || "";
      })()
    },
    {
      fieldname: "status",
      label: __("Status"),
      fieldtype: "Select",
      options: "\nPlanned Only\nCompleted Only\nMissed Only",
      default: (() => {
        const ro = frappe.route_options || {};
        return ro.status || "";
      })()
    },
    {
      fieldname: "accuracy_threshold",
      label: __("Poor Accuracy Threshold (m)"),
      fieldtype: "Float",
      default: (() => {
        const ro = frappe.route_options || {};
        // allow both names, just in case
        return (ro.accuracy_threshold != null ? ro.accuracy_threshold : (ro.poor_accuracy_threshold != null ? ro.poor_accuracy_threshold : 50));
      })()
    }
  ],

  onload: function(report) {
    // ✅ Ensure route options are applied, then clear them to avoid “sticky” filters later
    // Keep small delay so report can read them fully.
    setTimeout(() => {
      frappe.route_options = null;
    }, 500);
  }
};
