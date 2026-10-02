Source code for the article [OAuth for AI Agents: Securing Agent Access to REST APIs](https://restfulapi.net/oauth-for-ai-agents/) on restfulapi.net.

An AI agent gets access to a REST API with OAuth 2.0: discovery through a 401 response and protected resource metadata (RFC 9728), client credentials for an agent that acts for itself, authorization code with PKCE for the user, and token exchange (RFC 8693) with the `act` claim for an agent that acts for the user. The Orders API validates JWT access tokens (RFC 9068) and answers with 401 and 403 challenges (RFC 6750).

`auth_server.py` is a DEMO authorization server for learning only. It has no login page and signs in the demo user automatically. Use Keycloak, Auth0, Okta, Microsoft Entra ID or another real authorization server in production. The client secrets in the code are fake demo values.

## Tested versions

- Python 3.11.15 (3.10 or newer works)
- fastapi 0.142.2, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1, python-multipart 0.0.32

## Run

```
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/oauth-for-ai-agents-example
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1: the demo authorization server
uvicorn auth_server:app --port 9200

# Terminal 2: the Orders API
uvicorn orders_api:app --port 9201

# Terminal 3: the agent
python agent.py              # stops before the risky action
python agent.py --approve    # a human approved the cancel
```

Restart the Orders API to reset the orders.

## Files

- `auth_server.py`: demo authorization server (metadata, JWKS, authorize, token endpoint with client credentials, authorization code + PKCE and token exchange)
- `orders_api.py`: the REST API that validates tokens, enforces scopes and serves `/.well-known/oauth-protected-resource`
- `agent.py`: the agent client that discovers the authorization server, gets tokens and calls the API
