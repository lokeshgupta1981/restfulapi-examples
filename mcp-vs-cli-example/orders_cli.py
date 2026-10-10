"""orders: a small command-line tool for the order service.

Examples:
  python orders_cli.py list --customer C-5 --status paid
  python orders_cli.py list --customer C-5 --status paid --fields id,total --json
  python orders_cli.py get ORD-1007 --json
  python orders_cli.py cancel ORD-1007 --reason "customer request"
"""
import argparse
import json
import sys

import orders_core


def print_orders(orders, fields, as_json):
    if fields:
        orders = [{f: o[f] for f in fields} for o in orders]
    if as_json:
        print(json.dumps(orders))
        return
    for o in orders:
        print("  ".join(str(v) for v in o.values()) if fields else
              f"{o['id']}  {o['customer_id']}  {o['status']:<9}  {o['total']:>8.2f} {o['currency']}")


def main():
    parser = argparse.ArgumentParser(prog="orders", description="Read and change orders.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List orders, filtered by customer and status.")
    p_list.add_argument("--customer", help="Customer ID, for example C-5.")
    p_list.add_argument("--status", choices=orders_core.STATUSES)
    p_list.add_argument("--fields", help="Comma-separated fields to print, for example id,total.")
    p_list.add_argument("--json", action="store_true", help="Print JSON instead of a table.")

    p_get = sub.add_parser("get", help="Show one order.")
    p_get.add_argument("order_id")
    p_get.add_argument("--json", action="store_true", help="Print JSON.")

    p_cancel = sub.add_parser("cancel", help="Cancel an open or paid order.")
    p_cancel.add_argument("order_id")
    p_cancel.add_argument("--reason", required=True)

    args = parser.parse_args()
    try:
        if args.command == "list":
            fields = args.fields.split(",") if args.fields else None
            print_orders(orders_core.list_orders(args.customer, args.status), fields, args.json)
        elif args.command == "get":
            order = orders_core.get_order(args.order_id)
            print(json.dumps(order, indent=None if args.json else 2))
        elif args.command == "cancel":
            order = orders_core.cancel_order(args.order_id, args.reason)
            print(f"{order['id']} cancelled")
    except (KeyError, ValueError) as err:
        print(f"error: {err.args[0]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
