# Operation routes

Use [START_HERE.md](../START_HERE.md) and [CURRENT.md](CURRENT.md) to select the current source and task.

| Route | Guide | State |
| --- | --- | --- |
| Finite anime production | [AUTOMATION.md](AUTOMATION.md), [MEDIA-TOOLS.md](MEDIA-TOOLS.md) | Request/result commits, source/model caches and saved render receipts |
| ChatGPT Site and publisher | [ACCOUNT_LINKING.md](../sites/ACCOUNT_LINKING.md), [CHATGPT_PUBLISHING.md](CHATGPT_PUBLISHING.md) | Site OAuth database plus backend private media/draft/receipt volume |
| Standalone GitHub/desktop publisher | [SOCIAL_PUBLISHING.md](SOCIAL_PUBLISHING.md) | Separate credentials, queue and delivery receipts |
| Legacy prepared-pilot worker | Commands below | Application SQLite/media and optional n8n volumes |

Use one publishing route for an account/episode. The routes do not automatically synchronize credentials or uncertain delivery state.

## Legacy worker and n8n

The original science-fixture pipeline remains available for development and recovery. It is separate from the current anime review renderer and hosted publisher.

```sh
python -m whatif --help
python -m whatif status
```

Inspect or restore the authoritative application store before a command that initializes a new one. The legacy worker uses SQLite leases, content hashes and stage checkpoints; `quality_review` requires actual review before delivery. Detailed fixture inputs are in `pilots/` and the [archived prototype README](archive/README_BEFORE_START_GUIDE.md).

n8n is optional. Its database and encryption key are separate from the application store. Use [BACKUP.md](BACKUP.md) for that backup contract. The current finite GitHub media workflow does not require an always-on personal computer or n8n instance.
