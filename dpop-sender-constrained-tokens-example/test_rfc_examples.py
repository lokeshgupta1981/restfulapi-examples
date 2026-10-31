"""Checks our thumbprint and ath code against the examples in RFC 9449."""
import dpop

# RFC 9449, figure 4 (public key) and figure 9 (its jkt in the cnf claim)
rfc_jwk = {"kty": "EC", "crv": "P-256",
           "x": "l8tFrhx-34tV3hRICRDY9zCkDlpBhF42UQUfWVAWBFs",
           "y": "9VE4jf_Ok_o64zbTTlcuNJajHmt6v9TDVrU0CdvGRDA"}
assert dpop.jwk_thumbprint(rfc_jwk) == "0ZcOCORZNYy-DWpqq30jZyJGHTN0d2HglBV3uiguA4I"

# RFC 9449, figures 13 and 14 (access token and its ath)
assert dpop.access_token_hash("Kz~8mXK1EalYznwH-LC-1fBAo.4Ljp~zsPE_NeO.gxU") == \
    "fUHyO2r2Z3DZ53EsNrWBb0xWXoaNy59IiKCAqksmQEo"

print("RFC 9449 examples: jkt and ath match")
