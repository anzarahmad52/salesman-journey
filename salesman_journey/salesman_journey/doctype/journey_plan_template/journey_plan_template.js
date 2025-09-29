// Copyright (c) 2025, Salesman Journey and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Journey Plan Template", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Journey Plan Template', {
    setup(frm) {
        frm.set_query('salesman', () => {
            return {
                query: 'frappe.core.doctype.user.user.user_query',
                filters: {
                    role: 'Sales User',
                    user_type: 'System User', 
                    enabled: 1                
                }
            };
        });
    },
    refresh(frm) {
        if (frm.doc.salesman) {
            frappe.db.get_value('User', frm.doc.salesman, 'enabled').then(r => {
                if (r && r.message && r.message.enabled === 0) {
                    frappe.msgprint(__('Selected Salesman is disabled. Please choose an active Sales User.'));
                    frm.set_value('salesman', null);
                }
            });
        }
    }
});
