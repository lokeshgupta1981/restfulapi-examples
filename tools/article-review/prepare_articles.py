from pathlib import Path
from bs4 import BeautifulSoup
import re, json, difflib

ROOT=Path('C:\\Users\\lokes\\OneDrive\\Documents\\ChatGPT\\restfulapi\\ai-drafts-review')
OUT=ROOT/'articles'; OUT.mkdir(exist_ok=True)
changes={}; texts={}
for item in json.loads((ROOT/'manifest.json').read_text()):
    texts[item['id']]=(ROOT/'originals'/(item['id']+'.wp.html')).read_text(encoding='utf-8')
    changes[item['id']]=[]

def replace(post, old, new):
    raw=texts[post]
    # Only prose outside preformatted examples is eligible.
    parts=re.split(r'(<pre\b.*?</pre>)',raw,flags=re.S)
    count=sum(p.count(old) for i,p in enumerate(parts) if i%2==0)
    assert count==1,(post,old,count)
    texts[post]=''.join(p.replace(old,new) if i%2==0 else p for i,p in enumerate(parts))
    changes[post].append({'before':old,'after':new})

def after(post,prefix,paragraphs):
    raw=texts[post]
    matches=[m for m in re.finditer(r'<!-- wp:paragraph[^>]*-->\s*<p\b.*?</p>\s*<!-- /wp:paragraph -->',raw,re.S)
             if BeautifulSoup(m.group(),'html.parser').get_text(' ',strip=True).startswith(prefix)]
    assert len(matches)==1,(post,prefix,len(matches))
    m=matches[0]
    addition='\n\n'.join('<!-- wp:paragraph -->\n<p>'+p+'</p>\n<!-- /wp:paragraph -->' for p in paragraphs)
    texts[post]=raw[:m.end()]+'\n\n'+addition+raw[m.end():]
    changes[post].append({'expanded_after':prefix,'paragraphs':paragraphs})

# Connection troubleshooting: explain errors by their layer and avoid unsafe retries.
replace('3076','could not start an MCP server or could not finish a request to it, so the server\'s tools do not show up or a tool call fails.','could not start an MCP server or complete a request to it. The server may appear disconnected, its tools may be missing, or a particular call may fail.')
replace('3076','A local server fails with startup and process errors, and a remote server fails with HTTP status codes.','For stdio, start with the process and its standard error output. For HTTP, check network connectivity first, then the status code and response body. A local server can use either transport.')
replace('3076','means the operating system found no program with that name.','usually means the operating system could not find the executable. An invalid working directory can produce the same error, so check that path too when the executable is present.')
replace('3076','means the server process started and exited before it answered the request.','means the client reached the end of the server\'s output stream before the exchange finished. The process may have crashed or exited normally; the message alone does not establish which.')
replace('3076','When Inspector connects and lists the tools, the server is fine and the problem is in the host\'s configuration, its <em>PATH</em>, its environment variables or its MCP version.','When Inspector connects and lists tools, that particular command, environment and discovery path work. Compare those settings with the host\'s configuration, <em>PATH</em>, environment and protocol version. A successful listing does not test every tool or the host\'s authorization flow.')
after('3076','For a slow tool, measure',[
    'A timeout does not prove that the server stopped working. If a cancellation, payment or deployment request times out, check its status before sending it again. Reuse an idempotency key when the service supports one; otherwise, a retry can repeat a change that already succeeded.',
    'Keep the first error and the matching server log entry when asking for help. Include the host and SDK versions, transport, command or endpoint path, and the time of the failure. Remove bearer tokens, API keys, personal data and secrets from the logs before sharing them.'
])

# llms.txt: discovery is an opt-in convention, not an access or ranking control.
replace('3063','so the agent reads a few small Markdown files instead of crawling HTML pages.','so an agent that supports or is directed to the index can find the relevant Markdown pages without parsing the full documentation site.')
replace('3063','The honest answer in October 2026 is that coding agents and documentation tools use it, while search engines and most AI crawlers do not.','Some coding agents and documentation integrations use <em>llms.txt</em>. Publishing the file does not require any agent, crawler or search engine to fetch it, and support depends on the tool and its configuration.')
replace('3063','The agent pays for every one of those tokens,','If the HTML is passed to the model without effective extraction, navigation and layout consume context tokens,')
after('3063','Keep secrets and private URLs out',[
    'The file is documentation, not an access-control mechanism. A link in <em>Optional</em> remains a public link, and leaving an endpoint out of the index does not protect it. Apply authentication and authorization to the API and any private documentation independently.',
    'Generate the index in the same build that publishes the documentation. Validate that each linked page exists, describes the deployed API version, and uses the correct base URL. When a page moves, update the index or keep a redirect so an agent does not generate code from a stale guide.'
])

# Transport guide: protocol statelessness does not make writes retry-safe.
replace('3010','When the server crashes, the client restarts it and sends the lost requests again.','After an unexpected exit, the client should restart the server and reconnect. It can retry lost reads, but it must establish whether a write already succeeded before repeating that write.')
replace('3010','so a <em>tools/list</em> request returns the same tools over stdio and over HTTP.','so choosing a transport does not change what <em>tools/list</em> means. The tools visible to a caller can still depend on authorization and server configuration.')
replace('3010','any instance can answer any request, and a server restart loses only the requests that were in progress.','requests no longer require a connection-scoped MCP session. Any instance can answer a request only if it can also reach the application data and job state that the request needs.')
replace('3010','The header <em>X-Accel-Buffering: no</em> tells reverse proxies such as nginx not to buffer the stream,','The header <em>X-Accel-Buffering: no</em> tells nginx not to buffer the stream,')
after('3010','A stdio server becomes an HTTP server',[
    'The transport switch also changes the trust boundary. A shared service must obtain the caller\'s identity from verified credentials rather than from a customer ID supplied by the model. Keep per-user authorization in the tools and the underlying API even when all requests enter through one endpoint.',
    'For multiple HTTP instances, store shared business state in a database or job service. Protocol statelessness removes the MCP session dependency; it does not copy an in-memory cart, export or task from one process to another. Route explicit state handles to storage that every permitted instance can access.'
])

# Generated tools: omitted annotations are not evidence of safety.
replace('2770','The tool has no <em>destructiveHint</em> annotation, so the host has no signal to ask the user first.','The tool omits <em>destructiveHint</em>, so its definition does not explicitly classify the deletion. Omission is not evidence that a tool is safe, and the host still needs an approval policy for writes.')
replace('2770','but a host can only do that when the server tells it which tools are sensitive.','and the host must enforce its own policy rather than assuming an unannotated tool is safe.')
replace('2770','The host sends the tool list to the model with every request, so every tool costs tokens even when nobody calls it.','A host that includes the complete tool list in every model request pays for those definitions even when no tool is called. Hosts with tool search or on-demand loading can reduce that cost.')
replace('2770','The HTTP method, which tells a developer that an operation is safe or destructive, gets lost.','The model-facing tool definition may omit the HTTP method, although the generated implementation still needs that method to call the API. An HTTP method alone is also not enough to express the operation\'s business risk.')
after('2770','The confirmation code forces the summary step',[
    'Treat the code as a binding between the previewed parameters and the submitted write. It does not establish who approved the write. A production workflow records approval in trusted host or server code and binds it to the authenticated user, ticket, resolution and an expiry. A model must not be able to approve its own request by echoing the code.',
    'Regeneration should run the same contract checks as a hand-written change: list the exposed tools, compare their schemas, reject newly exposed admin routes, and exercise pagination and errors. Review a diff of the generated tool catalog whenever the OpenAPI document or converter version changes.'
])

# Gateways: separate optional infrastructure from required controls.
replace('3041','so a provider outage does not stop the app.','which can keep the app available during some provider failures. Fallback still depends on a healthy compatible provider and the application\'s data-handling policy.')
replace('3041','so AI gateways limit tokens per minute instead of requests,','so AI gateways often apply token budgets alongside request and concurrency limits,')
replace('3041','We need both when we run agents in production.','We may need both roles when a production platform has model-governance and tool-governance requirements.')
replace('3041','A production agent platform runs both in most cases.','A production agent platform can implement those roles in one product, separate services, or application code, according to its scale and requirements.')
replace('3041','so prompts and keys stay in our network and we operate the service.','so we control the gateway deployment and operate the service. Prompts still leave our network when the selected model provider is external.')
after('3041','Before we pick a product, we decide',[
    'Give each boundary its own credential and audit identity. A request passing through two gateways should remain traceable to the same user and operation, but the model provider and each MCP server should receive only the credential intended for them. Do not use a correlation ID as proof of identity.',
    'Fallback needs a clear stopping point. After partial streamed output or a tool action, starting another provider can duplicate work or change the answer midstream. Define which failures are retryable, whether another provider may receive the prompt, and how the client recognizes a failed or incomplete attempt.'
])

# CLI comparison: execution permissions are deployment choices on both sides.
replace('3045','because every program on the <em>PATH</em> is reachable through that one tool.','because an allowed program on the <em>PATH</em> can be invoked through the shell tool. The agent\'s sandbox and permission policy can restrict which programs and paths are reachable.')
replace('3045','The model never sees the token,','A well-designed host keeps the token out of model context,')
replace('3045','A command that the agent runs has the same rights as the user who started the agent,','Unless it runs under a narrower service account or sandbox, a command inherits the rights of the user who started the agent,')
replace('3045','A CLI gives an agent a cheap, composable interface that the model often knows already, and it runs with the full rights of the user on a machine with a shell.','A familiar CLI gives a shell-based agent a composable interface with on-demand help. Its actual rights come from the execution account, credentials and sandbox.')
after('3045','Both ways need a rule that lets',[
    'Structured arguments make a permission rule easier to target, but they do not make its implementation correct. An MCP tool named <em>get_order</em> can still perform a write, and a CLI can use a dedicated read-only credential. Review the operation behind either interface and enforce its permissions at the service.',
    'Compare the full task with the same data and output fields. Count definitions or help that the host actually sends, the tool results, retries, and any generated filtering code. A single result-size measurement is useful for tuning this example, but it does not establish that one protocol is always cheaper.'
])

# Security: describe trust boundaries rather than attributing unconditional trust to a model.
replace('3064','and the model trusts every piece of text in its context.','and the model may encounter instructions embedded in untrusted text. These boundaries need separate controls; a valid access token does not make a tool result or description trustworthy.')
replace('3064','An LLM cannot reliably tell instructions from data.','An LLM can mistake instructions embedded in data for instructions it should follow.')
replace('3064','which stops rug pulls.','which detects a changed definition relative to the approved baseline. It does not detect a compromised implementation whose definition stays unchanged.')
replace('3064','which stops web pages.','which rejects browser requests with an unapproved origin. It is not a replacement for authentication or an outbound network policy.')
replace('3064','The client guard works with any Streamable HTTP server,','The demo client guard speaks the request format used by this example; adapt authentication, protocol-version support and pagination before using it with another Streamable HTTP server,')
after('3064','The hash check catches the rug pull',[
    'The first pin is a trust decision. Fetch the catalog from the intended endpoint, review the definitions, and store the approved hashes where the server cannot rewrite them. Re-pinning an unexpected catalog automatically would approve the change that the check was meant to stop.',
    'Keep approval separate from scope. A token with <em>orders:write</em> says which operations the caller may attempt; it does not prove that the user approved this particular checkout. Verify the target, amount and recipient in a trusted confirmation flow, then authorize the exact action before execution.'
])

# ACP: interoperability is subject to versions and negotiated capabilities.
replace('3059','so an ACP agent can run in any ACP editor.','so compatible editors and agents can work together without a separate integration for each pair.')
replace('3059','Before an action that changes something, the agent calls <em>session/request_permission</em>','When the agent\'s permission policy requires approval, it calls <em>session/request_permission</em>')
replace('3059','Permission prompts protect the user only when the agent uses the editor\'s file and terminal methods, because the protocol does not stop an agent that writes to disk by itself.','Permission prompts depend on the agent honoring the result and its execution policy. ACP does not sandbox the process or stop it from writing to disk directly, so the process still needs appropriate OS-level restrictions.')
replace('3059','The Agent Client Protocol lets any ACP editor run any ACP agent.','The Agent Client Protocol gives compatible editors and coding agents a shared integration contract.')
after('3059','When we run without --yes and type reject',[
    'A rejection must leave the proposed change unapplied. A real agent should report the refused operation clearly and continue only with work the user still authorized. Granting a reusable permission also needs a defined scope; an approval for one file should not silently authorize every later command.',
    'The timeout-editing helper illustrates the protocol, not a general Python refactoring engine. Regular expressions do not understand every multiline call, alias or existing timeout expression. For a production editor agent, use syntax-aware edits and run the project\'s checks before presenting the resulting diff.'
])

# Apps: a UI click still passes through host authorization.
replace('3038','The model reads the text, and the view renders the list.','The text provides a readable fallback, while the view renders the list. A host may also expose structured data to the model; do not assume that only the text is visible to it.')
replace('3038','The view needs no SDK, although','The wire messages can be implemented without an SDK, although')
replace('3038','A real host runs a model that decides when to call the tool,','A typical AI host lets a model request the initial tool,')
after('3038','The test host enforces the visibility rule',[
    'Visibility controls which interface may invoke the tool. It does not authorize a stock change for a particular user. The server must check the caller\'s warehouse permissions and validate the requested quantity even when the call came from a button in an approved view.',
    'Keep credentials outside the HTML resource. The host mediates tool calls, so the view should request an operation through the bridge rather than receive a bearer token or provider API key. Treat a model-generated argument, a tool result and a message from the iframe as separate untrusted inputs.'
])

# OAuth: permissions are not action-specific consent, and discovery is not automatic trust.
replace('2780','We need MCP server authorization whenever an MCP server runs on a public or company URL,','We need access control when a remote MCP server exposes protected data or actions,')
replace('2780','The client needs only the MCP server URL. Everything else comes from two metadata documents that it discovers after the first failed request.','Discovery can start from the MCP server URL and two metadata documents. The client still needs a registration mechanism, a supported authorization flow and a policy for deciding which authorization servers it trusts.')
replace('2780','and the user approves or denies the cancel there.','and the user approves or denies the extra permission there. That consent grants a scope; it is not necessarily approval for one exact order cancellation.')
replace('2780','so our server code needs no change.','so discovery can still work. Treat this as a documented SDK behavior rather than a reason to copy the challenge unchanged into a hand-written implementation.')
after('2780','The client handled both challenges without',[
    'This demonstration authorization server signs in the same test user and automatically grants consent. The successful retry proves that discovery, PKCE, token validation and scope escalation can connect. It does not test a real login screen, user denial, account switching or an approval gate for a specific order.',
    'Before deployment, test those user flows and key rotation with the actual authorization server. Redact authorization codes and bearer tokens from request logs, and distinguish a failed login from a valid token that lacks permission. Bind any action-specific approval to the user and order in trusted application code.'
])

# OpenAI APIs: typed output and tool behavior matter as much as stored state.
replace('3062','and the main difference is who keeps the conversation.','and they differ in their request and response model, tool support and options for carrying conversation state.')
replace('3062','<em>developer</em> (called <em>system</em> in older code)','<em>developer</em> or <em>system</em> for application guidance, according to the selected model')
replace('3062','The text sits three levels deep, in <em>output[0].content[0].text</em>.','In this response, the text is in <em>output[0].content[0].text</em>. Do not assume that position for every response: tool and reasoning items may appear before a message.')
replace('3062','The Responses API runs some tools on OpenAI\'s side.','The Responses API includes tools managed by OpenAI and integrations with tools that run elsewhere.')
replace('3062','and the model calls it inside the same request without a round trip to our code.','and supported hosted tools can run during that request. Custom functions and tools executed in our environment still require our application to perform the action and return its result.')
replace('3062','so a team that must not keep prompts on the provider\'s side sets <em>store</em> to <em>false</em> in both APIs.','so set <em>store</em> explicitly according to the application\'s needs. Disabling application-state storage is not the same as eliminating all provider retention; review the organization\'s data controls and abuse-monitoring policy separately.')
after('3062','The token numbers are word counts from the stub',[
    'The stub exercises request shapes and client logic. It does not reproduce model reasoning, real tokenization, retention enforcement or tool-selection quality. Keep this deterministic check, then run a small representative evaluation against the chosen model before migrating a user flow.',
    'In that evaluation, check ordinary answers, several tool calls, a refused request, incomplete output and a failed tool. Compare task success and application behavior rather than expecting identical wording from the two endpoints. Carry forward every item needed to continue a manually managed reasoning or tool-calling exchange.'
])

# Compatibility is a tested subset, not a promise about every OpenAI feature.
replace('3046','so any OpenAI SDK or tool can call it after we change the base URL, the API key and the model name.','so clients using the implemented endpoints and fields can call it after changing the base URL, API key and model name. Compatibility is a claim about a subset of the API, not every OpenAI feature.')
replace('3046','so switching them to another server needs no code change.','so they can pick up another server through configuration when their required endpoints and fields are supported.')
replace('3046','A server that returns HTTP 200 with an error object in the body breaks every client.','A server that returns HTTP 200 with an error object can bypass the SDK\'s HTTP error handling and break code that expects a normal completion.')
replace('3046','Most compatibility problems return HTTP 200, so the differences show up only in the results.','Some compatibility problems return HTTP 200, so checking the status alone does not establish that a requested feature worked.')
after('3046','Each check calls the server through the SDK',[
    'Run the checker with the same model, SDK version and request options that the application will use. A passing text request does not test strict JSON, parallel tool calls, images, reasoning settings or streaming cancellation. Add focused cases for each feature your application depends on.',
    'Keep a separate assertion for each result contract. For tools, check the name, argument JSON and matching call IDs. For structured output, validate the schema and values. For streams, accept empty <em>choices</em> arrays on usage chunks and distinguish a finished answer from a disconnected stream.'
])

# Primitives: the host mediates the control model; templates have their own catalog.
replace('3051','The model decides when to call a tool, the host app (the AI application the user works in) decides which resources to read, and the user decides when to run a prompt.','Their intended control models are model-selected tools, application-managed resources and user-selected prompts. The host app, the AI application the user works in, mediates all three and chooses how to expose them.')
replace('3051','The model does not read a resource by itself,','The model does not open the resource connection itself,')
replace('3051','Every extra tool definition also costs context tokens on every model call.','Every extra tool definition included in a model request uses context tokens. A host can reduce that cost by selecting tools or loading definitions on demand.')
after('3051','A lookup where the model picks the key',[
    'The same policy document can support all three primitives without duplicating the business rule. Expose it as a resource, include or link it from a prompt, and let a read tool return its URI when the model needs to discover it. Keep one authoritative policy source so the views do not disagree after an update.',
    'Test the catalogs separately. A connected client that lists only <em>resources/list</em> will not discover URI templates; it also needs <em>resources/templates/list</em>. Likewise, a prompt being listed does not mean the host has run it or that its suggested tools were invoked.'
])

# Tasks: protocol handles need application durability and independent cancellation policy.
replace('3060','With tasks, the first request returns within milliseconds with a <em>taskId</em>,','With tasks, the first request can return promptly with a <em>taskId</em>,')
replace('3060','so every client that declares the extension handles every server the same way.','so compatible clients have a common way to interpret a job handle and its lifecycle. Authorization, storage and the work itself remain application responsibilities.')
after('3060','The task ids and timestamps change on every run',[
    'The demo keeps task records in memory. A client can reconnect while that server process is alive, but restarting the process loses those records. For crash recovery, persist the task and its ownership before acknowledging creation, and execute the work in a durable job system.',
    'Persisting a handle does not prevent duplicate jobs when the creation response is lost. Deduplicate job creation using an application-level operation identifier, and check an existing job before starting another export. Cancellation is also a request, not proof that the job stopped; read the final status before reporting cancellation as complete.'
])

# A2A: an opaque agent can still disclose data through its messages and artifacts.
replace('3066','which also checks that the agent follows the specification.','which parses the example responses using the SDK\'s protocol types. That is useful interoperability coverage, not a complete conformance test.')
replace('3066','which keeps the policy rules and data inside the finance team.','which keeps the implementation behind that team\'s boundary. Messages and artifacts can still expose policy or customer data, so the finance agent must authorize what it returns.')
replace('3066','The following example is the first step of every A2A conversation.','The following example shows discovery when the client starts without a cached Agent Card.')
after('3066','For a real agent, use the server side',[
    'Bind each task and artifact to the authenticated caller. A task ID groups work; it is not a credential. Apply the same access checks when a client polls, continues a task, subscribes to events or downloads the result, and validate any webhook destination before making outbound requests.',
    'Treat the remote agent\'s result as data from another system. A completed task means the remote workflow finished, not that its conclusion is factually correct or authorized for every downstream use. Validate the returned fields and keep local approval rules before acting on a recommendation that moves money or changes records.'
])

# Skills: executable content can access APIs; the format does not confer credentials or enforcement.
replace('3020','No script in the folder runs until a step tells the agent to run it, and the skill has no server, no port and no credentials of its own.','The skill format does not itself start a service or execute a script. The host controls activation and execution, and a script runs with the credentials and permissions available in that environment.')
replace('3020','A skill cannot return the status of an invoice, because a skill has no credentials and no connection of its own.','A skill can instruct the agent to run a script or call an existing API tool. It does not itself provide the standardized service connection, live tool catalog or authorization boundary that an MCP server provides.')
replace('3020','A skill alone cannot read the invoice or move money, because both need the billing system.','Instructions alone cannot read an invoice or move money; the agent also needs an authorized execution path to the billing system. That path could be an MCP tool, a CLI or a script that calls the API.')
replace('3020','An MCP server alone can issue any refund,','An MCP server can expose an authorized refund operation,')
replace('3020','The skill\'s approval rule stops the agent before the MCP tool that moves money.','The scripted demo follows the skill\'s approval rule and stops before the tool that moves money. A real deployment must enforce that gate in trusted code, because instructions alone cannot guarantee that an agent will stop.')
after('3020','A skill served by an MCP server is untrusted content',[
    'Fetching a remote <em>SKILL.md</em> is not the same as activating it. The host must route it through its skill-loading process, verify the listed files and apply its trust or approval policy before placing the instructions in model context. A server connection should not silently enable every workflow the server offers.',
    'Keep business authorization at the billing service. A skill can explain the refund policy and an MCP tool can calculate or submit the refund, but neither should let the model override the customer\'s permissions. Bind approval for a high-value refund to the invoice, amount and authenticated user outside the skill text.'
])

# Cross-article editorial pass: put the first explanation under a heading, remove roadmaps.
roadmaps={
 '3076':['We follow a connection in the order'],
 '3063':['Notice that the links end in'],
 '3010':['We go through both transports'],
 '2770':['We map every OpenAPI field'],
 '3041':[],
 '3045':[],
 '3064':['In this article, we cover'],
 '3059':[],
 '3038':[],
 '2780':['The sections that follow explain'],
 '3062':['We cover how each API works'],
 '3060':[],
 '3066':['We cover how discovery'],
 '3051':[],
 '3020':['We start with what a skill is'],
 '3046':['We cover what "compatible" includes']
}
for post,raw in list(texts.items()):
    h=re.search(r'<!-- wp:heading(?:\s[^>]*)?-->.*?<!-- /wp:heading -->',raw,re.S)
    assert h
    intro=raw[:h.start()]; rest=raw[h.end():]
    for prefix in roadmaps[post]:
        def trim(m):
            return '' if BeautifulSoup(m.group(),'html.parser').get_text(' ',strip=True).startswith(prefix) else m.group()
        intro=re.sub(r'<!-- wp:paragraph[^>]*-->.*?<!-- /wp:paragraph -->',trim,intro,flags=re.S)
    # Intro roadmap lists are editorial scaffolding; the numbered headings provide navigation.
    intro=re.sub(r'<!-- wp:list\b.*?<!-- /wp:list -->','',intro,flags=re.S)
    paragraphs=list(re.finditer(r'<!-- wp:paragraph[^>]*-->.*?<!-- /wp:paragraph -->',intro,re.S))
    assert len(paragraphs)>=2
    cut=paragraphs[1].end()
    texts[post]=intro[:cut]+'\n\n'+h.group()+'\n\n'+intro[cut:].strip()+'\n\n'+rest.lstrip()
    changes[post].append({'structure':'First H2 moved after short introduction; redundant roadmap removed. Code and subsequent section order retained.'})
    # Keep sectional cross-references consistent without altering code or anchors.
    parts=re.split(r'(<pre\b.*?</pre>)',texts[post],flags=re.S)
    texts[post]=''.join(re.sub(r'\bsection (?=\d)','Section ',p) if i%2==0 else p for i,p in enumerate(parts))

for post,raw in texts.items():
    original=(ROOT/'originals'/(post+'.wp.html')).read_text(encoding='utf-8')
    assert re.findall(r'<pre\b.*?</pre>',original,re.S)==re.findall(r'<pre\b.*?</pre>',raw,re.S),post
    assert re.findall(r'<h[23]\b.*?</h[23]>',original,re.S)==re.findall(r'<h[23]\b.*?</h[23]>',raw,re.S),post
    assert re.findall(r'<img\b[^>]*>',original)==re.findall(r'<img\b[^>]*>',raw),post
    # Never carry author-facing prompts into review article bodies.
    raw,n=re.subn(r'<!-- wp:paragraph[^>]*-->\s*<p>Lokesh:.*?</p>\s*<!-- /wp:paragraph -->','',raw,flags=re.S)
    if n: changes[post].append({'removed_editorial_requests':n})
    (OUT/(post+'.wp.html')).write_text(raw,encoding='utf-8')
    (OUT/(post+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),raw.splitlines(True),fromfile='WordPress draft',tofile='review article')),encoding='utf-8')
    print(post,len(changes[post]),'changes; code, headings and images retained')
(ROOT/'changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
