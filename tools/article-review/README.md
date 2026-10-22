# Article review tooling

These scripts prepare local editorial review copies for restfulapi.net. They do not save to WordPress.

Article data and exports: C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\ai-drafts-review
Canonical example source: C:\Users\lokes\IdeaProjects\restfulapi-examples

Run prepare_articles.py to build edits from backed-up originals, then build_review_pack.py to produce HTML, Markdown, WordPress-ready source and the ZIP. These scripts currently contain the local review-data path. Install verification-requirements.txt in an isolated environment as needed. verify_projects.py executes local example checks and may regenerate example output files; inspect the repository diff afterward. check_links.py checks outgoing article links. inspect_assets.py makes internal image contact sheets without WordPress post numbers.

Review logs distinguish fresh checks from historical article output. See review-notes.md in the article data directory for limitations and dependency discrepancies.
