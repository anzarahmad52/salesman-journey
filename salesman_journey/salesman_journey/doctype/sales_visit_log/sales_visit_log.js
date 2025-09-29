frappe.ui.form.on('Sales Visit Log', {
    refresh: function (frm) {
      // if (!frm.doc.__islocal && !frm.doc.check_in_time) {
        if (!frm.doc.check_in_time) {
        frm.add_custom_button(__('Check-In'), async function () {
          if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(async function (position) {
              const currentLat = position.coords.latitude;
              const currentLon = position.coords.longitude;
  

              const customer = frm.doc.customer;
              if (!customer) {
                frappe.msgprint(__('Please select a customer.'));
                return;
              }
  
              const customerDoc = await frappe.db.get_doc('Customer', customer);
              const customerLat = parseFloat(customerDoc.latitude || 0);
              const customerLon = parseFloat(customerDoc.longitude || 0);
  
              if (!customerLat || !customerLon) {
                frappe.msgprint(__('Customer does not have location data.'));
                return;
              }
  
              const distance = getDistanceFromLatLonInM(currentLat, currentLon, customerLat, customerLon);
  
              if (distance > 100) {
                frappe.msgprint(__('You are too far from the customer location (Distance: ' + distance.toFixed(2) + ' meters).'));
                return;
              }
  
              const now = frappe.datetime.now_datetime();
              frm.set_value('check_in_time', now);
              frm.set_value('location', currentLat + ', ' + currentLon);
              frm.save();
              frappe.msgprint(__('Check-in successful!'));
  
            }, function () {
              frappe.msgprint(__('Geolocation access denied.'));
            });
          } else {
            frappe.msgprint(__('Geolocation is not supported by this browser.'));
          }
        });
      }
  
      if (frm.doc.check_in_time && !frm.doc.check_out_time) {
        frm.add_custom_button(__('Check-Out'), function () {
          const now = frappe.datetime.now_datetime();
          frm.set_value('check_out_time', now);
          frm.save();
          frappe.msgprint(__('Check-out successful!'));
        });
      }
    }
  });
  
  // Haversine formula to calculate distance between two lat/lon points
  function getDistanceFromLatLonInM(lat1, lon1, lat2, lon2) {
    function deg2rad(deg) {
      return deg * (Math.PI / 180);
    }
  
    const R = 6371e3; // Radius of Earth in meters
    const dLat = deg2rad(lat2 - lat1);
    const dLon = deg2rad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const d = R * c; // Distance in meters
    return d;
  }
