frappe.query_reports["Salesman Visit Performance"] = {
  "filters": [
    {
      "fieldname": "view_mode",
      "label": __("View Mode"),
      "fieldtype": "Select",
      "options": "Detail\nSummary\nCustomer Summary",
      "default": "Summary",
      "reqd": 1
    },
    {
      "fieldname": "from_date",
      "label": __("From Date"),
      "fieldtype": "Date",
      "default": frappe.datetime.month_start(),
      "reqd": 1
    },
    {
      "fieldname": "to_date",
      "label": __("To Date"),
      "fieldtype": "Date",
      "default": frappe.datetime.get_today(),
      "reqd": 1
    },
    {
      "fieldname": "salesman",
      "label": __("Salesman"),
      "fieldtype": "Link",
      "options": "User"
    },
    {
      "fieldname": "journey_plan",
      "label": __("Journey Plan Template"),
      "fieldtype": "Link",
      "options": "Journey Plan Template"
    },

    // Detail + Customer Summary filter
    {
      "fieldname": "customer",
      "label": __("Customer"),
      "fieldtype": "Link",
      "options": "Customer",
      "depends_on": "eval:doc.view_mode=='Detail' || doc.view_mode=='Customer Summary'"
    },

    // Detail + Customer Summary
    {
      "fieldname": "only_completed",
      "label": __("Only Completed Visits"),
      "fieldtype": "Check",
      "default": 0,
      "depends_on": "eval:doc.view_mode=='Detail' || doc.view_mode=='Customer Summary'"
    },

    // Summary-only
    {
      "fieldname": "poor_accuracy_threshold",
      "label": __("Poor Accuracy Threshold (m)"),
      "fieldtype": "Float",
      "default": 50,
      "description": __("Used in Summary mode (count visits with accuracy > threshold)."),
      "depends_on": "eval:doc.view_mode=='Summary'"
    }
  ],

  onload: function(report) {
    report.page.add_inner_button(__('Open Detail (Selected Salesman)'), function() {
      const checked = report.datatable?.rowmanager?.getCheckedRows?.() || [];
      const row = checked[0];

      if (!row) {
        frappe.msgprint(__('Please select one row first (tick checkbox).'));
        return;
      }

      const salesmanColIndex = (report.columns || []).findIndex(c => c.fieldname === 'salesman');
      if (salesmanColIndex < 0) {
        frappe.msgprint(__('Salesman column not found.'));
        return;
      }

      const salesman = row[salesmanColIndex];
      if (!salesman) {
        frappe.msgprint(__('Salesman value not found in selected row.'));
        return;
      }

      const f = report.get_values() || {};

      frappe.set_route('query-report', 'Salesman Visit Performance', {
        view_mode: 'Detail',
        from_date: f.from_date,
        to_date: f.to_date,
        salesman: salesman,
        journey_plan: f.journey_plan || null
      });
    });
  }
};




// frappe.query_reports["Salesman Visit Performance"] = {
//   "filters": [
//     {
//       "fieldname": "view_mode",
//       "label": __("View Mode"),
//       "fieldtype": "Select",
//       "options": "Detail\nSummary\nCustomer Summary",
//       "default": "Summary",
//       "reqd": 1
//     },
//     {
//       "fieldname": "from_date",
//       "label": __("From Date"),
//       "fieldtype": "Date",
//       "default": frappe.datetime.month_start(),
//       "reqd": 1
//     },
//     {
//       "fieldname": "to_date",
//       "label": __("To Date"),
//       "fieldtype": "Date",
//       "default": frappe.datetime.get_today(),
//       "reqd": 1
//     },
//     {
//       "fieldname": "salesman",
//       "label": __("Salesman"),
//       "fieldtype": "Link",
//       "options": "User"
//     },
//     {
//       "fieldname": "journey_plan",
//       "label": __("Journey Plan Template"),
//       "fieldtype": "Link",
//       "options": "Journey Plan Template"
//     },

//     // Detail-only filters
//     {
//       "fieldname": "customer",
//       "label": __("Customer"),
//       "fieldtype": "Link",
//       "options": "Customer",
//       "depends_on": "eval:doc.view_mode=='Detail'"
//     },
//     {
//       "fieldname": "only_completed",
//       "label": __("Only Completed Visits"),
//       "fieldtype": "Check",
//       "default": 0,
//       "depends_on": "eval:doc.view_mode=='Detail'"
//     },

//     // Summary-only filter
//     {
//       "fieldname": "poor_accuracy_threshold",
//       "label": __("Poor Accuracy Threshold (m)"),
//       "fieldtype": "Float",
//       "default": 50,
//       "description": __("Used in Summary mode (count visits with accuracy > threshold)."),
//       "depends_on": "eval:doc.view_mode=='Summary'"
//     }
//   ]
// };





// frappe.query_reports["Salesman Visit Performance"] = {
//   "filters": [
//     {
//       "fieldname": "view_mode",
//       "label": __("View Mode"),
//       "fieldtype": "Select",
//       "options": "Detail\nSummary",
//       "default": "Summary",
//       "reqd": 1
//     },
//     {
//       "fieldname": "from_date",
//       "label": __("From Date"),
//       "fieldtype": "Date",
//       "default": frappe.datetime.month_start(),
//       "reqd": 1
//     },
//     {
//       "fieldname": "to_date",
//       "label": __("To Date"),
//       "fieldtype": "Date",
//       "default": frappe.datetime.get_today(),
//       "reqd": 1
//     },
//     {
//       "fieldname": "salesman",
//       "label": __("Salesman"),
//       "fieldtype": "Link",
//       "options": "User"
//     },
//     {
//       "fieldname": "journey_plan",
//       "label": __("Journey Plan Template"),
//       "fieldtype": "Link",
//       "options": "Journey Plan Template"
//     },

//     // Detail-only filters
//     {
//       "fieldname": "customer",
//       "label": __("Customer"),
//       "fieldtype": "Link",
//       "options": "Customer",
//       "depends_on": "eval:doc.view_mode=='Detail'"
//     },
//     {
//       "fieldname": "only_completed",
//       "label": __("Only Completed Visits"),
//       "fieldtype": "Check",
//       "default": 0,
//       "depends_on": "eval:doc.view_mode=='Detail'"
//     },

//     // Summary-only filter
//     {
//       "fieldname": "poor_accuracy_threshold",
//       "label": __("Poor Accuracy Threshold (m)"),
//       "fieldtype": "Float",
//       "default": 50,
//       "description": __("Used in Summary mode (count visits with accuracy > threshold)."),
//       "depends_on": "eval:doc.view_mode=='Summary'"
//     }
//   ],

//   onload: function(report) {
//     // Button appears mainly for Summary mode usage
//     report.page.add_inner_button(__('Open Detail (Selected Salesman)'), function() {
//       const checked = report.datatable?.rowmanager?.getCheckedRows?.() || [];
//       const row = checked[0];

//       if (!row) {
//         frappe.msgprint(__('Please select one row first (tick checkbox).'));
//         return;
//       }

//       // Find "salesman" column index safely
//       const salesmanColIndex = (report.columns || []).findIndex(c => c.fieldname === 'salesman');
//       if (salesmanColIndex < 0) {
//         frappe.msgprint(__('Salesman column not found.'));
//         return;
//       }

//       const salesman = row[salesmanColIndex];
//       if (!salesman) {
//         frappe.msgprint(__('Salesman value not found in selected row.'));
//         return;
//       }

//       const f = report.get_values() || {};

//       frappe.set_route('query-report', 'Salesman Visit Performance', {
//         view_mode: 'Detail',
//         from_date: f.from_date,
//         to_date: f.to_date,
//         salesman: salesman,
//         journey_plan: f.journey_plan || null
//       });
//     });
//   }
// };




// frappe.query_reports["Salesman Visit Performance"] = {
//   "filters": [
//     {
//       "fieldname": "view_mode",
//       "label": __("View Mode"),
//       "fieldtype": "Select",
//       "options": "Detail\nSummary",
//       "default": "Summary",
//       "reqd": 1
//     },
//     {
//       "fieldname": "from_date",
//       "label": __("From Date"),
//       "fieldtype": "Date",
//       "default": frappe.datetime.month_start(),
//       "reqd": 1
//     },
//     {
//       "fieldname": "to_date",
//       "label": __("To Date"),
//       "fieldtype": "Date",
//       "default": frappe.datetime.get_today(),
//       "reqd": 1
//     },
//     {
//       "fieldname": "salesman",
//       "label": __("Salesman"),
//       "fieldtype": "Link",
//       "options": "User"
//     },
//     {
//       "fieldname": "journey_plan",
//       "label": __("Journey Plan Template"),
//       "fieldtype": "Link",
//       "options": "Journey Plan Template"
//     },

//     // Detail-only filters
//     {
//       "fieldname": "customer",
//       "label": __("Customer"),
//       "fieldtype": "Link",
//       "options": "Customer",
//       "depends_on": "eval:doc.view_mode=='Detail'"
//     },
//     {
//       "fieldname": "only_completed",
//       "label": __("Only Completed Visits"),
//       "fieldtype": "Check",
//       "default": 0,
//       "depends_on": "eval:doc.view_mode=='Detail'"
//     },

//     // Summary-only filter
//     {
//       "fieldname": "poor_accuracy_threshold",
//       "label": __("Poor Accuracy Threshold (m)"),
//       "fieldtype": "Float",
//       "default": 50,
//       "description": __("Used in Summary mode (count visits with accuracy > threshold)."),
//       "depends_on": "eval:doc.view_mode=='Summary'"
//     }
//   ]
// };
