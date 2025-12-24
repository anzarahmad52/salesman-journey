import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class JourneyPlanTemplate(Document):
    def validate(self):
        self._set_defaults()
        self._validate_cycle_weeks()
        self._validate_week_no_range()
        self._validate_no_customer_repeat_same_day_across_weeks()
        self._set_auto_status()

    def on_update(self):
        # Keep status correct even if user edits dates / disables template
        # Avoid recursion: only update when needed
        self._set_auto_status(save_if_changed=True)

    def _set_defaults(self):
        # Force Weekly (feature is weekly rotation)
        self.frequency = "Weekly"

        if not getattr(self, "cycle_weeks", None):
            self.cycle_weeks = 1

        if not getattr(self, "cycle_anchor_date", None) and getattr(self, "start_date", None):
            self.cycle_anchor_date = self.start_date

    def _validate_cycle_weeks(self):
        if int(self.cycle_weeks or 0) <= 0:
            frappe.throw("Number of Weeks (cycle_weeks) must be at least 1.")

    def _validate_week_no_range(self):
        cw = int(self.cycle_weeks or 1)

        for i, row in enumerate(self.route_days or [], start=1):
            if not getattr(row, "week_no", None):
                frappe.throw(f"Row #{i}: Week No is required.")

            try:
                wn = int(row.week_no)
            except Exception:
                frappe.throw(f"Row #{i}: Week No must be an integer.")

            if wn < 1 or wn > cw:
                frappe.throw(f"Row #{i}: Week No ({wn}) must be between 1 and {cw}.")

    def _validate_no_customer_repeat_same_day_across_weeks(self):
        # key: (day_of_week, customer) -> first_week_no
        seen = {}

        for i, row in enumerate(self.route_days or [], start=1):
            day = (row.day_of_week or "").strip()
            cust = (row.customer or "").strip()

            if not day or not cust:
                continue

            wn = int(row.week_no or 0)
            key = (day, cust)

            if key in seen:
                prev_week = seen[key]
                frappe.throw(
                    f"Row #{i}: Customer <b>{cust}</b> is duplicated on <b>{day}</b> "
                    f"across weeks (already exists in Week {prev_week}). "
                    f"Customer must not repeat within the selected cycle."
                )

            seen[key] = wn

    def _set_auto_status(self, save_if_changed=False):
        """
        Auto-maintain status:
        - Inactive if is_disabled=1
        - Draft if missing required dates
        - Scheduled if start_date > today
        - Expired if end_date < today
        - Active otherwise (today in range)
        """
        old = self.status

        if int(getattr(self, "is_disabled", 0) or 0) == 1:
            self.status = "Inactive"
        else:
            if not self.start_date:
                self.status = "Draft"
            else:
                today = getdate(nowdate())
                sd = getdate(self.start_date)
                ed = getdate(self.end_date) if self.end_date else None

                if sd > today:
                    self.status = "Scheduled"
                elif ed and ed < today:
                    self.status = "Expired"
                else:
                    self.status = "Active"

        if save_if_changed and self.status != old:
            # update without triggering validate loop
            self.db_set("status", self.status, update_modified=False)

    def get_week_no_for_date(self, for_date):
        """
        week_no = ((weeks_since_anchor % cycle_weeks) + 1)
        """
        cw = int(self.cycle_weeks or 1)
        anchor = getdate(self.cycle_anchor_date or self.start_date)
        d = getdate(for_date)

        if not anchor:
            return 1

        days = (d - anchor).days
        weeks = days // 7
        return (weeks % cw) + 1
