"""Replaceable boundaries; unconfigured integrations never report simulated success."""
from typing import Protocol


class UnavailableIntegration(RuntimeError):
    pass


class WritingProvider(Protocol):
    def propose(self, channel: dict, topic_history: list[str]) -> dict: ...


class AssetProvider(Protocol):
    def search(self, scene: dict) -> list[dict]: ...


class PublishingProvider(Protocol):
    def capabilities(self, brand: str) -> dict: ...
    def lookup(self, idempotency_key: str) -> dict: ...
    def submit(self, draft: dict, authorization: dict) -> dict: ...


class UnconnectedWriter:
    def propose(self, channel, topic_history):
        raise UnavailableIntegration("No model API connected. Save assistant-prepared jobs in pilots/ or provide an approved adapter.")


class UnconnectedStock:
    def search(self, scene):
        raise UnavailableIntegration("Stock search not connected. Use original diagrams or supply licensed assets with provenance.")


class DraftPublisher:
    def capabilities(self, brand):
        return {"mode":"draft_only","connected":False,"brand":brand,"scheduling":False,"analytics":False}
    def lookup(self, idempotency_key):
        raise UnavailableIntegration("No provider connection; cannot resolve an uncertain remote upload")
    def submit(self, draft, authorization):
        raise UnavailableIntegration("Live transport disabled; connect a supported provider and record explicit publishing scope")
