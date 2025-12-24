frappe.query_reports["Salesman Visit Summary"] = {
  "filters": [
    {
      "fieldname": "from_date",
      "label": __("From Date"),
      "fieldtype": "Date",
      "default": frappe.datetime.add_days(frappe.datetime.get_today(), -7),
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
    {
      "fieldname": "poor_accuracy_threshold",
      "label": __("Poor Accuracy Threshold (m)"),
      "fieldtype": "Float",
      "default": 50,
      "description": __("Count visits as Poor when accuracy > threshold.")
    }
  ]
};
