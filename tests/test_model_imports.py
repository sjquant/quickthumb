import importlib

import pytest
import quickthumb.models as models


@pytest.mark.parametrize(
    ("module_name", "symbol"),
    [
        ("common", "Align"),
        ("layers", "TextLayer"),
        ("effects", "Stroke"),
        ("motion", "AnimationSpec"),
        ("visualizations", "BarChartSpec"),
        ("inspection", "CanvasInspection"),
        ("options", "GifOptions"),
        ("document", "CanvasModel"),
    ],
)
def test_should_preserve_model_imports_across_domain_modules(module_name, symbol):
    """Domain modules expose the same model objects as the compatibility package."""
    # given: a model symbol exposed by the migrated package
    module = importlib.import_module(f"quickthumb.models.{module_name}")

    # when: the symbol is resolved through its domain module and compatibility path
    domain_symbol = getattr(module, symbol)
    compatibility_symbol = getattr(models, symbol)

    # then: both paths resolve to the identical model object
    assert domain_symbol is compatibility_symbol


def test_should_keep_existing_quickthumb_models_symbols_available():
    """The package-level model namespace retains the established public symbols."""
    # given: representative symbols consumed by existing runtime modules
    expected = ["TextLayer", "AnimationSpec", "CanvasModel", "LayerType"]

    # when: symbols are resolved from quickthumb.models
    resolved = [getattr(models, symbol) for symbol in expected]

    # then: every established symbol remains available after the file-to-package migration
    assert resolved == [
        models.TextLayer,
        models.AnimationSpec,
        models.CanvasModel,
        models.LayerType,
    ]
