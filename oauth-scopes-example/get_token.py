"""Get an access token with the authorization code flow and PKCE.

Usage: python get_token.py --client bookshop-web --user asha --scope "orders:read"
       add -v to print the authorization request and the redirect

The demo authorization server signs in the user named in --user without a
login page, so the whole flow runs from the command line.
"""
import argparse
import json
import sys

from oauth_client import fetch_token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", default="bookshop-web")
    parser.add_argument("--secret", help="client secret for confidential clients")
    parser.add_argument("--user", default="asha")
    parser.add_argument("--scope", default="")
    parser.add_argument("-v", action="store_true", help="print the redirect steps")
    args = parser.parse_args()

    log = (lambda line: print(line, file=sys.stderr)) if args.v else None
    result = fetch_token(args.client, args.secret, args.user, args.scope, log=log)
    print(json.dumps(result, indent=2))
    sys.exit(0 if "access_token" in result else 1)


if __name__ == "__main__":
    main()
