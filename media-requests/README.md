# Agent requests

Commit exactly one unique JSON request per commit on the branch configured by .github/workflows/media-tools.yml. Use examples/media-request.json as the schema. That push triggers the on-demand self-hosted workflow if an online matching runner is available. Reconcile the existing request/run/result before retrying. Do not include credentials, cookies, shell commands or private narration in requests.

No production request was submitted when the tools were created. The example lives outside this directory to avoid starting a job merely by saving the implementation.
