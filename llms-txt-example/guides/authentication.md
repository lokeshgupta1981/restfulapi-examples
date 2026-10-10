# Authentication

Send an API key in the Authorization header of every request:

    Authorization: Bearer sk_test_...

Keys that start with sk_test_ work only against test data. Keys that start with sk_live_ move real money. A missing or wrong key returns HTTP 401.
