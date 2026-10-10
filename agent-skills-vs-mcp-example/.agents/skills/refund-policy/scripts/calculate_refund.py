"""Calculate a refund in cents: calculate_refund.py <plan> <days_since_invoice> <amount_cents>"""

import sys

plan, days, amount = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
if days > 90:
    refund, rule = 0, "more than 90 days: no refund"
elif plan == "monthly":
    refund, rule = (amount, "monthly, 0 to 14 days: 100 percent") if days <= 14 else (
        (amount // 2, "monthly, 15 to 30 days: 50 percent") if days <= 30 else (0, "monthly after 30 days: no refund"))
elif plan == "annual":
    if days <= 30:
        refund, rule = amount, "annual, 0 to 30 days: 100 percent"
    else:
        unused_months = 12 - (days + 29) // 30
        refund, rule = amount * unused_months // 12, f"annual, 31 to 90 days: pro rata, {unused_months} of 12 months"
else:
    sys.exit(f"unknown plan {plan}")
print(f"refund_cents={refund} rule={rule}")
