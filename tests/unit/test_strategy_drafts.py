from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from options_analysis.domain import (
    AssetType,
    StrategyDraftDefinition,
    StrategyDraftLeg,
)
from options_analysis.services import StrategyDraftService
from options_analysis.storage import SQLiteStrategyDraftRepository


def definition(
    name: str = "SPY income",
    *,
    quantity: str = "-1",
) -> StrategyDraftDefinition:
    return StrategyDraftDefinition(
        name=name,
        underlying_symbol="spy",
        provider_id="fake",
        strategy_template_id="cash_secured_put",
        legs=(
            StrategyDraftLeg(
                symbol="SPY300118P00095000",
                provider_symbol="SPY300118P00095000",
                asset_type=AssetType.OPTION,
                quantity=Decimal(quantity),
                average_open_price=Decimal("2"),
            ),
        ),
    )


def service(path: Path) -> StrategyDraftService:
    return StrategyDraftService(SQLiteStrategyDraftRepository(path))


def test_save_upserts_by_name_and_persists_across_service_instances(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    drafts = service(database)

    first = drafts.save(definition())
    updated = drafts.save(definition("spy INCOME", quantity="-2"))
    restarted = service(database).list_drafts()

    assert updated.draft_id == first.draft_id
    assert updated.created_at == first.created_at
    assert updated.name == "spy INCOME"
    assert updated.legs[0].quantity == -2
    assert restarted == (updated,)
    assert database.stat().st_mode & 0o077 == 0


def test_remove_is_idempotent(tmp_path: Path) -> None:
    drafts = service(tmp_path / "state.sqlite3")
    saved = drafts.save(definition())

    assert drafts.remove(saved.draft_id) == ()
    assert drafts.remove(saved.draft_id) == ()


def test_draft_definition_rejects_empty_legs_and_zero_quantity() -> None:
    with pytest.raises(ValidationError, match="at least 1 item"):
        StrategyDraftDefinition(
            name="Empty",
            underlying_symbol="SPY",
            provider_id="fake",
            legs=(),
        )
    with pytest.raises(ValidationError, match="quantity must be nonzero"):
        definition(quantity="0")
