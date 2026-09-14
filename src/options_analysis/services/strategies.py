"""Provider-neutral option-strategy template catalog."""

from decimal import Decimal

from options_analysis.domain import AssetType, PutCall
from options_analysis.domain.strategies import (
    StrategyAction,
    StrategyLegRole,
    StrategyOutlook,
    StrategyTemplate,
)

_TEMPLATES = (
    StrategyTemplate(
        template_id="long_call",
        display_name="Long call",
        description="Buy one call for defined downside and bullish exposure.",
        outlook=StrategyOutlook.BULLISH,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Long call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=0,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="long_put",
        display_name="Long put",
        description="Buy one put for defined downside and bearish exposure.",
        outlook=StrategyOutlook.BEARISH,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Long put",
                asset_type=AssetType.OPTION,
                put_call=PutCall.PUT,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=0,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="covered_call",
        display_name="Covered call",
        description="Own 100 shares and sell one call against them.",
        outlook=StrategyOutlook.NEUTRAL,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Long shares",
                asset_type=AssetType.EQUITY,
                action=StrategyAction.BUY,
                ratio=Decimal("100"),
            ),
            StrategyLegRole(
                label="Short call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.SELL,
                ratio=Decimal("1"),
                strike_order=0,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="bull_call_spread",
        display_name="Bull call spread",
        description="Buy a lower-strike call and sell a higher-strike call.",
        outlook=StrategyOutlook.BULLISH,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Long lower call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=0,
            ),
            StrategyLegRole(
                label="Short higher call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.SELL,
                ratio=Decimal("1"),
                strike_order=1,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="bear_put_spread",
        display_name="Bear put spread",
        description="Sell a lower-strike put and buy a higher-strike put.",
        outlook=StrategyOutlook.BEARISH,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Short lower put",
                asset_type=AssetType.OPTION,
                put_call=PutCall.PUT,
                action=StrategyAction.SELL,
                ratio=Decimal("1"),
                strike_order=0,
            ),
            StrategyLegRole(
                label="Long higher put",
                asset_type=AssetType.OPTION,
                put_call=PutCall.PUT,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=1,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="long_call_butterfly",
        display_name="Long call butterfly",
        description="Buy the wings and sell two calls at the middle strike.",
        outlook=StrategyOutlook.NEUTRAL,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Long lower call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=0,
            ),
            StrategyLegRole(
                label="Short two middle calls",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.SELL,
                ratio=Decimal("2"),
                strike_order=1,
            ),
            StrategyLegRole(
                label="Long higher call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=2,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="iron_condor",
        display_name="Iron condor",
        description="Buy outer wings and sell inner put and call strikes.",
        outlook=StrategyOutlook.NEUTRAL,
        same_expiration=True,
        legs=(
            StrategyLegRole(
                label="Long lower put",
                asset_type=AssetType.OPTION,
                put_call=PutCall.PUT,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=0,
            ),
            StrategyLegRole(
                label="Short higher put",
                asset_type=AssetType.OPTION,
                put_call=PutCall.PUT,
                action=StrategyAction.SELL,
                ratio=Decimal("1"),
                strike_order=1,
            ),
            StrategyLegRole(
                label="Short lower call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.SELL,
                ratio=Decimal("1"),
                strike_order=2,
            ),
            StrategyLegRole(
                label="Long higher call",
                asset_type=AssetType.OPTION,
                put_call=PutCall.CALL,
                action=StrategyAction.BUY,
                ratio=Decimal("1"),
                strike_order=3,
            ),
        ),
    ),
    StrategyTemplate(
        template_id="custom",
        display_name="Custom",
        description="Select and edit arbitrary same-underlying legs.",
        outlook=StrategyOutlook.CUSTOM,
        same_expiration=False,
        legs=(),
    ),
)


class StrategyCatalogService:
    def list_templates(self) -> tuple[StrategyTemplate, ...]:
        return _TEMPLATES
