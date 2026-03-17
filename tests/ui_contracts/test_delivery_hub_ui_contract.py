"""Contract checks for Build and Release secondary hub navigation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "templates/index.html"
SHARED_JS = ROOT / "static/js/components/shared/delivery-hub-shared.js"
BACKLOG_JS = ROOT / "static/js/views/delivery/backlog.js"
INTEGRATION_JS = ROOT / "static/js/views/integration/integration.js"
DATA_FACTORY_JS = ROOT / "static/js/views/testing/data_factory.js"
CUTOVER_JS = ROOT / "static/js/views/operations/cutover.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_template_loads_delivery_hub_shared_component():
    src = _read(INDEX_HTML)
    assert '/static/js/components/shared/delivery-hub-shared.js' in src


def test_shared_component_exposes_build_and_release_navs():
    src = _read(SHARED_JS)
    assert "testId: 'build-hub-nav'" in src
    assert "testId: 'release-hub-nav'" in src
    assert "id: 'backlog'" in src
    assert "id: 'integration'" in src
    assert "id: 'data-factory'" in src
    assert "id: 'cutover'" in src
    assert "data-delivery-view" in src


def test_build_and_release_views_render_secondary_hub_navigation():
    backlog_src = _read(BACKLOG_JS)
    integration_src = _read(INTEGRATION_JS)
    data_factory_src = _read(DATA_FACTORY_JS)
    cutover_src = _read(CUTOVER_JS)

    assert "DeliveryHubUI.nav('build', 'backlog')" in backlog_src
    assert "DeliveryHubUI.nav('build', 'integration')" in integration_src
    assert "DeliveryHubUI.nav('build', 'data-factory')" in data_factory_src
    assert "DeliveryHubUI.nav('release', 'cutover')" in cutover_src
