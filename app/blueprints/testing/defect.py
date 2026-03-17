"""Testing blueprint route registrations for defect-side operations."""

from flask import jsonify, request

from app.core.exceptions import ConflictError, NotFoundError
from app.models.program import Program
from app.models.testing import Defect, DefectComment, DefectLink, VALID_TRANSITIONS, canonicalize_defect_status
from app.services.testing import defect as defect_service
from app.services.testing import execution_query as execution_queries
from app.services.helpers.testing_operational_roles import require_operational_permission
from app.utils.helpers import db_commit_or_error


def register_testing_defect_routes(
    bp,
    *,
    get_or_404,
    resolved_testing_project_id,
):
    """Register defect routes on the shared testing blueprint."""

    @bp.route("/programs/<int:pid>/testing/defects", methods=["GET"])
    def list_defects(pid):
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            result = execution_queries.list_defects(
                pid,
                project_id=resolved_testing_project_id(pid),
                severity=request.args.get("severity"),
                status=request.args.get("status"),
                module=request.args.get("module"),
                test_case_id=request.args.get("test_case_id"),
                search=request.args.get("search"),
                limit=request.args.get("limit"),
                offset=request.args.get("offset"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @bp.route("/programs/<int:pid>/testing/defects", methods=["POST"])
    def create_defect(pid):
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            defect = defect_service.create_defect(pid, request.get_json(silent=True) or {})
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(defect.to_dict()), 201

    @bp.route("/testing/defects/<int:defect_id>", methods=["GET"])
    def get_defect(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        include_comments = request.args.get("include_comments", "0") in ("1", "true")
        return jsonify(defect.to_dict(include_comments=include_comments))

    @bp.route("/testing/defects/<int:defect_id>", methods=["PUT"])
    def update_defect(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        payload = request.get_json(silent=True) or {}
        if "status" in payload:
            current_status = canonicalize_defect_status(defect.status)
            next_status = canonicalize_defect_status(payload.get("status"))
            if next_status and next_status != current_status:
                permission_error = require_operational_permission("retest_manage")
                if permission_error:
                    return permission_error

        try:
            defect_service.update_defect(defect, payload)
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({
                "error": str(exc),
                "allowed": VALID_TRANSITIONS.get(defect.status, []),
            }), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(defect.to_dict())

    @bp.route("/testing/defects/<int:defect_id>", methods=["DELETE"])
    def delete_defect(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        defect_service.delete_defect(defect)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Defect deleted"}), 200

    @bp.route("/testing/defects/<int:defect_id>/comments", methods=["GET"])
    def list_defect_comments(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        return jsonify(execution_queries.list_defect_comments(defect.id))

    @bp.route("/testing/defects/<int:defect_id>/comments", methods=["POST"])
    def create_defect_comment(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        try:
            comment = defect_service.create_defect_comment(defect, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(comment.to_dict()), 201

    @bp.route("/testing/defect-comments/<int:comment_id>", methods=["DELETE"])
    def delete_defect_comment(comment_id):
        comment, err = get_or_404(DefectComment, comment_id)
        if err:
            return err
        defect_service.delete_defect_comment(comment)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Comment deleted"}), 200

    @bp.route("/testing/defects/<int:defect_id>/history", methods=["GET"])
    def list_defect_history(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        return jsonify(execution_queries.list_defect_history(defect.id))

    @bp.route("/testing/defects/<int:defect_id>/links", methods=["GET"])
    def list_defect_links(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        return jsonify(execution_queries.list_defect_links(defect.id))

    @bp.route("/testing/defects/<int:defect_id>/links", methods=["POST"])
    def create_defect_link(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        try:
            link = defect_service.create_defect_link(defect, request.get_json(silent=True) or {})
        except NotFoundError:
            return jsonify({"error": "Target defect not found"}), 404
        except ConflictError:
            return jsonify({"error": "Link already exists"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(link.to_dict()), 201

    @bp.route("/testing/defect-links/<int:link_id>", methods=["DELETE"])
    def delete_defect_link(link_id):
        link, err = get_or_404(DefectLink, link_id)
        if err:
            return err
        defect_service.delete_defect_link(link)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Defect link deleted"}), 200

    @bp.route("/testing/defects/<int:defect_id>/sla", methods=["GET"])
    def get_defect_sla(defect_id):
        defect, err = get_or_404(Defect, defect_id)
        if err:
            return err
        return jsonify(execution_queries.get_defect_sla(defect))
