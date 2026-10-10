---
name: refund-policy
description: Decide whether and how much to refund for a customer invoice, following the company refund rules. Use when a customer asks for a refund, a credit or money back on an invoice.
metadata:
  owner: billing-team
  version: "1.2"
---

# Refund policy

Follow these steps for every refund request.

1. Get the invoice with the `get_invoice` tool of the billing MCP server.
2. Read [the refund rules](references/REFUND-RULES.md) and find the rule that matches the plan and the age of the invoice.
3. Calculate the amount with `scripts/calculate_refund.py <plan> <days_since_invoice> <amount_cents>`.
   Never calculate the amount yourself.
4. If the amount is above 50000 cents, stop and ask a human approver.
5. Otherwise call `issue_refund` with the invoice ID and the calculated amount, and tell the customer the amount and the rule you applied.
