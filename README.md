# quick_purchase_invoice

A Frappe v16 / ERPNext custom app that gives bookkeepers a single-screen, keyboard-fast way to capture supplier bills.

The signature feature is a **QuickBooks-style "Type" toggle** on every line — pick **Item** or **Account** and the second column's lookup switches accordingly. No drilling into a row's edit pencil to set an expense account.

## Install

```bash
bench get-app https://github.com/Syncflo-design/quick_purchase_invoice
bench --site <yoursite> install-app quick_purchase_invoice
```

On Frappe Cloud:

1. Bench → Apps → **Add App** → point at the GitHub repo / branch.
2. Bench → Sites → install the app on the target site.
3. (Optional) deploy.

## Use

Desk → search "Quick Purchase Invoice" → New.

Header: Company, Supplier, Bill No, Posting Date. Currency is auto-set from the supplier (override if needed). Pick a Purchase Tax Template if applicable.

Items grid: pick **Type = Item** or **Type = Account** for each line. The second column ("Item / Account") becomes an Item or Account picker accordingly. For Account rows, Qty is locked to 1.

Save & Submit creates the real Purchase Invoice in ERPNext, links it back, and clears the form for the next bill. Users with the **Accounts User** role auto-submit the resulting PI; others leave it as a draft for finance to review.

## Status

v0.0.1 — initial build, Frappe v16 / ERPNext v16. Tested against `nesterp.jh.frappe.cloud`.

## License

MIT
