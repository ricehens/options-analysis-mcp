from options_analysis.domain import AssetType, PutCall, StrategyAction
from options_analysis.services import StrategyCatalogService


def test_catalog_has_stable_unique_templates_and_leg_roles() -> None:
    templates = StrategyCatalogService().list_templates()
    by_id = {template.template_id: template for template in templates}

    assert len(by_id) == len(templates) == 8
    assert set(by_id) == {
        "bear_put_spread",
        "bull_call_spread",
        "covered_call",
        "custom",
        "iron_condor",
        "long_call",
        "long_call_butterfly",
        "long_put",
    }
    covered = by_id["covered_call"]
    assert covered.legs[0].asset_type is AssetType.EQUITY
    assert covered.legs[0].ratio == 100
    assert covered.legs[1].action is StrategyAction.SELL
    assert covered.legs[1].put_call is PutCall.CALL
    assert [leg.ratio for leg in by_id["long_call_butterfly"].legs] == [1, 2, 1]
