"""Testing blueprint route registrations for catalog and suite operations."""

from flask import jsonify, request

from .route_helpers import (
    _actor_from_request,
    _compute_snapshot_diff,
    _create_test_case_version,
    _derive_primary_traceability_fields,
    _extract_suite_assignment,
    _normalize_traceability_links,
    _sync_test_case_trace_links,
    _validate_test_case_traceability_scope,
    _validate_traceability_links_scope,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models import db
from app.models.audit import write_audit
from app.models.backlog import BacklogItem, ConfigItem
from app.models.explore import ExploreRequirement
from app.models.program import Program
from app.models.testing import (
    TestCase,
    TestCaseDependency,
    TestCaseSuiteLink,
    TestCaseTraceLink,
    TestCaseVersion,
    TestCycle,
    TestStep,
    TestSuite,
)
from app.services.testing import catalog as catalog_service
from app.services.helpers.project_owned_scope import (
    normalize_member_scope,
    normalize_project_scope,
    resolve_project_scope,
)
from app.services.helpers.scoped_queries import get_scoped
from app.services.scope_resolution import resolve_l3_for_tc, validate_l3_for_layer
from app.utils.helpers import db_commit_or_error


def _normalize_suite_payload(data):
    """Reject removed suite_type input while keeping purpose canonical."""
    payload = dict(data or {})
    purpose = str(payload.get("purpose") or "").strip()
    suite_type = str(payload.get("suite_type") or "").strip()

    if suite_type:
        raise ValueError("suite_type is no longer accepted; use purpose")
    if purpose:
        payload["purpose"] = purpose
    return payload


def register_testing_catalog_routes(
    bp,
    *,
    get_or_404,
    resolved_testing_project_id,
    request_project_id,
):
    """Register catalog, suite, step, and dependency routes on the shared blueprint."""

    @bp.route("/programs/<int:pid>/testing/catalog", methods=["GET"])
    def list_test_cases(pid):
        """List test cases for a program."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            result = catalog_service.list_test_cases(
                pid,
                project_id=resolved_testing_project_id(pid),
                test_layer=request.args.get("test_layer"),
                status=request.args.get("status"),
                module=request.args.get("module"),
                suite_id=request.args.get("suite_id"),
                is_regression=request.args.get("is_regression"),
                explore_requirement_id=request.args.get("explore_requirement_id"),
                search=request.args.get("search"),
                limit=request.args.get("limit"),
                offset=request.args.get("offset"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @bp.route("/programs/<int:pid>/testing/catalog", methods=["POST"])
    def create_test_case(pid):
        """Create a new test case with auto-generated code and L3 scope resolution."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        if not data.get("title"):
            return jsonify({"error": "title is required"}), 400
        if data.get("requirement_id") not in (None, ""):
            return jsonify({"error": "requirement_id is no longer accepted; use explore_requirement_id"}), 400

        try:
            suite_ids = _extract_suite_assignment(data)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            project_id = resolve_project_scope(pid, request_project_id(data))
            if project_id is None:
                raise ValueError("project_id is required")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        normalized_trace_links = _normalize_traceability_links(data.get("traceability_links", []))
        if normalized_trace_links:
            for link in normalized_trace_links:
                resolved = resolve_l3_for_tc(
                    {"process_level_id": link["l3_process_level_id"]},
                    project_id=project_id,
                    program_id=pid,
                )
                if not resolved:
                    return jsonify({
                        "error": f"Invalid L3 process level: {link['l3_process_level_id']}",
                    }), 400
                link["l3_process_level_id"] = resolved

            primary_fields = _derive_primary_traceability_fields(normalized_trace_links)
            data["process_level_id"] = primary_fields["process_level_id"]
            data["explore_requirement_id"] = primary_fields["explore_requirement_id"]
            data["backlog_item_id"] = primary_fields["backlog_item_id"]
            data["config_item_id"] = primary_fields["config_item_id"]

        resolved_l3 = resolve_l3_for_tc(data, project_id=project_id, program_id=pid)
        if resolved_l3:
            data["process_level_id"] = resolved_l3

        try:
            _validate_test_case_traceability_scope(
                data,
                program_id=pid,
                project_id=project_id,
                normalized_links=normalized_trace_links,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        is_valid, error_msg = validate_l3_for_layer(
            data.get("test_layer", "sit"),
            data.get("process_level_id"),
        )
        if not is_valid:
            return jsonify({
                "error": error_msg,
                "resolution_attempted": True,
                "hint": "Ensure the linked WRICEF/Config/Requirement has a scope_item_id (L3) assigned.",
            }), 400

        module = data.get("module", "GEN")
        code = data.get("code") or f"TC-{module.upper()}-{TestCase.query.filter_by(program_id=pid).count() + 1:04d}"
        try:
            assigned_to_id = normalize_member_scope(
                pid,
                data.get("assigned_to_id"),
                field_name="assigned_to_id",
                project_id=project_id,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        tc = TestCase(
            program_id=pid,
            project_id=project_id,
            code=code,
            title=data["title"],
            description=data.get("description", ""),
            test_layer=data.get("test_layer", "sit"),
            test_type=data.get("test_type", "functional"),
            module=data.get("module", ""),
            preconditions=data.get("preconditions", ""),
            test_steps=data.get("test_steps", ""),
            expected_result=data.get("expected_result", ""),
            test_data_set=data.get("test_data_set", ""),
            status=data.get("status", "draft"),
            priority=data.get("priority", "medium"),
            risk=data.get("risk", "medium"),
            is_regression=data.get("is_regression", False),
            assigned_to=data.get("assigned_to", ""),
            reviewer=data.get("reviewer", ""),
            version=data.get("version", "1.0"),
            data_readiness=data.get("data_readiness", ""),
            assigned_to_id=assigned_to_id,
            explore_requirement_id=data.get("explore_requirement_id"),
            backlog_item_id=data.get("backlog_item_id"),
            config_item_id=data.get("config_item_id"),
            process_level_id=data.get("process_level_id"),
        )
        db.session.add(tc)
        db.session.flush()

        for suite_id in suite_ids:
            db.session.add(TestCaseSuiteLink(
                test_case_id=tc.id,
                suite_id=suite_id,
                added_method="manual",
                tenant_id=tc.tenant_id,
            ))

        if normalized_trace_links:
            _sync_test_case_trace_links(tc.id, normalized_trace_links)

        _create_test_case_version(
            tc,
            change_summary=data.get("change_summary", "initial create"),
            created_by=_actor_from_request(data),
        )

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(tc.to_dict()), 201

    @bp.route("/testing/catalog/<int:case_id>", methods=["GET"])
    def get_test_case(case_id):
        """Get test case detail with steps."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err
        include_steps = request.args.get("include_steps", "true").lower() in ("true", "1")
        return jsonify(tc.to_dict(include_steps=include_steps))

    @bp.route("/testing/catalog/<int:case_id>", methods=["PUT"])
    def update_test_case(case_id):
        """Update a test case."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        if data.get("requirement_id") not in (None, ""):
            return jsonify({"error": "requirement_id is no longer accepted; use explore_requirement_id"}), 400
        if data.get("suite_id") not in (None, ""):
            return jsonify({"error": "suite_id is no longer accepted; use suite_ids"}), 400

        try:
            project_id = normalize_project_scope(tc.program_id, request_project_id(data) or tc.project_id)
            assigned_to_id = (
                normalize_member_scope(
                    tc.program_id,
                    data.get("assigned_to_id"),
                    field_name="assigned_to_id",
                    project_id=project_id,
                )
                if "assigned_to_id" in data else tc.assigned_to_id
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        normalized_trace_links = None
        if "traceability_links" in data:
            normalized_trace_links = _normalize_traceability_links(data.get("traceability_links", []))
            for link in normalized_trace_links:
                resolved = resolve_l3_for_tc(
                    {"process_level_id": link["l3_process_level_id"]},
                    project_id=project_id,
                    program_id=tc.program_id,
                )
                if not resolved:
                    return jsonify({
                        "error": f"Invalid L3 process level: {link['l3_process_level_id']}",
                    }), 400
                link["l3_process_level_id"] = resolved

            if normalized_trace_links:
                primary_fields = _derive_primary_traceability_fields(normalized_trace_links)
                data["process_level_id"] = primary_fields["process_level_id"]
                data["explore_requirement_id"] = primary_fields["explore_requirement_id"]
                data["backlog_item_id"] = primary_fields["backlog_item_id"]
                data["config_item_id"] = primary_fields["config_item_id"]
            else:
                data["process_level_id"] = None
                data["explore_requirement_id"] = None
                data["backlog_item_id"] = None
                data["config_item_id"] = None
        elif any(
            field in data
            for field in ("process_level_id", "explore_requirement_id", "backlog_item_id", "config_item_id")
        ):
            data["process_level_id"] = resolve_l3_for_tc(
                data,
                project_id=project_id,
                program_id=tc.program_id,
            )

        try:
            _validate_test_case_traceability_scope(
                data,
                program_id=tc.program_id,
                project_id=project_id,
                normalized_links=normalized_trace_links,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        for field in (
            "code",
            "title",
            "description",
            "test_layer",
            "test_type",
            "module",
            "preconditions",
            "test_steps",
            "expected_result",
            "test_data_set",
            "status",
            "priority",
            "risk",
            "is_regression",
            "assigned_to",
            "reviewer",
            "version",
            "data_readiness",
            "assigned_to_id",
            "explore_requirement_id",
            "backlog_item_id",
            "config_item_id",
            "process_level_id",
        ):
            if field in data:
                setattr(tc, field, assigned_to_id if field == "assigned_to_id" else data[field])

        if "suite_ids" in data or "suite_id" in data:
            try:
                suite_ids = _extract_suite_assignment(data)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            requested = set(suite_ids)
            existing_links = TestCaseSuiteLink.query.filter_by(test_case_id=tc.id).all()
            existing_suite_ids = {link.suite_id for link in existing_links}

            for link in existing_links:
                if link.suite_id not in requested:
                    db.session.delete(link)
            for suite_id in requested - existing_suite_ids:
                db.session.add(TestCaseSuiteLink(
                    test_case_id=tc.id,
                    suite_id=suite_id,
                    added_method="manual",
                    tenant_id=tc.tenant_id,
                ))

        if normalized_trace_links is not None:
            _sync_test_case_trace_links(tc.id, normalized_trace_links)

        _create_test_case_version(
            tc,
            change_summary=data.get("change_summary", "manual update"),
            created_by=_actor_from_request(data),
        )

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(tc.to_dict())

    @bp.route("/testing/catalog/<int:case_id>", methods=["DELETE"])
    def delete_test_case(case_id):
        """Delete a test case."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        db.session.delete(tc)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test case deleted"}), 200

    @bp.route("/testing/catalog/<int:case_id>/versions", methods=["GET"])
    def list_test_case_versions(case_id):
        """List all versions for a test case."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err
        versions = TestCaseVersion.query.filter_by(test_case_id=case_id).order_by(TestCaseVersion.version_no.desc()).all()
        return jsonify([version.to_dict(include_snapshot=False) for version in versions])

    @bp.route("/testing/catalog/<int:case_id>/versions", methods=["POST"])
    def create_test_case_version(case_id):
        """Create an explicit version snapshot for a test case."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        version = _create_test_case_version(
            tc,
            change_summary=data.get("change_summary", "manual snapshot"),
            created_by=_actor_from_request(data),
            version_label=data.get("version_label", ""),
        )

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(version.to_dict(include_snapshot=True)), 201

    @bp.route("/testing/catalog/<int:case_id>/versions/diff", methods=["GET"])
    def diff_test_case_versions(case_id):
        """Return field and step-level diff between two versions."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        try:
            from_no = int(request.args.get("from", ""))
            to_no = int(request.args.get("to", ""))
        except (TypeError, ValueError):
            return jsonify({"error": "from and to query params are required integers"}), 400

        left = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=from_no).first()
        right = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=to_no).first()
        if not left or not right:
            return jsonify({"error": "version not found"}), 404

        return jsonify({
            "test_case_id": case_id,
            "from": left.to_dict(include_snapshot=False),
            "to": right.to_dict(include_snapshot=False),
            "diff": _compute_snapshot_diff(left.snapshot, right.snapshot),
        })

    @bp.route("/testing/catalog/<int:case_id>/versions/<int:version_no>", methods=["GET"])
    def get_test_case_version(case_id, version_no):
        """Get one version snapshot by version number."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        version = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=version_no).first()
        if not version:
            return jsonify({"error": "version not found"}), 404
        return jsonify(version.to_dict(include_snapshot=True))

    @bp.route("/testing/catalog/<int:case_id>/versions/<int:version_no>/restore", methods=["POST"])
    def restore_test_case_version(case_id, version_no):
        """Restore a test case to a previous version snapshot."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        version = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=version_no).first()
        if not version:
            return jsonify({"error": "version not found"}), 404

        snapshot = version.snapshot or {}
        for field in (
            "code",
            "title",
            "description",
            "test_layer",
            "test_type",
            "module",
            "preconditions",
            "test_steps",
            "expected_result",
            "test_data_set",
            "status",
            "priority",
            "risk",
            "is_regression",
            "assigned_to",
            "reviewer",
            "version",
            "data_readiness",
            "assigned_to_id",
            "explore_requirement_id",
            "backlog_item_id",
            "config_item_id",
            "process_level_id",
        ):
            if field in snapshot:
                setattr(tc, field, snapshot.get(field))

        suite_ids = [int(suite_id) for suite_id in (snapshot.get("suite_ids") or []) if suite_id is not None]
        legacy_suite_id = snapshot.get("suite_id")
        if legacy_suite_id and int(legacy_suite_id) not in suite_ids:
            suite_ids.append(int(legacy_suite_id))

        existing_links = TestCaseSuiteLink.query.filter_by(test_case_id=tc.id).all()
        existing_suite_ids = {link.suite_id for link in existing_links}
        requested = set(suite_ids)

        for link in existing_links:
            if link.suite_id not in requested:
                db.session.delete(link)
        for suite_id in requested - existing_suite_ids:
            db.session.add(TestCaseSuiteLink(
                test_case_id=tc.id,
                suite_id=suite_id,
                added_method="restore",
                tenant_id=tc.tenant_id,
            ))

        TestStep.query.filter_by(test_case_id=tc.id).delete()
        for idx, step in enumerate((snapshot.get("steps") or []), start=1):
            action = (step.get("action") or "").strip()
            if not action:
                continue
            db.session.add(TestStep(
                test_case_id=tc.id,
                tenant_id=tc.tenant_id,
                step_no=step.get("step_no") or idx,
                action=action,
                expected_result=step.get("expected_result") or "",
                test_data=step.get("test_data") or "",
                notes=step.get("notes") or "",
            ))

        if "traceability_links" in snapshot:
            _sync_test_case_trace_links(
                tc.id,
                _normalize_traceability_links(snapshot.get("traceability_links") or []),
            )

        data = request.get_json(silent=True) or {}
        restored_version = _create_test_case_version(
            tc,
            change_summary=data.get("change_summary", f"restored from version {version_no}"),
            created_by=_actor_from_request(data),
        )

        err = db_commit_or_error()
        if err:
            return err

        return jsonify({
            "message": "Version restored",
            "restored_from": version_no,
            "new_version": restored_version.to_dict(include_snapshot=False),
            "test_case": tc.to_dict(include_steps=True),
        })

    @bp.route("/testing/catalog/<int:case_id>/traceability-derived", methods=["GET"])
    def get_test_case_traceability_derived(case_id):
        """Return derived/manual/excluded coverage details for UI rendering."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        from app.models.explore.process import ProcessLevel

        links = TestCaseTraceLink.query.filter_by(test_case_id=case_id).all()
        groups = []
        total_not_covered = 0

        for link in links:
            l3_id = str(link.l3_process_level_id)
            requirements = ExploreRequirement.query.filter_by(project_id=tc.project_id, scope_item_id=l3_id).all()
            requirement_ids = {str(requirement.id) for requirement in requirements}

            wricef_items = (
                BacklogItem.query.filter(
                    BacklogItem.program_id == tc.program_id,
                    BacklogItem.project_id == tc.project_id,
                    BacklogItem.explore_requirement_id.in_(requirement_ids),
                ).all()
                if requirement_ids else []
            )
            config_items = (
                ConfigItem.query.filter(
                    ConfigItem.program_id == tc.program_id,
                    ConfigItem.project_id == tc.project_id,
                    ConfigItem.explore_requirement_id.in_(requirement_ids),
                ).all()
                if requirement_ids else []
            )

            payload = link.to_dict()
            excluded_req = {str(value) for value in payload.get("excluded_requirement_ids", [])}
            excluded_wricef = {str(value) for value in payload.get("excluded_backlog_item_ids", [])}
            excluded_cfg = {str(value) for value in payload.get("excluded_config_item_ids", [])}

            derived_req = [{
                "id": str(requirement.id),
                "code": requirement.code,
                "title": requirement.title,
                "fit_status": requirement.fit_status,
                "source": "derived",
                "excluded": str(requirement.id) in excluded_req,
                "coverage_status": "not_covered" if str(requirement.id) in excluded_req else "covered",
            } for requirement in requirements]

            derived_wricef = [{
                "id": backlog.id,
                "code": backlog.code,
                "title": backlog.title,
                "wricef_type": backlog.wricef_type,
                "source": "derived",
                "excluded": str(backlog.id) in excluded_wricef,
                "coverage_status": "not_covered" if str(backlog.id) in excluded_wricef else "covered",
            } for backlog in wricef_items]

            derived_cfg = [{
                "id": config.id,
                "code": config.code,
                "title": config.title,
                "source": "derived",
                "excluded": str(config.id) in excluded_cfg,
                "coverage_status": "not_covered" if str(config.id) in excluded_cfg else "covered",
            } for config in config_items]

            manual_req = [{"id": rid, "source": "manual"} for rid in payload.get("manual_requirement_ids", [])]
            manual_wricef = [{"id": bid, "source": "manual"} for bid in payload.get("manual_backlog_item_ids", [])]
            manual_cfg = [{"id": cid, "source": "manual"} for cid in payload.get("manual_config_item_ids", [])]

            not_covered = sum(1 for item in derived_req if item["coverage_status"] == "not_covered")
            not_covered += sum(1 for item in derived_wricef if item["coverage_status"] == "not_covered")
            not_covered += sum(1 for item in derived_cfg if item["coverage_status"] == "not_covered")
            total_not_covered += not_covered

            groups.append({
                "l3_process_level_id": l3_id,
                "derived": {
                    "requirements": derived_req,
                    "wricef": derived_wricef,
                    "config_items": derived_cfg,
                },
                "manual": {
                    "requirements": manual_req,
                    "wricef": manual_wricef,
                    "config_items": manual_cfg,
                },
                "excluded": {
                    "requirements": list(excluded_req),
                    "wricef": [int(value) for value in excluded_wricef if str(value).isdigit()],
                    "config_items": [int(value) for value in excluded_cfg if str(value).isdigit()],
                },
                "summary": {
                    "derived_requirements": len(derived_req),
                    "derived_wricef": len(derived_wricef),
                    "derived_config_items": len(derived_cfg),
                    "manual_additions": len(manual_req) + len(manual_wricef) + len(manual_cfg),
                    "not_covered": not_covered,
                },
            })

        explore_requirement_code = None
        process_level_name = None
        source_type = "unlinked"

        if tc.explore_requirement_id:
            try:
                explore_requirement = get_scoped(
                    ExploreRequirement,
                    str(tc.explore_requirement_id),
                    project_id=tc.project_id,
                )
            except NotFoundError:
                explore_requirement = None
            if explore_requirement:
                explore_requirement_code = explore_requirement.code
            source_type = "explore"

        if tc.process_level_id:
            try:
                process_level = get_scoped(
                    ProcessLevel,
                    str(tc.process_level_id),
                    project_id=tc.project_id,
                )
            except NotFoundError:
                process_level = None
            if process_level:
                process_level_name = process_level.name

        return jsonify({
            "test_case_id": tc.id,
            "groups": groups,
            "summary": {
                "group_count": len(groups),
                "not_covered_total": total_not_covered,
                "explore_requirement_code": explore_requirement_code,
                "process_level_name": process_level_name,
                "source_type": source_type,
            },
        })

    @bp.route("/testing/catalog/<int:case_id>/traceability-overrides", methods=["PUT"])
    def update_test_case_traceability_overrides(case_id):
        """Update manual or excluded traceability override lists with audit log."""
        tc, err = get_or_404(TestCase, case_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        normalized_links = _normalize_traceability_links(data.get("traceability_links", []))
        if not normalized_links:
            return jsonify({"error": "traceability_links is required"}), 400

        existing_by_l3 = {
            str(link.l3_process_level_id): link.to_dict()
            for link in TestCaseTraceLink.query.filter_by(test_case_id=case_id).all()
        }
        for link in normalized_links:
            existing = existing_by_l3.get(str(link["l3_process_level_id"]), {})
            for field in (
                "l4_process_level_ids",
                "explore_requirement_ids",
                "backlog_item_ids",
                "config_item_ids",
            ):
                if not link.get(field):
                    link[field] = existing.get(field, [])

        try:
            _validate_traceability_links_scope(
                normalized_links,
                program_id=tc.program_id,
                project_id=tc.project_id,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        _sync_test_case_trace_links(case_id, normalized_links)
        write_audit(
            entity_type="test_case",
            entity_id=str(case_id),
            action="update",
            actor=request.headers.get("X-User", "system"),
            program_id=tc.program_id,
            tenant_id=tc.tenant_id,
            diff={"traceability_overrides": {"new": normalized_links}},
        )

        err = db_commit_or_error()
        if err:
            return err

        return jsonify({
            "message": "Traceability overrides updated",
            "traceability_links": [
                link.to_dict() for link in TestCaseTraceLink.query.filter_by(test_case_id=case_id).all()
            ],
        })

    @bp.route("/programs/<int:pid>/testing/suites", methods=["GET"])
    def list_test_suites(pid):
        """List test suites for a program."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            result = catalog_service.list_test_suites(
                pid,
                project_id=resolved_testing_project_id(pid),
                purpose=request.args.get("purpose"),
                status=request.args.get("status"),
                module=request.args.get("module"),
                search=request.args.get("search"),
                suite_type=request.args.get("suite_type"),
                limit=request.args.get("limit"),
                offset=request.args.get("offset"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @bp.route("/programs/<int:pid>/testing/suites", methods=["POST"])
    def create_test_suite(pid):
        """Create a new test suite."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            data = _normalize_suite_payload(request.get_json(silent=True) or {})
            data["project_id"] = request_project_id(data)
            suite = catalog_service.create_test_suite(pid, data)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(suite.to_dict()), 201

    @bp.route("/testing/suites/<int:suite_id>", methods=["GET"])
    def get_test_suite(suite_id):
        """Get test suite detail with optional case expansion."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err
        include_cases = request.args.get("include_cases", "false").lower() in ("true", "1")
        return jsonify(suite.to_dict(include_cases=include_cases))

    @bp.route("/testing/suites/<int:suite_id>", methods=["PUT"])
    def update_test_suite(suite_id):
        """Update a test suite."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        try:
            data = _normalize_suite_payload(request.get_json(silent=True) or {})
            data["project_id"] = request_project_id(data) or suite.project_id
            catalog_service.update_test_suite(suite, data)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(suite.to_dict())

    @bp.route("/testing/suites/<int:suite_id>", methods=["DELETE"])
    def delete_test_suite(suite_id):
        """Delete a suite without deleting linked test cases."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        catalog_service.delete_test_suite(suite)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test suite deleted"}), 200

    @bp.route("/testing/suites/<int:suite_id>/cases", methods=["GET"])
    def list_suite_cases(suite_id):
        """List all test cases linked to a suite."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err
        return jsonify(catalog_service.list_suite_cases(suite.id))

    @bp.route("/testing/suites/<int:suite_id>/cases", methods=["POST"])
    def add_case_to_suite(suite_id):
        """Add a test case to a suite."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        try:
            link = catalog_service.add_case_to_suite(suite, request.get_json(silent=True) or {})
        except NotFoundError as exc:
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ConflictError:
            return jsonify({"error": "Test case already in this suite"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(link.to_dict()), 201

    @bp.route("/testing/suites/<int:suite_id>/cases/<int:tc_id>", methods=["DELETE"])
    def remove_case_from_suite(suite_id, tc_id):
        """Remove a test case from a suite."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        try:
            catalog_service.remove_case_from_suite(suite, tc_id)
        except NotFoundError as exc:
            if exc.resource == "TestCaseSuiteLink":
                return jsonify({"error": "Link not found"}), 404
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return "", 204

    @bp.route("/testing/catalog/<int:case_id>/suites", methods=["GET"])
    def list_tc_suites(case_id):
        """List all suites a test case belongs to."""
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err
        return jsonify(catalog_service.list_test_case_suites(test_case.id))

    @bp.route("/testing/suites/<int:suite_id>/generate-from-wricef", methods=["POST"])
    def generate_from_wricef(suite_id):
        """Auto-generate test cases from WRICEF or config items."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        try:
            created = catalog_service.generate_from_wricef(
                suite,
                wricef_ids=data.get("wricef_item_ids", []),
                config_ids=data.get("config_item_ids", []),
                scope_item_id=data.get("scope_item_id"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

        err = db_commit_or_error()
        if err:
            return err
        return jsonify({
            "message": f"Generated {len(created)} test cases",
            "count": len(created),
            "test_case_ids": [test_case.id for test_case in created],
            "suite_id": suite.id,
        }), 201

    @bp.route("/testing/suites/<int:suite_id>/generate-from-process", methods=["POST"])
    def generate_from_process(suite_id):
        """Auto-generate test cases from Explore process steps."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        scope_item_ids = data.get("scope_item_ids", [])
        if not scope_item_ids:
            return jsonify({"error": "scope_item_ids is required"}), 400

        try:
            created = catalog_service.generate_from_process(
                suite,
                scope_item_ids,
                test_level=data.get("test_level", "sit"),
                uat_category=data.get("uat_category", ""),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

        err = db_commit_or_error()
        if err:
            return err
        return jsonify({
            "message": f"Generated {len(created)} test cases from process",
            "count": len(created),
            "test_case_ids": [test_case.id for test_case in created],
            "suite_id": suite.id,
        }), 201

    @bp.route("/testing/test-cases/<int:case_id>/clone", methods=["POST"])
    def clone_test_case(case_id):
        """Clone a single test case."""
        source, err = get_or_404(TestCase, case_id)
        if err:
            return err

        try:
            clone = catalog_service.clone_test_case(source, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(clone.to_dict()), 201

    @bp.route("/testing/test-suites/<int:suite_id>/clone-cases", methods=["POST"])
    def clone_suite_cases(suite_id):
        """Bulk-clone all test cases from one suite into a target suite."""
        source_suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        target_suite_id = data.get("target_suite_id")
        if not target_suite_id:
            return jsonify({"error": "target_suite_id is required"}), 400

        target_suite, target_err = get_or_404(TestSuite, target_suite_id)
        if target_err:
            return target_err
        if source_suite.program_id != target_suite.program_id:
            return jsonify({"error": "Source and target suites must belong to the same program"}), 400

        overrides = {key: data[key] for key in ("test_layer", "assigned_to", "priority", "module") if key in data}
        try:
            cloned = catalog_service.bulk_clone_suite(suite_id, target_suite_id, overrides)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

        err = db_commit_or_error()
        if err:
            return err
        return jsonify({
            "cloned_count": len(cloned),
            "items": [item.to_dict() for item in cloned],
        }), 201

    @bp.route("/testing/catalog/<int:case_id>/steps", methods=["GET"])
    def list_test_steps(case_id):
        """List steps for a test case ordered by step number."""
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err
        return jsonify(catalog_service.list_test_steps(test_case.id))

    @bp.route("/testing/catalog/<int:case_id>/steps", methods=["POST"])
    def create_test_step(case_id):
        """Add a step to a test case."""
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err

        try:
            step = catalog_service.create_test_step(test_case, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(step.to_dict()), 201

    @bp.route("/testing/steps/<int:step_id>", methods=["PUT"])
    def update_test_step(step_id):
        """Update a test step."""
        step, err = get_or_404(TestStep, step_id)
        if err:
            return err

        catalog_service.update_test_step(step, request.get_json(silent=True) or {})
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(step.to_dict())

    @bp.route("/testing/steps/<int:step_id>", methods=["DELETE"])
    def delete_test_step(step_id):
        """Delete a test step."""
        step, err = get_or_404(TestStep, step_id)
        if err:
            return err

        catalog_service.delete_test_step(step)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test step deleted"}), 200

    @bp.route("/testing/cycles/<int:cycle_id>/suites", methods=["POST"])
    def assign_suite_to_cycle(cycle_id):
        """Assign a suite to a cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        try:
            cycle_suite = catalog_service.assign_suite_to_cycle(cycle, request.get_json(silent=True) or {})
        except NotFoundError as exc:
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ConflictError:
            return jsonify({"error": "Suite already assigned to this cycle"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(cycle_suite.to_dict()), 201

    @bp.route("/testing/cycles/<int:cycle_id>/suites/<int:suite_id>", methods=["DELETE"])
    def remove_suite_from_cycle(cycle_id, suite_id):
        """Remove a suite assignment from a cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        try:
            catalog_service.remove_suite_from_cycle(cycle, suite_id)
        except NotFoundError as exc:
            if exc.resource == "TestCycleSuite":
                return jsonify({"error": "Suite not assigned to this cycle"}), 404
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Suite removed from cycle"}), 200

    @bp.route("/testing/catalog/<int:case_id>/dependencies", methods=["GET"])
    def list_case_dependencies(case_id):
        """List dependencies for a test case."""
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err
        return jsonify(catalog_service.list_case_dependencies(test_case.id))

    @bp.route("/testing/catalog/<int:case_id>/dependencies", methods=["POST"])
    def create_case_dependency(case_id):
        """Create a dependency for a test case."""
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err

        try:
            dependency = catalog_service.create_case_dependency(
                test_case,
                request.get_json(silent=True) or {},
            )
        except NotFoundError as exc:
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ConflictError:
            return jsonify({"error": "Dependency already exists"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(dependency.to_dict()), 201

    @bp.route("/testing/dependencies/<int:dep_id>", methods=["DELETE"])
    def delete_case_dependency(dep_id):
        """Delete a test case dependency."""
        dependency, err = get_or_404(TestCaseDependency, dep_id)
        if err:
            return err

        catalog_service.delete_case_dependency(dependency)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Dependency deleted"}), 200
