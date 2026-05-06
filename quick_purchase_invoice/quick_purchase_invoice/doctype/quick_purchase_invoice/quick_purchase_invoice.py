"""Quick Purchase Invoice — staging doc that creates a real Purchase Invoice on submit.

The form is optimised for fast keyboard capture; the ERPNext Purchase Invoice is the
authoritative accounting record. After submit, ``linked_purchase_invoice`` points at
the newly-created PI.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# Roles that should auto-submit the resulting Purchase Invoice.
# Any user without one of these roles will get a draft PI for finance to review.
AUTO_SUBMIT_ROLES = {"Accounts User", "Accounts Manager"}


class QuickPurchaseInvoice(Document):
    # --- lifecycle -----------------------------------------------------------

    def validate(self):
        self._sanitise_rows()
        self._validate_rows()
        self._compute_totals()

    def on_submit(self):
        pi_name = self._create_purchase_invoice()
        self.db_set("linked_purchase_invoice", pi_name)
        self.db_set("status", "Submitted")

    def on_cancel(self):
        # We deliberately do NOT cancel the linked PI automatically — that's an
        # accounting decision and should be done explicitly by finance. Just mark
        # the staging doc as cancelled so it falls out of normal lists.
        self.db_set("status", "Cancelled")

    # --- validation helpers --------------------------------------------------

    def _sanitise_rows(self) -> None:
        """Force per-row invariants (Account rows have qty=1, link_doctype mirrors entry_type)."""
        for row in self.items or []:
            entry_type = row.entry_type or "Item"
            row.entry_type = entry_type
            row.link_doctype = entry_type
            if entry_type == "Account":
                row.qty = 1
            row.amount = round(flt(row.qty) * flt(row.rate), 2)

    def _validate_rows(self) -> None:
        if not self.items:
            frappe.throw(_("Add at least one item or account row before submitting."))
        for idx, row in enumerate(self.items, start=1):
            if not row.entry_ref:
                frappe.throw(_("Row #{0}: please pick an {1}.").format(idx, row.entry_type or "Item"))
            if flt(row.rate) <= 0:
                frappe.throw(_("Row #{0}: Rate must be greater than zero.").format(idx))
            if row.entry_type == "Item":
                if not frappe.db.exists("Item", row.entry_ref):
                    frappe.throw(_("Row #{0}: Item {1} does not exist.").format(idx, row.entry_ref))
            elif row.entry_type == "Account":
                acc = frappe.db.get_value(
                    "Account",
                    row.entry_ref,
                    ["is_group", "company", "root_type"],
                    as_dict=True,
                )
                if not acc:
                    frappe.throw(_("Row #{0}: Account {1} does not exist.").format(idx, row.entry_ref))
                if acc.is_group:
                    frappe.throw(
                        _("Row #{0}: Account {1} is a group account; pick a leaf account.")
                        .format(idx, row.entry_ref)
                    )
                if acc.company and acc.company != self.company:
                    frappe.throw(
                        _("Row #{0}: Account {1} belongs to company {2}, not {3}.")
                        .format(idx, row.entry_ref, acc.company, self.company)
                    )
            else:
                frappe.throw(_("Row #{0}: unsupported entry type {1}.").format(idx, row.entry_type))

    def _compute_totals(self) -> None:
        net = 0.0
        qty = 0.0
        for row in self.items or []:
            net += flt(row.amount)
            qty += flt(row.qty)
        self.net_total = round(net, 2)
        self.total_qty = round(qty, 2)
        # Tax preview — we copy the template's "rate" if it's a flat percentage.
        # The authoritative tax compute happens on the Purchase Invoice itself.
        self.total_taxes_and_charges = round(self._estimate_tax(net), 2)
        self.grand_total = round(self.net_total + (self.total_taxes_and_charges or 0), 2)

    def _estimate_tax(self, net_total: float) -> float:
        """Best-effort header tax preview based on the chosen template.

        We sum the percentage rates of each "On Net Total" row in the template and
        apply that to ``net_total``. This is a preview only; ERPNext will recompute
        on the real Purchase Invoice using its own tax engine.
        """
        if not self.taxes_and_charges:
            return 0.0
        try:
            template = frappe.get_doc("Purchase Taxes and Charges Template", self.taxes_and_charges)
        except frappe.DoesNotExistError:
            return 0.0
        total_pct = 0.0
        for tax in template.taxes or []:
            if (tax.charge_type or "") == "On Net Total":
                total_pct += flt(tax.rate)
        return net_total * total_pct / 100.0

    # --- submit pipeline -----------------------------------------------------

    def _create_purchase_invoice(self) -> str:
        """Build, insert, and (conditionally) submit the real Purchase Invoice.

        Returns the new PI's ``name``.
        """
        pi = frappe.new_doc("Purchase Invoice")
        pi.company = self.company
        pi.supplier = self.supplier
        pi.bill_no = self.bill_no
        pi.bill_date = self.posting_date
        pi.posting_date = self.posting_date
        pi.due_date = self.posting_date
        pi.currency = self.currency
        if self.conversion_rate:
            pi.conversion_rate = self.conversion_rate
        if self.taxes_and_charges:
            pi.taxes_and_charges = self.taxes_and_charges

        # Decide stock impact on the PI: enable update_stock if any Item row's
        # item is a stock item. Otherwise leave it off — non-stock posting only.
        any_stock_item = False

        for row in self.items:
            line = pi.append("items", {})
            line.qty = flt(row.qty) or 1
            line.rate = flt(row.rate)
            line.description = row.description or ""
            if row.entry_type == "Item":
                line.item_code = row.entry_ref
                item_doc = frappe.get_cached_doc("Item", row.entry_ref)
                if not line.description:
                    line.description = item_doc.description or item_doc.item_name
                if item_doc.is_stock_item:
                    any_stock_item = True
            else:  # Account
                # ERPNext requires *something* in item_name for blank-item lines;
                # we leave item_code blank and use the description as item_name.
                line.item_name = (row.description or row.entry_ref)[:140]
                line.expense_account = row.entry_ref
                # Make absolutely sure stock-related defaults don't fire.
                line.is_stock_item = 0
                line.uom = "Nos"

        pi.update_stock = 1 if any_stock_item else 0

        # If a tax template is set, copy its rows into the PI so amounts compute.
        if self.taxes_and_charges:
            template = frappe.get_doc("Purchase Taxes and Charges Template", self.taxes_and_charges)
            for tax in template.taxes or []:
                pi.append(
                    "taxes",
                    {
                        "category": tax.category,
                        "add_deduct_tax": tax.add_deduct_tax,
                        "charge_type": tax.charge_type,
                        "row_id": tax.row_id,
                        "account_head": tax.account_head,
                        "description": tax.description,
                        "rate": tax.rate,
                        "tax_amount": tax.tax_amount,
                        "cost_center": tax.cost_center,
                    },
                )

        pi.flags.ignore_permissions = False
        pi.insert()

        if self._user_can_auto_submit():
            pi.submit()

        return pi.name

    def _user_can_auto_submit(self) -> bool:
        """True if the current user has any of AUTO_SUBMIT_ROLES."""
        roles = set(frappe.get_roles(frappe.session.user))
        return bool(roles & AUTO_SUBMIT_ROLES)
