"""How Python builds and parses query strings and path segments."""

from urllib.parse import parse_qs, quote, urlencode

search_params = {"q": "C++ Primer"}
form_style = urlencode(search_params)
rfc3986_style = urlencode(search_params, quote_via=quote)
print("urlencode (form style):  ", form_style)
print("urlencode (quote_via):   ", rfc3986_style)

sku = "AB/12"
print("quote(sku) default safe: ", quote(sku))
print("quote(sku, safe=''):     ", quote(sku, safe=""))

company = "AT&T Modem"
print("quote(company, safe=''): ", quote(company, safe=""))

raw_query = "q=C++&tag=a&tag=b"
print("raw_query:               ", raw_query)
print("parse_qs(raw_query):     ", parse_qs(raw_query))
