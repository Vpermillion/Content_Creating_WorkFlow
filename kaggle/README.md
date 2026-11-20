# Finite speech generation on Kaggle

**Optional legacy route:** the notebook and transfer contract are implemented; a Kaggle run is not established by the saved records. The current anime renderer uses Kokoro on the production runtime without requiring Kaggle. The older science sample uses FFmpeg/libflite. See [CURRENT.md](../docs/CURRENT.md) for active scope.

1. Create new, approved prepared jobs before generating local narration. Export a batch with stable content versions:

   ```sh
   python -m whatif tts-export /private/path/input.json pilot-001 pilot-002 pilot-003
   ```

   An exact manifest is retained in `data/batches/{batch-id}/input.json`. Existing pilot narration must not be silently replaced; use new job versions when switching voices.
2. In your authorized Kaggle account, upload that manifest to a private dataset or use another supported private input route. Mount it in a private notebook at `/kaggle/input/whatif-batch/input.json`. Never upload credentials to a dataset or notebook.
3. Import `finite-tts.ipynb`. Review the pinned package/model/voice licenses and language support. The software repository's Apache license was fetched and saved in `docs/kokoro-license.txt`; model-card and voice rights still require current verification. This template uses built-in `af_heart` English only. It does not support Mongolian by assumption.
4. Enable Internet for dependency/model downloads, choose an available GPU if entitled, then run this **finite** batch. The model loads once. Device, elapsed time, stable IDs, content versions, checksums and exact scene-sample boundaries are saved. CPU is supported by the template but unbenchmarked here. No performance or quota promise is made.
5. Download the completed `tts-output` directory from that exact notebook run. An absent `output.json` means an incomplete batch. Stop the notebook when finished.
6. Import it:

   ```sh
   python -m whatif tts-import /private/path/tts-output
   python -m whatif run JOB_ID
   ```

   The importer validates the complete job set, matching batch and content versions, relative audio names, hashes, WAV durations and contiguous text-matched segment timings before checkpointing speech. It refuses missing/duplicate/wrong-run outputs and existing narration. The hash/manifest contract detects mismatches; it does not prove which remote model generated user-supplied audio.

`kernel-metadata.example.json` is a private notebook submission template with explicit username/dataset placeholders. It has not been submitted. The official Kaggle CLI kernel reference was retrieved on 2026-10-25 and saved in `docs/kaggle-kernels.md`. After secure authentication and metadata replacement, its documented lifecycle is `kaggle kernels push -p DIRECTORY`, `kaggle kernels status USER/SLUG`, then `kaggle kernels output USER/SLUG -p OUTPUT_DIRECTORY`. Do not run push with placeholders or against another user's notebook.

Automated authenticated submission, bounded status polling, exact remote run identity and retrieval remain integration work; the manual handoff avoids claiming these calls succeeded. Future polling should cap attempts/time and back off on quota errors. Preserve queued jobs on unavailable GPU/credentials. Never keep an idle notebook alive as a speech API or automatically purchase fallback compute.

For manual audio without Kaggle, use the same output contract against a locally exported input batch. Supply actual WAV hashes and segment timings derived from audio/alignment. Do not manufacture word timings from character counts.

