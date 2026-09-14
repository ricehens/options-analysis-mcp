"""Saved-strategy use cases independent of storage and data providers."""

from typing import Protocol
from uuid import UUID

from options_analysis.domain import StrategyDraft, StrategyDraftDefinition


class StrategyDraftRepository(Protocol):
    def initialize(self) -> None: ...

    def list_drafts(self) -> tuple[StrategyDraft, ...]: ...

    def save(self, definition: StrategyDraftDefinition) -> StrategyDraft: ...

    def remove(self, draft_id: UUID) -> bool: ...


class StrategyDraftService:
    def __init__(self, repository: StrategyDraftRepository) -> None:
        self._repository = repository

    def list_drafts(self) -> tuple[StrategyDraft, ...]:
        self._repository.initialize()
        return self._repository.list_drafts()

    def save(self, definition: StrategyDraftDefinition) -> StrategyDraft:
        self._repository.initialize()
        return self._repository.save(definition)

    def remove(self, draft_id: UUID) -> tuple[StrategyDraft, ...]:
        self._repository.initialize()
        self._repository.remove(draft_id)
        return self._repository.list_drafts()
