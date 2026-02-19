"""AI KB service for KB version lifecycle and diff operations.

This service centralizes KB versioning ORM operations so blueprints remain
focused on HTTP parsing/response responsibilities.
"""

import logging

from app.models import db
from app.models.ai import AIEmbedding, KBVersion

logger = logging.getLogger(__name__)


def list_kb_versions() -> list[dict]:
    """Return all KB versions sorted by newest first.

    Returns:
        List of serialized KB version objects.
    """
    versions = KBVersion.query.order_by(KBVersion.created_at.desc()).all()
    return [version.to_dict() for version in versions]


def create_kb_version(data: dict) -> tuple[dict, int]:
    """Create a KB version record.

    Args:
        data: Request payload containing version metadata.

    Returns:
        Tuple of (response_payload, http_status).
    """
    version = data.get("version")
    if not version:
        return {"error": "version is required"}, 400

    existing = KBVersion.query.filter_by(version=version).first()
    if existing:
        return {"error": f"Version {version} already exists"}, 409

    kb_version = KBVersion(
        version=version,
        description=data.get("description", ""),
        embedding_model=data.get("embedding_model"),
        embedding_dim=data.get("embedding_dim"),
        created_by=data.get("created_by", "system"),
    )
    db.session.add(kb_version)
    db.session.commit()
    logger.info("KB version created version=%s id=%s", version, kb_version.id)
    return kb_version.to_dict(), 201


def get_kb_version_with_stats(version_id: int) -> tuple[dict, int]:
    """Fetch a KB version with live embedding statistics.

    Args:
        version_id: KB version primary key.

    Returns:
        Tuple of (response_payload, http_status).
    """
    kb_version = db.session.get(KBVersion, version_id)
    if not kb_version:
        return {"error": "KB version not found"}, 404

    chunk_count = AIEmbedding.query.filter_by(kb_version=kb_version.version, is_active=True).count()
    entity_count = (
        db.session.query(
            db.func.count(db.distinct(db.func.concat(AIEmbedding.entity_type, "-", AIEmbedding.entity_id)))
        )
        .filter_by(kb_version=kb_version.version, is_active=True)
        .scalar()
        or 0
    )

    result = kb_version.to_dict()
    result["live_chunks"] = chunk_count
    result["live_entities"] = entity_count
    return result, 200


def activate_kb_version(version_id: int) -> tuple[dict, int]:
    """Activate a KB version and toggle embedding active flags accordingly.

    Args:
        version_id: KB version primary key.

    Returns:
        Tuple of (response_payload, http_status).
    """
    kb_version = db.session.get(KBVersion, version_id)
    if not kb_version:
        return {"error": "KB version not found"}, 404

    old_active = KBVersion.query.filter(KBVersion.status == "active", KBVersion.id != kb_version.id).first()
    if old_active:
        AIEmbedding.query.filter_by(kb_version=old_active.version, is_active=True).update({"is_active": False})

    AIEmbedding.query.filter_by(kb_version=kb_version.version).update({"is_active": True})
    kb_version.activate()
    db.session.commit()
    logger.info("KB version activated id=%s version=%s", kb_version.id, kb_version.version)
    return kb_version.to_dict(), 200


def archive_kb_version(version_id: int) -> tuple[dict, int]:
    """Archive a non-active KB version and deactivate linked embeddings.

    Args:
        version_id: KB version primary key.

    Returns:
        Tuple of (response_payload, http_status).
    """
    kb_version = db.session.get(KBVersion, version_id)
    if not kb_version:
        return {"error": "KB version not found"}, 404

    if kb_version.status == "active":
        return {"error": "Cannot archive the active version. Activate another version first."}, 400

    AIEmbedding.query.filter_by(kb_version=kb_version.version).update({"is_active": False})
    kb_version.archive()
    db.session.commit()
    logger.info("KB version archived id=%s version=%s", kb_version.id, kb_version.version)
    return kb_version.to_dict(), 200


def diff_kb_versions(version_a: str, version_b: str) -> dict:
    """Compute entity-level diff between two KB versions.

    Args:
        version_a: Left KB version label.
        version_b: Right KB version label.

    Returns:
        Dict containing added/removed/changed entities and summary counts.
    """
    entities_a = {
        (row[0], row[1], row[2])
        for row in db.session.query(AIEmbedding.entity_type, AIEmbedding.entity_id, AIEmbedding.content_hash)
        .filter_by(kb_version=version_a)
        .distinct()
        .all()
    }
    entities_b = {
        (row[0], row[1], row[2])
        for row in db.session.query(AIEmbedding.entity_type, AIEmbedding.entity_id, AIEmbedding.content_hash)
        .filter_by(kb_version=version_b)
        .distinct()
        .all()
    }

    keys_a = {(entity[0], entity[1]) for entity in entities_a}
    keys_b = {(entity[0], entity[1]) for entity in entities_b}

    added = keys_b - keys_a
    removed = keys_a - keys_b
    common = keys_a & keys_b

    hash_a = {(entity[0], entity[1]): entity[2] for entity in entities_a}
    hash_b = {(entity[0], entity[1]): entity[2] for entity in entities_b}
    changed = [key for key in common if hash_a.get(key) != hash_b.get(key)]

    return {
        "version_a": version_a,
        "version_b": version_b,
        "added": [{"entity_type": key[0], "entity_id": key[1]} for key in added],
        "removed": [{"entity_type": key[0], "entity_id": key[1]} for key in removed],
        "changed": [{"entity_type": key[0], "entity_id": key[1]} for key in changed],
        "unchanged": len(common) - len(changed),
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "unchanged_count": len(common) - len(changed),
        },
    }
