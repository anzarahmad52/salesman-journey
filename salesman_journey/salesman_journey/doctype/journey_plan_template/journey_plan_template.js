frappe.ui.form.on('Journey Plan Template', {
  refresh(frm) {
    // Force Weekly (your rotation is weekly)
    if (frm.doc.frequency && frm.doc.frequency !== 'Weekly') {
      frm.set_value('frequency', 'Weekly');
    }

    // Ensure default cycle_weeks
    if (!frm.doc.cycle_weeks || frm.doc.cycle_weeks < 1) {
      frm.set_value('cycle_weeks', 1);
    }

    // Default anchor date to start_date
    if (!frm.doc.cycle_anchor_date && frm.doc.start_date) {
      frm.set_value('cycle_anchor_date', frm.doc.start_date);
    }
  },

  start_date(frm) {
    if (!frm.doc.cycle_anchor_date && frm.doc.start_date) {
      frm.set_value('cycle_anchor_date', frm.doc.start_date);
    }
  },

  cycle_weeks(frm) {
    // If user decreases cycle weeks, block existing rows that are out of range
    const cw = cint(frm.doc.cycle_weeks || 1);

    let invalid = false;
    (frm.doc.route_days || []).forEach(row => {
      if (row.week_no && cint(row.week_no) > cw) {
        invalid = true;
      }
    });

    if (invalid) {
      frappe.msgprint(
        `Some Route Day rows have Week No greater than Number of Weeks (${cw}). Please correct Week No in rows.`
      );
    }
  }
});

// Child table events
frappe.ui.form.on('Route Day', {
  route_days_add(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const cw = cint(frm.doc.cycle_weeks || 1);

    // Default week_no to 1 when user adds a new row
    if (!row.week_no) row.week_no = 1;

    // If cycle_weeks is 1, force week_no=1
    if (cw === 1) row.week_no = 1;

    frm.refresh_field('route_days');
  },

  week_no(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const cw = cint(frm.doc.cycle_weeks || 1);

    if (!row.week_no) return;

    if (cint(row.week_no) < 1) {
      row.week_no = 1;
      frm.refresh_field('route_days');
      return;
    }

    if (cint(row.week_no) > cw) {
      frappe.msgprint(`Week No must be between 1 and ${cw}.`);
      row.week_no = cw;
      frm.refresh_field('route_days');
    }
  }
});



// // Copyright (c) 2025, Salesman Journey and contributors
// // For license information, please see license.txt

// // frappe.ui.form.on("Journey Plan Template", {
// // 	refresh(frm) {

// // 	},
// // });
// frappe.ui.form.on('Journey Plan Template', {
//     setup(frm) {
//         frm.set_query('salesman', () => {
//             return {
//                 query: 'frappe.core.doctype.user.user.user_query',
//                 filters: {
//                     role: 'Sales User',
//                     user_type: 'System User', 
//                     enabled: 1                
//                 }
//             };
//         });
//     },
//     refresh(frm) {
//         if (frm.doc.salesman) {
//             frappe.db.get_value('User', frm.doc.salesman, 'enabled').then(r => {
//                 if (r && r.message && r.message.enabled === 0) {
//                     frappe.msgprint(__('Selected Salesman is disabled. Please choose an active Sales User.'));
//                     frm.set_value('salesman', null);
//                 }
//             });
//         }
//     }
// });
