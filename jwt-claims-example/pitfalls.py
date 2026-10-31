"""What PyJWT checks when we forget to ask: run each case and print the outcome."""
import jwt

from tokens import AUDIENCE, ISSUER, PUBLIC_KEY, make_token


def attempt(label, token, **kwargs):
    try:
        claims = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], **kwargs)
        print(f"{label:<52} ACCEPTED (sub={claims.get('sub')})")
    except jwt.InvalidTokenError as e:
        print(f"{label:<52} REJECTED: {type(e).__name__}: {e}")


print("PyJWT", jwt.__version__)
attempt("1. no exp, plain decode()", make_token(drop=["exp"]), audience=AUDIENCE)
attempt("2. no exp, require=['exp']", make_token(drop=["exp"]), audience=AUDIENCE,
        options={"require": ["exp"]})
attempt("3. wrong iss, issuer not passed", make_token(iss="https://evil.example"), audience=AUDIENCE)
attempt("4. wrong iss, issuer passed", make_token(iss="https://evil.example"), audience=AUDIENCE,
        issuer=ISSUER)
attempt("5. token has aud, audience not passed", make_token())
attempt("6. no aud at all, audience not passed", make_token(drop=["aud"]))
attempt("7. no aud at all, require=['aud']", make_token(drop=["aud"]), options={"require": ["aud"]})
attempt("8. sub is a number", make_token(sub=4711), audience=AUDIENCE)
attempt("9. unknown claim 'admin': true", make_token(admin=True), audience=AUDIENCE)
