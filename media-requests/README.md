# Agent requests

Commit exactly one unique JSON request per commit on the branch configured by .github/workflows/media-tools.yml. Use examples/media-request.json as the schema. That push triggers the on-demand GitHub-hosted workflow with saved caches. Reconcile the existing request/run/result before retrying. Do not include credentials, cookies, shell commands or private narration in requests.

A bounded hosted preview test was subsequently submitted and succeeded; see artifacts/hosted-media-trial-20261027.json. The example lives outside this directory to avoid starting a job merely by saving the implementation.
