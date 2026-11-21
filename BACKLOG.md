# Remaining work

Implementation status and checks are maintained in [docs/CURRENT.md](docs/CURRENT.md). Select work according to the user's current request.

| Area | Remaining task |
| --- | --- |
| Site access | Diagnose the observed owner-check 403 using configured ownership and authenticated identity |
| Live publishing | Verify matching backend deployment/settings, provider consent, media import and draft retrieval through the deployed Site |
| Account registry | Register exact Instagram, Facebook and TikTok IDs before publishing to those aliases |
| More channels | Replace the Site's fixed Ifverse target map with a deliberate multi-destination configuration if requested; backend registry support already exists |
| Media planning | Improve automatic story-to-footage matching while keeping concrete shot reasons and reviewed inputs |
| Hollywood | Generalize the anime-only review runner and validate Hollywood branding |
| Recovery | Verify durable private-state backup/restore and deployment recovery on the intended host |
| Analytics | Add provider metrics when requested; no general analytics integration is established |

The OAuth-to-publisher bridge, basic uploader, source cache, narrator and captions already exist. Reuse them. Historical science pilots, optional Kaggle/n8n work and seven-account rollout are background rather than the active roadmap.
