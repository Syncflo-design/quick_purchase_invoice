// Quick Purchase Invoice — form script
// Goals:
//  1. QuickBooks-style "Type" toggle: when entry_type changes, the entry_ref
//     dynamic-link target switches between Item and Account.
//  2. Smart defaults: today's date, supplier currency, last purchase rate from
//     this supplier, account-name as default description.
//  3. After submit, redirect to a fresh blank form (Save & New).

frappe.ui.form.on("Quick Purchase Invoice", {
    refresh(frm) {
        frm.page.wrapper.addClass("quick-pi-form");
        paint_row_classes(frm);

        // After submit, jump straight to a new blank one (clear & next).
        if (frm.doc.docstatus === 1 && frm.doc.linked_purchase_invoice && !frm._post_submit_handled) {
            frm._post_submit_handled = true;
            frappe.show_alert({
                message: __("Purchase Invoice {0} created.", [frm.doc.linked_purchase_invoice]),
                indicator: "green",
            }, 6);
            // Tiny delay so the user sees the toast before the form resets.
            setTimeout(() => frappe.set_route("Form", "Quick Purchase Invoice", "new"), 700);
        }

        // Quick link to the resulting PI in the form sidebar.
        if (frm.doc.linked_purchase_invoice) {
            frm.add_custom_button(__("Open Purchase Invoice"), () => {
                frappe.set_route("Form", "Purchase Invoice", frm.doc.linked_purchase_invoice);
            });
        }
    },

    onload(frm) {
        if (frm.is_new()) {
            if (!frm.doc.posting_date) {
                frm.set_value("posting_date", frappe.datetime.get_today());
            }
        }

        // Restrict the tax template to the chosen company.
        frm.set_query("taxes_and_charges", () => ({
            filters: { company: frm.doc.company || "" },
        }));

        // Restrict accounts in row picker to leaf, non-group, in the right company.
        frm.set_query("entry_ref", "items", (doc, cdt, cdn) => {
            const row = locals[cdt][cdn];
            if (row.entry_type === "Account") {
                return {
                    filters: {
                        is_group: 0,
                        company: doc.company || "",
                        root_type: ["in", ["Expense", "Asset", "Liability", "Income"]],
                    },
                };
            }
            // Item rows: optionally filter to "is_purchase_item=1".
            return { filters: { disabled: 0, is_purchase_item: 1 } };
        });
    },

    company(frm) {
        // Re-apply tax-template filter when company changes.
        frm.set_query("taxes_and_charges", () => ({ filters: { company: frm.doc.company || "" } }));
    },

    async supplier(frm) {
        if (!frm.doc.supplier) return;
        const sup = await frappe.db.get_doc("Supplier", frm.doc.supplier);
        if (sup.default_currency) {
            frm.set_value("currency", sup.default_currency);
        } else {
            // Fall back to company currency.
            const company = frm.doc.company;
            if (company) {
                const c = await frappe.db.get_value("Company", company, "default_currency");
                if (c && c.message && c.message.default_currency) {
                    frm.set_value("currency", c.message.default_currency);
                }
            }
        }
    },

    validate(frm) {
        // Soft warning when rows mix Item and Account types.
        if (frm._mix_warning_shown) return;
        const types = new Set((frm.doc.items || []).map(r => r.entry_type || "Item"));
        if (types.size > 1) {
            frappe.show_alert({
                message: __("This invoice mixes Item and Account rows — make sure that's intended."),
                indicator: "orange",
            }, 7);
            frm._mix_warning_shown = true;
        }
    },
});

frappe.ui.form.on("Quick Purchase Invoice Item", {
    items_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        // Defaults so a brand-new row is consistent before the user touches it.
        if (!row.entry_type) row.entry_type = "Item";
        row.link_doctype = row.entry_type;
        if (!row.qty) row.qty = 1;
        // Repaint after the new row is rendered into the DOM.
        setTimeout(() => paint_row_classes(frm), 30);
    },

    entry_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const new_type = row.entry_type || "Item";
        row.link_doctype = new_type;
        // Clear the picker — its target doctype just changed.
        row.entry_ref = null;
        row.description = null;
        row.rate = 0;
        if (new_type === "Account") {
            // Account rows always have qty=1.
            row.qty = 1;
            frappe.model.set_value(cdt, cdn, "qty", 1);
        }
        frm.refresh_field("items");
        compute_amount(frm, cdt, cdn);
        paint_row_classes(frm);
    },

    async entry_ref(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.entry_ref) return;
        if (row.entry_type === "Item") {
            await fill_from_item(frm, cdt, cdn);
        } else if (row.entry_type === "Account") {
            await fill_from_account(frm, cdt, cdn);
        }
        compute_amount(frm, cdt, cdn);
    },

    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        // Guard: Account rows must stay at qty=1.
        if (row.entry_type === "Account" && flt(row.qty) !== 1) {
            frappe.model.set_value(cdt, cdn, "qty", 1);
        }
        compute_amount(frm, cdt, cdn);
    },

    rate(frm, cdt, cdn) {
        compute_amount(frm, cdt, cdn);
    },
});

// --- helpers ----------------------------------------------------------------

/**
 * Tag each items grid row with a CSS class reflecting its entry_type.
 * Lets stylesheet draw the coloured left-strip + Type pill without per-cell DOM hacks.
 */
function paint_row_classes(frm) {
    const grid = frm.fields_dict && frm.fields_dict.items && frm.fields_dict.items.grid;
    if (!grid || !grid.grid_rows) return;
    grid.grid_rows.forEach(gr => {
        if (!gr || !gr.row) return;
        const $row = (gr.row instanceof jQuery) ? gr.row : window.$(gr.row);
        $row.removeClass("qpi-type-item qpi-type-account");
        const t = (gr.doc && gr.doc.entry_type) || "Item";
        $row.addClass(t === "Account" ? "qpi-type-account" : "qpi-type-item");
    });
}


function compute_amount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, "amount", amount);
    refresh_totals(frm);
}

function refresh_totals(frm) {
    let net = 0, qty = 0;
    (frm.doc.items || []).forEach(r => {
        net += flt(r.amount);
        qty += flt(r.qty);
    });
    frm.set_value("net_total", net);
    frm.set_value("total_qty", qty);
    frm.set_value("grand_total", net + flt(frm.doc.total_taxes_and_charges));
}

async function fill_from_item(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const item = await frappe.db.get_doc("Item", row.entry_ref);
    if (!row.description) {
        frappe.model.set_value(cdt, cdn, "description", item.description || item.item_name);
    }
    // Last purchase rate from THIS supplier.
    let rate = null;
    if (frm.doc.supplier) {
        const r = await frappe.call({
            method: "quick_purchase_invoice.api.get_supplier_last_rate",
            args: { supplier: frm.doc.supplier, item_code: row.entry_ref },
        });
        if (r && r.message) rate = flt(r.message);
    }
    if (!rate && item.last_purchase_rate) rate = flt(item.last_purchase_rate);
    if (rate) frappe.model.set_value(cdt, cdn, "rate", rate);
}

async function fill_from_account(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const acc = await frappe.db.get_value("Account", row.entry_ref, ["account_name"]);
    if (acc && acc.message && acc.message.account_name && !row.description) {
        frappe.model.set_value(cdt, cdn, "description", acc.message.account_name);
    }
}

// Frappe ships a global flt() helper but defining a local fallback keeps this
// file lint-clean for editors that don't load Frappe globals.
function flt(v) {
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
}
