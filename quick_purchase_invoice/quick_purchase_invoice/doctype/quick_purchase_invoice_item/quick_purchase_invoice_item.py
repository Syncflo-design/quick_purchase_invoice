import frappe
from frappe.model.document import Document


class QuickPurchaseInvoiceItem(Document):
    """Child row of Quick Purchase Invoice.

    Validation is intentionally light here — the parent's `validate` handles cross-row
    rules (e.g. "at least one row required") and the type-specific assertions.
    The compute of `amount` happens here because it's a pure per-row derivation.
    """

    def validate(self):
        # Force qty=1 for Account rows; lets us trust the value downstream.
        if (self.entry_type or "Item") == "Account":
            self.qty = 1

        # Keep the helper field in sync; this is also done client-side, but this
        # guards against stray inserts that bypass the form (e.g. via REST).
        self.link_doctype = self.entry_type or "Item"

        # Recompute amount.
        qty = float(self.qty or 0)
        rate = float(self.rate or 0)
        self.amount = round(qty * rate, 2)
