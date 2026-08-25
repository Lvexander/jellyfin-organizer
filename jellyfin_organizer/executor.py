"""Execute filesystem operation plans."""

from __future__ import annotations

import shutil

from .models import OperationStatus, OperationType, Plan, PlanSummary


def summarize_plan(plan: Plan) -> PlanSummary:
    """Summarize what can be processed from a plan."""

    processed = 0
    skipped = 0
    safe_to_delete_source = True

    for operation in plan.operations:
        if operation.status == OperationStatus.OK:
            processed += 1
        else:
            skipped += 1

        if operation.status == OperationStatus.CONFLICT:
            safe_to_delete_source = False

    return PlanSummary(
        processed=processed,
        skipped=skipped,
        safe_to_delete_source=safe_to_delete_source,
    )


def execute_plan(plan: Plan) -> PlanSummary:
    """Execute safe operations from a plan."""

    processed = 0
    skipped = 0
    safe_to_delete_source = True

    for operation in plan.operations:
        if operation.status == OperationStatus.CONFLICT:
            skipped += 1
            safe_to_delete_source = False
            continue

        if operation.status != OperationStatus.OK:
            skipped += 1
            continue

        if operation.operation == OperationType.NOOP:
            processed += 1
            continue

        if operation.destination is None:
            skipped += 1
            continue

        if operation.destination.exists():
            skipped += 1
            safe_to_delete_source = False
            continue

        operation.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(operation.source), str(operation.destination))
        processed += 1

    return PlanSummary(
        processed=processed,
        skipped=skipped,
        safe_to_delete_source=safe_to_delete_source,
    )
