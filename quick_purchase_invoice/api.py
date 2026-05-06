"""Whitelisted helpers used by the Quick Purchase Invoice form."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def get_supplier_last_rate(supplier: str, item_code: str) -> float | None:
    """Return the most recent rate this supplier charged for ``item_code``.

    Looks at submitted Purchase Invoice Items first; falls back to None.
    """
    if not (supplier and item_code):
        return None

    row = frappe.db.sql(
        """
        SELECT pii.rate
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pii.item_code = %(item_code)s
          AND pi.supplier  = %(supplier)s
          AND pi.docstatus = 1
        ORDER BY pi.posting_date DESC, pi.creation DESC
        LIMIT 1
        """,
        {"item_code": item_code, "supplier": supplier},
        as_dict=True,
    )
    if row:
        return float(row[0]["rate"]) if row[0]["rate"] else None
    return None
