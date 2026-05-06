# quick_purchase_invoice — Design

A Frappe v15 custom app for ERPNext that gives bookkeepers a single-screen, keyboard-fast way to capture supplier bills, with a QuickBooks-style **Item / Account** row toggle.

## Why this exists

Stock ERPNext's Purchase Invoice form is rich but slow for high-volume bookkeeping. The biggest friction is that posting a non-stock GL expense (rent, bank charges, fees) requires either creating a non-stock Item or drilling into the row's edit pencil to set `expense_account`. This app removes that friction.

## UX summary

One DocType: **Quick Purchase Invoice** (staging — submits a real `Purchase Invoice` and links to it).

Single page. Header fields, then one items grid. On submit:
- A real `Purchase Invoice` is created in the chosen company.
- For users with the `Accounts User` role, the PI is also submitted (`docstatus=1`).
- For everyone else, the PI is left as a draft for finance to review.
- Form is cleared and refocused on Supplier for the next bill.

## Header fields

| Field | Type | Default | Required |
|---|---|---|---|
| `company` | Link → Company | "Syncflo Testing" | yes |
| `supplier` | Link → Supplier | — | yes |
| `bill_no` | Data | — | yes (supplier's invoice number) |
| `posting_date` | Date | today | yes (also used as bill_date) |
| `currency` | Link → Currency | from supplier; falls back to company | yes |
| `conversion_rate` | Float | 1.0 | shown only if currency ≠ company_currency |
| `taxes_and_charges` | Link → Purchase Taxes and Charges Template | first default for company, else blank | no |
| `linked_purchase_invoice` | Link → Purchase Invoice | populated after submit | read-only |

## Items grid (`Quick Purchase Invoice Item`, child table)

| Field | Type | Behaviour |
|---|---|---|
| `entry_type` | Select [Item, Account] | default "Item" |
| `item_code` | Link → Item | visible only when `entry_type` = Item |
| `account` | Link → Account | visible only when `entry_type` = Account; filtered to `is_group=0` AND root_type IN (Expense, Asset, Liability) |
| `description` | Small Text | auto-fills from item description (Item rows) or account name (Account rows); editable |
| `qty` | Float | Item: editable, default 1; Account: locked to 1, read-only |
| `rate` | Currency | Item: defaults from this supplier's last purchase rate for this item; Account: user types |
| `amount` | Currency | computed `qty × rate`, read-only |

The dynamic Item-vs-Account behaviour is implemented via `depends_on` expressions on the two link fields, plus a form script that re-applies read-only flags on `qty` when `entry_type` changes.

## Validation

Per row:
- `entry_type` = Item → `item_code` required; `account` ignored.
- `entry_type` = Account → `account` required; `item_code` ignored. `qty` forced to 1.
- `rate` and `amount` must be > 0.

Header-level:
- At least one row required.
- If the rows mix Item and Account types, the form-script flashes a non-blocking confirmation toast — the user can proceed.

## Submit pipeline

`quick_purchase_invoice.api.create_purchase_invoice(quick_pi_name)`:

1. Load the staged Quick PI doc.
2. Build a `Purchase Invoice` doc with header fields copied across.
3. For each row:
   - **Item row** → push a `Purchase Invoice Item` with `item_code`, `qty`, `rate`, `description`. Let ERPNext fill `expense_account` from Item Defaults. `update_stock` flag respects the item's `is_stock_item`.
   - **Account row** → push a `Purchase Invoice Item` with no `item_code`, `qty=1`, `rate=amount`, `expense_account=<account>`, `description=<description>`. ERPNext allows item-less rows when `expense_account` is set.
4. If header has `taxes_and_charges`, fetch the template and copy its `taxes` child rows.
5. `pi.insert()`.
6. If user has role `Accounts User`, `pi.submit()`.
7. Stamp `linked_purchase_invoice` on the Quick PI.
8. Return the new PI's name.

## Defaults & smart fills (form script)

- On `supplier` change: read `Supplier.default_currency`; if set and ≠ company_currency, populate `currency` and prompt for `conversion_rate`.
- On `item_code` change in a row: query the most recent `Purchase Invoice Item` row for `(supplier, item_code, docstatus=1)` ordered by `posting_date desc`, take its `rate`. Fall back to `Item.last_purchase_rate`. Fall back to blank.
- On `account` change: copy account name into `description` if `description` is blank.
- On `entry_type` change: if switching to Account, force `qty=1` and clear `item_code`; if switching to Item, clear `account`.

## Roles

The app does NOT create a new role. It looks at the logged-in user's roles:
- Has `Accounts User`? → auto-submit the resulting Purchase Invoice.
- Otherwise? → leave as draft.

(Russell can flip this later by editing `quick_purchase_invoice.api.AUTO_SUBMIT_ROLES`.)

## Out of scope (v1)

- Cost Center selection (uses company default)
- File / PDF attachment field
- Debit notes / returns
- Multi-row tax categories (header template only)
- Bulk paste / CSV import
- Mobile-friendly layout (desktop-first; mobile later if needed)
