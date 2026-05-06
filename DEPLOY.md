# Deploying `quick_purchase_invoice` to nesterp.jh.frappe.cloud

Tested target: Frappe v16 / ERPNext v16 on Frappe Cloud.

## 1 — Push the code to GitHub

From `C:\ClaudeCode\CoWork_Helper\projects\quick_purchase_invoice`:

```bash
cd C:\ClaudeCode\CoWork_Helper\projects\quick_purchase_invoice
git init
git branch -M main
git add .
git commit -m "feat: initial Quick Purchase Invoice app (Item-or-Account row toggle)"
git remote add origin https://github.com/Syncflo-design/quick_purchase_invoice.git
git push -u origin main
```

(Create the empty repo on GitHub first: https://github.com/organizations/Syncflo-design/repositories/new — name `quick_purchase_invoice`, no README, no .gitignore, no license.)

## 2 — Add the app to your bench on Frappe Cloud

1. Open the **Bench** that owns `nesterp.jh.frappe.cloud`.
2. **Apps** tab → **Add App**.
3. Pick **Add from GitHub** → URL `https://github.com/Syncflo-design/quick_purchase_invoice`, branch `main`.
4. Frappe Cloud builds. Once green, click **Deploy** on the bench.
5. **Sites** tab → `nesterp` → **Apps** → **Install** → pick `quick_purchase_invoice`.

## 3 — Smoke-test (5 minutes)

After install, on `nesterp.jh.frappe.cloud`:

1. Login as a user with the `Accounts User` role.
2. Top-bar search → **Quick Purchase Invoice** → **+ New**.
3. Fill:
   - Company: *Syncflo Testing*
   - Supplier: *PNA*
   - Bill No: `TEST-001`
   - Posting Date: today
4. Items grid:
   - Row 1 (**Item** row): Type = Item; pick any Item (e.g. `AdHoc01`); description should auto-fill; set Qty = 1, Rate = 100.
   - Row 2 (**Account** row): Type = Account; pick any Expense account (e.g. *Bank Charges*); description auto-fills; Qty locks to 1; Rate = 50.
5. Watch the orange "this invoice mixes Item and Account rows" toast appear (cosmetic warning, not blocking).
6. **Save & Submit**.
7. Expected:
   - Toast: "Purchase Invoice ACC-PINV-XXX created."
   - Form clears, navigates to a new blank Quick PI.
   - Original Quick PI shows `Linked Purchase Invoice` populated.
   - The linked PI has `bill_no=TEST-001`, two rows: one with `item_code=AdHoc01`, one with `expense_account=<chosen account>` and blank `item_code`.

## 4 — Updating

After code changes:

```bash
git add . && git commit -m "..." && git push
```

Then in Frappe Cloud → Bench → Apps → click **Update** on the `quick_purchase_invoice` row → Deploy. Migrations run automatically.

## 5 — Rolling back

Frappe Cloud keeps the previous deploy. If the new release is broken:

- Bench → **Deploys** tab → previous green deploy → **Rollback to this**.

## Common deploy issues

- **`InvalidGitHubUrl`** — the repo must be public OR the bench's deploy key must be added as a Deploy Key on the GitHub repo (Settings → Deploy keys → Add → paste the key Frappe Cloud shows).
- **`No module named quick_purchase_invoice`** after install — bench wasn't redeployed after add-app. Click Deploy on the bench Deploys tab.
- **`Module quick_purchase_invoice has no DocType named X`** — uninstall + reinstall, OR run `bench --site nesterp.jh.frappe.cloud migrate` from the SSH console (Bench → Settings → SSH).
