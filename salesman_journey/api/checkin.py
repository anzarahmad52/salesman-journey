# import frappe
# from frappe.utils import now_datetime
# from frappe import _

# @frappe.whitelist()
# def create_checkin_tracker(visit_log, lat, lon, customer):
#     if not visit_log or not customer:
#         frappe.throw(_("Visit Log and Customer are required"))

#     try:
#         frappe.log_error(f"[Check-In] Request: {visit_log} / {customer}", "Check-In Started")

#         # Fetch Sales Visit Log to inherit salesman and validate existence
#         doc = frappe.get_doc("Sales Visit Log", visit_log)

#         # Validate customer consistency
#         if doc.customer != customer:
#             frappe.throw(_("Customer mismatch with Visit Log"))

#         # Prevent duplicate check-in
#         existing = frappe.get_all("Check-in Tracker", filters={
#             "visit_log": visit_log
#         }, limit=1)
#         if existing:
#             frappe.throw(_("Check-in already done for this visit"))

#         # Create tracker
#         tracker = frappe.new_doc("Check-in Tracker")
#         tracker.salesman = doc.salesman
#         tracker.customer = customer
#         tracker.visit_log = visit_log
#         tracker.latitude = lat
#         tracker.longitude = lon
#         tracker.check_in_time = now_datetime()
#         tracker.notes = "Checked in via mobile app"
#         tracker.insert(ignore_permissions=True)

#         # ✅ Log success
#         frappe.log_error(f"[Check-In] Tracker Created: {tracker.name}", "Check-In Tracker Success")

#         return tracker.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-in Tracker Creation Failed")
#         frappe.throw(_("Unable to create check-in. Please contact support."))


# @frappe.whitelist()
# def create_checkout_tracker(visit_log):
#     if not visit_log:
#         frappe.throw(_("Visit Log is required"))

#     try:
#         frappe.log_error(f"[Check-Out] Request: {visit_log}", "Check-Out Started")

#         # Get latest Check-in Tracker entry for this visit
#         tracker = frappe.get_all(
#             "Check-in Tracker",
#             filters={"visit_log": visit_log},
#             fields=["name"],
#             order_by="creation desc",
#             limit=1
#         )

#         if not tracker:
#             frappe.throw(_("No existing check-in found for this visit."))

#         tracker_doc = frappe.get_doc("Check-in Tracker", tracker[0].name)

#         # Prevent duplicate check-out
#         if tracker_doc.check_out_time:
#             frappe.throw(_("Already checked out."))

#         # Set check-out
#         tracker_doc.check_out_time = now_datetime()
#         tracker_doc.notes += "\nChecked out via mobile app"
#         tracker_doc.save(ignore_permissions=True)

#         frappe.log_error(f"[Check-Out] Tracker Updated: {tracker_doc.name}", "Check-Out Success")

#         return tracker_doc.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-out Tracker Failed")
#         frappe.throw(_("Unable to check-out. Please contact support."))

# import frappe
# from frappe.utils import now_datetime
# from frappe import _

# @frappe.whitelist()
# def create_checkin_tracker(visit_log, lat, lon, customer):
#     if not visit_log or not customer:
#         frappe.throw(_("Visit Log and Customer are required"))

#     try:
#         frappe.log_error(f"[Check-In] Request: {visit_log} / {customer}", "Check-In Started")

#         doc = frappe.get_doc("Sales Visit Log", visit_log)

#         if doc.customer != customer:
#             frappe.throw(_("Customer mismatch with Visit Log"))

#         existing = frappe.get_all("Check-in Tracker", filters={"visit_log": visit_log}, limit=1)
#         if existing:
#             frappe.throw(_("Check-in already done for this visit"))

#         tracker = frappe.new_doc("Check-in Tracker")
#         tracker.salesman = doc.salesman
#         tracker.customer = customer
#         tracker.visit_log = visit_log
#         tracker.latitude = lat
#         tracker.longitude = lon
#         tracker.check_in_time = now_datetime()
#         tracker.notes = "Checked in via mobile app"
#         tracker.insert(ignore_permissions=True)

#         frappe.log_error(f"[Check-In] Tracker Created: {tracker.name}", "Check-In Tracker Success")
#         return tracker.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-in Tracker Creation Failed")
#         frappe.throw(_("Unable to create check-in. Please contact support."))


# @frappe.whitelist()
# def create_checkout_tracker(visit_log, next_visit_date=None, linked_order=None):
#     if not visit_log:
#         frappe.throw(_("Visit Log is required"))

#     try:
#         frappe.log_error(f"[Check-Out] Request: {visit_log}", "Check-Out Started")

#         tracker = frappe.get_all(
#             "Check-in Tracker",
#             filters={"visit_log": visit_log},
#             fields=["name"],
#             order_by="creation desc",
#             limit=1
#         )

#         if not tracker:
#             frappe.throw(_("No existing check-in found for this visit."))

#         tracker_doc = frappe.get_doc("Check-in Tracker", tracker[0].name)

#         if tracker_doc.check_out_time:
#             frappe.throw(_("Already checked out."))

#         tracker_doc.check_out_time = now_datetime()
#         tracker_doc.notes += "\nChecked out via mobile app"
#         tracker_doc.save(ignore_permissions=True)

#         # Update Visit Log
#         visit_doc = frappe.get_doc("Sales Visit Log", visit_log)

#         if next_visit_date:
#             visit_doc.next_visit_date = next_visit_date
#         if linked_order:
#             visit_doc.linked_order = linked_order

#         # Validate and set outcome
#         allowed_outcomes = ["Order", "No Order", "Complaint", "Info Only"]
#         if not visit_doc.outcome or visit_doc.outcome not in allowed_outcomes:
#             visit_doc.outcome = "No Order"  # Default fallback

#         visit_doc.save(ignore_permissions=True)

#         frappe.log_error(f"[Check-Out] Tracker Updated: {tracker_doc.name}", "Check-Out Success")
#         return tracker_doc.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-out Tracker Failed")
#         frappe.throw(_("Unable to check-out. Please contact support."))


# import frappe
# from frappe.utils import now_datetime
# from frappe import _

# @frappe.whitelist()
# def create_checkin_tracker(visit_log, lat, lon, customer):
#     if not visit_log or not customer:
#         frappe.throw(_("Visit Log and Customer are required"))

#     try:
#         frappe.log_error(f"[Check-In] Request: {visit_log} / {customer}", "Check-In Started")

#         doc = frappe.get_doc("Sales Visit Log", visit_log)

#         if doc.customer != customer:
#             frappe.throw(_("Customer mismatch with Visit Log"))

#         existing = frappe.get_all(
#             "Check-in Tracker",
#             filters={"visit_log": visit_log},
#             limit=1
#         )
#         if existing:
#             frappe.throw(_("Check-in already done for this visit"))

#         tracker = frappe.new_doc("Check-in Tracker")
#         tracker.salesman = doc.salesman
#         tracker.customer = customer
#         tracker.visit_log = visit_log
#         tracker.latitude = lat
#         tracker.longitude = lon
#         tracker.check_in_time = now_datetime()
#         tracker.status = "Check IN"
#         tracker.notes = "Checked in via mobile app"
#         tracker.insert(ignore_permissions=True)

#         frappe.log_error(f"[Check-In] Tracker Created: {tracker.name}", "Check-In Tracker Success")
#         return tracker.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-in Tracker Creation Failed")
#         frappe.throw(_("Unable to create check-in. Please contact support."))


# @frappe.whitelist()
# def create_checkout_tracker(visit_log, next_visit_date=None, linked_order=None):
#     if not visit_log:
#         frappe.throw(_("Visit Log is required"))

#     try:
#         frappe.log_error(f"[Check-Out] Request: {visit_log}", "Check-Out Started")

#         tracker = frappe.get_all(
#             "Check-in Tracker",
#             filters={"visit_log": visit_log},
#             fields=["name"],
#             order_by="creation desc",
#             limit=1
#         )

#         if not tracker:
#             frappe.throw(_("No existing check-in found for this visit."))

#         tracker_doc = frappe.get_doc("Check-in Tracker", tracker[0].name)

#         if tracker_doc.check_out_time:
#             frappe.throw(_("Already checked out."))

#         tracker_doc.check_out_time = now_datetime()
#         tracker_doc.status = "Check Out"
#         tracker_doc.notes += "\nChecked out via mobile app"
#         tracker_doc.save(ignore_permissions=True)
#         tracker_doc.submit()  # ✅ Submit so docstatus = 1

#         # Update Sales Visit Log
#         visit_doc = frappe.get_doc("Sales Visit Log", visit_log)

#         if next_visit_date:
#             visit_doc.next_visit_date = next_visit_date
#         if linked_order:
#             visit_doc.linked_order = linked_order

#         allowed_outcomes = ["Order", "No Order", "Complaint", "Info Only"]
#         if not visit_doc.outcome or visit_doc.outcome not in allowed_outcomes:
#             visit_doc.outcome = "No Order"

#         visit_doc.save(ignore_permissions=True)

#         frappe.log_error(f"[Check-Out] Tracker Submitted: {tracker_doc.name}", "Check-Out Success")
#         return tracker_doc.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-out Tracker Failed")
#         frappe.throw(_("Unable to check-out. Please contact support."))


# @frappe.whitelist()
# def get_checkin_status(visit_log):
#     tracker = frappe.get_all(
#         "Check-in Tracker",
#         filters={"visit_log": visit_log},
#         fields=["status", "docstatus"],
#         order_by="creation desc",
#         limit=1
#     )
#     if tracker:
#         return {
#             "status": tracker[0].status,
#             "docstatus": tracker[0].docstatus
#         }
#     return {"status": "", "docstatus": 0}
# import frappe
# from frappe.utils import now_datetime
# from frappe import _

# @frappe.whitelist()
# def create_checkin_tracker(visit_log, lat, lon, customer):
#     if not visit_log or not customer:
#         frappe.throw(_("Visit Log and Customer are required"))

#     try:
#         frappe.log_error(f"[Check-In] Request: {visit_log} / {customer}", "Check-In Started")

#         doc = frappe.get_doc("Sales Visit Log", visit_log)

#         if doc.customer != customer:
#             frappe.throw(_("Customer mismatch with Visit Log"))

#         existing = frappe.get_all(
#             "Check-in Tracker",
#             filters={"visit_log": visit_log},
#             limit=1
#         )
#         if existing:
#             frappe.throw(_("Check-in already done for this visit"))

#         tracker = frappe.new_doc("Check-in Tracker")
#         tracker.salesman = doc.salesman
#         tracker.customer = customer
#         tracker.visit_log = visit_log
#         tracker.latitude = lat
#         tracker.longitude = lon
#         tracker.check_in_time = now_datetime()
#         tracker.status = "Check IN"
#         tracker.notes = "Checked in via mobile app"
#         tracker.insert(ignore_permissions=True)

#         frappe.log_error(f"[Check-In] Tracker Created: {tracker.name}", "Check-In Tracker Success")
#         return tracker.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-in Tracker Creation Failed")
#         frappe.throw(_("Unable to create check-in. Please contact support."))


# @frappe.whitelist()
# def create_checkout_tracker(visit_log, next_visit_date=None, linked_order=None):
#     if not visit_log:
#         frappe.throw(_("Visit Log is required"))

#     try:
#         frappe.log_error(f"[Check-Out] Request: {visit_log}", "Check-Out Started")

#         tracker = frappe.get_all(
#             "Check-in Tracker",
#             filters={"visit_log": visit_log},
#             fields=["name"],
#             order_by="creation desc",
#             limit=1
#         )

#         if not tracker:
#             frappe.throw(_("No existing check-in found for this visit."))

#         tracker_doc = frappe.get_doc("Check-in Tracker", tracker[0].name)

#         if tracker_doc.check_out_time:
#             frappe.throw(_("Already checked out."))

#         tracker_doc.check_out_time = now_datetime()
#         tracker_doc.status = "Check Out"
#         tracker_doc.notes += "\nChecked out via mobile app"
#         tracker_doc.save(ignore_permissions=True)
#         tracker_doc.submit()

#         visit_doc = frappe.get_doc("Sales Visit Log", visit_log)

#         if next_visit_date:
#             visit_doc.next_visit_date = next_visit_date
#         if linked_order:
#             visit_doc.linked_order = linked_order

#         allowed_outcomes = ["Order", "No Order", "Complaint", "Info Only"]
#         if not visit_doc.outcome or visit_doc.outcome not in allowed_outcomes:
#             visit_doc.outcome = "No Order"

#         visit_doc.save(ignore_permissions=True)

#         frappe.log_error(f"[Check-Out] Tracker Submitted: {tracker_doc.name}", "Check-Out Success")
#         return tracker_doc.name

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Check-out Tracker Failed")
#         frappe.throw(_("Unable to check-out. Please contact support."))


# @frappe.whitelist()
# def get_checkin_status(visit_log):
#     """
#     Returns a string:
#     - "Check OUT" if last tracker submitted and status is Check Out
#     - "Check IN" if last tracker draft and status is Check IN
#     - "Not Checked In" if none found
#     """
#     tracker = frappe.get_all(
#         "Check-in Tracker",
#         filters={"visit_log": visit_log},
#         fields=["status", "docstatus"],
#         order_by="creation desc",
#         limit=1
#     )

#     if not tracker:
#         return "Not Checked In"

#     last = tracker[0]

#     if last["docstatus"] == 1 and last["status"] == "Check Out":
#         return "Check OUT"
#     elif last["status"] == "Check IN":
#         return "Check IN"
#     else:
#         return "Not Checked In"

# This Code working well 18-05-2024
import frappe
from frappe.utils import now_datetime
from frappe import _

@frappe.whitelist()
def create_checkin_tracker(visit_log, lat, lon, customer):
    if not visit_log or not customer:
        frappe.throw(_("Visit Log and Customer are required"))

    try:
        frappe.log_error(f"[Check-In] Request: {visit_log} / {customer}", "Check-In Started")

        doc = frappe.get_doc("Sales Visit Log", visit_log)

        if doc.customer != customer:
            frappe.throw(_("Customer mismatch with Visit Log"))

        existing = frappe.get_all(
            "Check-in Tracker",
            filters={"visit_log": visit_log},
            limit=1
        )
        if existing:
            frappe.throw(_("Check-in already done for this visit"))

        tracker = frappe.new_doc("Check-in Tracker")
        tracker.salesman = doc.salesman
        tracker.customer = customer
        tracker.visit_log = visit_log
        tracker.latitude = lat
        tracker.longitude = lon
        tracker.check_in_time = now_datetime()
        tracker.status = "Check IN"
        tracker.notes = "Checked in via mobile app"
        tracker.insert(ignore_permissions=True)

        visit_doc = frappe.get_doc("Sales Visit Log", visit_log)
        visit_doc.check_in_time = now_datetime()
        visit_doc.location = "{latitude}, {longitude}".format(latitude=lat, longitude=lon)
        # Save the document
        visit_doc.save(ignore_permissions=True)

        frappe.log_error(f"[Check-In] Tracker Created: {tracker.name}", "Check-In Tracker Success")
        return tracker.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Check-in Tracker Creation Failed")
        frappe.throw(_("Unable to create check-in. Please contact support."))

@frappe.whitelist()
def create_checkout_tracker(visit_log, next_visit_date=None, linked_order=None):
    if not visit_log:
        frappe.throw(_("Visit Log is required"))

    try:
        frappe.log_error(f"[Check-Out] Request: {visit_log}", "Check-Out Started")

        tracker = frappe.get_all(
            "Check-in Tracker",
            filters={"visit_log": visit_log},
            fields=["name"],
            order_by="creation desc",
            limit=1
        )

        if not tracker:
            frappe.throw(_("No existing check-in found for this visit."))

        tracker_doc = frappe.get_doc("Check-in Tracker", tracker[0].name)

        if tracker_doc.check_out_time:
            frappe.throw(_("Already checked out."))

        tracker_doc.check_out_time = now_datetime()
        tracker_doc.status = "Check Out"
        tracker_doc.notes += "\nChecked out via mobile app"
        tracker_doc.save(ignore_permissions=True)
        tracker_doc.submit()

        visit_doc = frappe.get_doc("Sales Visit Log", visit_log)

        if next_visit_date:
            visit_doc.next_visit_date = next_visit_date
        if linked_order:
            visit_doc.linked_order = linked_order

        allowed_outcomes = ["Order", "No Order", "Complaint", "Info Only"]
        if not visit_doc.outcome or visit_doc.outcome not in allowed_outcomes:
            visit_doc.outcome = "No Order"

        visit_doc.check_out_time = now_datetime()
        visit_doc.save(ignore_permissions=True)

        frappe.log_error(f"[Check-Out] Tracker Submitted: {tracker_doc.name}", "Check-Out Success")
        return tracker_doc.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Check-out Tracker Failed")
        frappe.throw(_("Unable to check-out. Please contact support."))

@frappe.whitelist()
def get_checkin_status(visit_log):
    """
    Returns a string:
    - "Check OUT" if last tracker submitted and status is Check Out
    - "Check IN" if last tracker draft and status is Check IN
    - "Not Checked In" if none found
    """
    tracker = frappe.get_all(
        "Check-in Tracker",
        filters={"visit_log": visit_log},
        fields=["status", "docstatus"],
        order_by="creation desc",
        limit=1
    )

    if not tracker:
        return "Not Checked In"

    last = tracker[0]

    if last["docstatus"] == 1 and last["status"] == "Check Out":
        return "Check OUT"
    elif last["status"] == "Check IN":
        return "Check IN"
    else:
        return "Not Checked In"


@frappe.whitelist()
def update_visit_remarks(visit_log, remarks, outcome=None):
    """
    Update the remarks and/or outcome field of a Sales Visit Log
    
    Args:
        visit_log (str): Name of the Sales Visit Log document
        remarks (str): New remarks to be added
        outcome (str, optional): New outcome value (Order/No Order/Complaint/Info Only)
        
    Returns:
        dict: Status and message
    """
    if not visit_log:
        frappe.throw(_("Visit Log is required"))
        
    if not remarks or not remarks.strip():
        frappe.throw(_("Remarks cannot be empty"))
    
    try:
        # Get the visit log document
        visit_doc = frappe.get_doc("Sales Visit Log", visit_log)
        
        # Add timestamp and new line if there are existing remarks
        timestamp = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")
        if visit_doc.remarks:
            visit_doc.remarks = f"{visit_doc.remarks}\n[{timestamp}] {remarks}"
        else:
            visit_doc.remarks = f"[{timestamp}] {remarks}"
        
        # Update outcome if provided
        if outcome:
            allowed_outcomes = ["Order", "No Order", "Complaint", "Info Only"]
            if outcome in allowed_outcomes:
                visit_doc.outcome = outcome
            else:
                frappe.throw(_(f"Invalid outcome. Must be one of: {', '.join(allowed_outcomes)}"))
        
        # Save the document
        visit_doc.save(ignore_permissions=True)
        
        return {
            "status": "success",
            "message": "Visit log updated successfully"
        }
        
    except frappe.DoesNotExistError:
        frappe.throw(_(f"Sales Visit Log {visit_log} does not exist"))
    except Exception as e:
        frappe.log_error(f"Error updating visit log {visit_log}: {str(e)}")
        frappe.throw(_("Failed to update visit log. Please try again or contact support."))


@frappe.whitelist()
def get_visit_log_details(visit_log_name):
    """
    Get details of a Sales Visit Log
    
    Args:
        visit_log_name (str): Name of the Sales Visit Log document
        
    Returns:
        dict: Dictionary containing all the details of the Sales Visit Log
    """
    if not visit_log_name:
        frappe.throw(_("Visit Log Name is required"))
    
    try:
        # Get the visit log document
        visit_log = frappe.get_doc("Sales Visit Log", visit_log_name)
        
        # Prepare the response with all fields
        visit_details = {
            'name': visit_log.name,
            'salesman': visit_log.salesman,
            'customer': visit_log.customer,
            'customer_name': frappe.db.get_value('Customer', visit_log.customer, 'customer_name') if visit_log.customer else None,
            'journey_plan': visit_log.journey_plan,
            'visit_date': visit_log.visit_date,
            'check_in_time': visit_log.check_in_time,
            'check_out_time': visit_log.check_out_time,
            'location': visit_log.location,
            'remarks': visit_log.remarks,
            'outcome': visit_log.outcome,
            'next_visit_date': visit_log.next_visit_date,
            'linked_order': visit_log.linked_order,
            'status': 'Checked In' if visit_log.check_in_time and not visit_log.check_out_time 
                     else 'Checked Out' if visit_log.check_out_time 
                     else 'Not Checked In',
            'duration': calculate_visit_duration(visit_log.check_in_time, visit_log.check_out_time) 
                       if visit_log.check_in_time and visit_log.check_out_time 
                       else None
        }
        
        return {
            'status': 'success',
            'data': visit_details
        }
        
    except frappe.DoesNotExistError:
        frappe.throw(_(f"Sales Visit Log '{visit_log_name}' does not exist"))
    except Exception as e:
        frappe.log_error(title=_("Error fetching Visit Log details"), message=frappe.get_traceback())
        frappe.throw(_(f"Error fetching Visit Log details: {str(e)}"))

def calculate_visit_duration(check_in_time, check_out_time):
    """
    Calculate the duration between check-in and check-out times
    
    Args:
        check_in_time (str): Check-in datetime string
        check_out_time (str): Check-out datetime string
        
    Returns:
        str: Formatted duration string (e.g., "2h 30m")
    """
    if not all([check_in_time, check_out_time]):
        return None
        
    from frappe.utils import get_datetime
    
    check_in = get_datetime(check_in_time)
    check_out = get_datetime(check_out_time)
    
    if check_out < check_in:
        return "Invalid duration"
        
    duration = check_out - check_in
    total_seconds = int(duration.total_seconds())
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"