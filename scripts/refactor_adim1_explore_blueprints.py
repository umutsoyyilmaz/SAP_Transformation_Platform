from pathlib import Path
import re

ROOT = Path("/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main")
BLUEPRINTS = {
    "workshops": ROOT / "app/blueprints/explore/workshops.py",
    "process_levels": ROOT / "app/blueprints/explore/process_levels.py",
    "requirements": ROOT / "app/blueprints/explore/requirements.py",
}
LEGACY_DIR = ROOT / "app/services/explore_legacy"
SERVICE_FILE = ROOT / "app/services/explore_service.py"


DISPATCH_TEMPLATE = '''

def dispatch_{name}_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch {name} blueprint endpoints to legacy implementations.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the legacy handler.
    """
    from app.services.explore_legacy import {name}_legacy

    route_params = route_params or {{}}
    query_params = query_params or {{}}
    data = data or {{}}

    logger.info(
        "Dispatching {name} endpoint=%s route_keys=%s query_keys=%s has_data=%s",
        endpoint,
        sorted(route_params.keys()),
        sorted(query_params.keys()),
        bool(data),
    )

    handler = getattr({name}_legacy, endpoint, None)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)
'''


def _strip_decorators_for_legacy(text: str) -> str:
    text = re.sub(r"^from app\.blueprints\.explore import explore_bp\n", "", text, flags=re.M)
    text = re.sub(r"^@explore_bp\.route\([^\n]*\)\n", "", text, flags=re.M)
    return text


def _extract_routes(text: str):
    lines = text.splitlines()
    routes = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("@explore_bp.route("):
            decorator = lines[i]
            j = i + 1
            extra_decorators = []
            while j < len(lines) and lines[j].startswith("@") and not lines[j].startswith("@explore_bp.route("):
                extra_decorators.append(lines[j])
                j += 1
            if j < len(lines) and lines[j].startswith("def "):
                def_line = lines[j]
                m = re.match(r"def\s+(\w+)\((.*?)\):", def_line)
                if m:
                    fn_name = m.group(1)
                    params = [
                        p.strip().split(":")[0].split("=")[0].strip()
                        for p in m.group(2).split(",")
                        if p.strip()
                    ]
                    routes.append((decorator, extra_decorators, def_line, fn_name, params))
                i = j
        i += 1
    return routes


def _generate_wrapper_module(module_name: str, routes) -> str:
    out = []
    out.append('"""Explore blueprint wrappers delegating ORM work to service layer."""')
    out.append("")
    out.append("from flask import request")
    out.append("")
    out.append("from app.blueprints.explore import explore_bp")
    out.append("from app.services import explore_service")
    out.append("")

    for decorator, extra_decorators, def_line, fn_name, params in routes:
        out.append(decorator)
        out.extend(extra_decorators)
        out.append(def_line)
        out.append('    """Delegate endpoint logic to explore_service while keeping blueprint thin."""')
        out.append("    data = request.get_json(silent=True) or {}")
        out.append("    query_params = request.args.to_dict(flat=True)")
        if params:
            route_params = ", ".join([f'\"{p}\": {p}' for p in params])
            out.append(f"    route_params = {{{route_params}}}")
        else:
            out.append("    route_params = {}")
        out.append(f'    return explore_service.dispatch_{module_name}_endpoint(')
        out.append(f'        endpoint="{fn_name}",')
        out.append("        route_params=route_params,")
        out.append("        query_params=query_params,")
        out.append("        data=data,")
        out.append("    )")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _ensure_legacy_package() -> None:
    LEGACY_DIR.mkdir(parents=True, exist_ok=True)
    init_file = LEGACY_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Legacy Explore handlers moved from blueprints for ADIM 1."""\n')


def _extend_service_dispatchers() -> None:
    service_text = SERVICE_FILE.read_text()
    marker = "\n# ADIM 1 explore blueprint dispatchers\n"
    if marker in service_text:
        service_text = service_text.split(marker)[0].rstrip() + "\n"

    addition = [marker]
    for name in BLUEPRINTS.keys():
        addition.append(DISPATCH_TEMPLATE.format(name=name))

    SERVICE_FILE.write_text(service_text + "\n".join(addition))


def main() -> None:
    _ensure_legacy_package()

    for module_name, path in BLUEPRINTS.items():
        original = path.read_text()
        legacy = _strip_decorators_for_legacy(original)
        (LEGACY_DIR / f"{module_name}_legacy.py").write_text(legacy)

        routes = _extract_routes(original)
        wrapper = _generate_wrapper_module(module_name, routes)
        path.write_text(wrapper)

    _extend_service_dispatchers()


if __name__ == "__main__":
    main()
