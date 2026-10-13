"""The worker's text check for a submitted text (docs/TEXT_PROCESSING_PIPELINE.md §5, §10).

`text.derive` links submissions whose standalone text is exactly the same, and records how many
layers do not use the script their contributor chose. Script detection itself happens when a
revision is saved, because saved revisions never change. Nothing is merged or deleted: the same
word from different speakers is valuable variation, and a reviewer decides.
"""

from sqlalchemy import ColumnElement, SQLColumnExpression, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert

from app.modules.processing.queue import JobContext, JobError, JobResult, handler
from app.modules.submissions import service
from app.modules.submissions.models import RelatedItem, Submission, TextLayer, TextRevision
from app.text import normalize, scripts

MAX_DUPLICATE_LINKS = 50


def sql_search_key(column: SQLColumnExpression[str]) -> ColumnElement[str]:
    """normalize.search_key in SQL, so both sides of the comparison are computed the same way."""
    collapsed = func.regexp_replace(column, normalize.SPACE_RUN, " ", "g")
    return func.btrim(collapsed, " \n")


@handler("text.derive")
def check_text(context: JobContext) -> JobResult:
    db = context.db
    submission = db.get(Submission, context.target_id)
    if submission is None:
        raise JobError("submission_not_found", retryable=False)
    current_texts = [
        (view.layer, view.current)
        for view in service.text_layers_of(db, submission.id)
        if view.current
    ]
    mismatched = sum(
        scripts.mismatch(layer.script_code, revision.detected_scripts)
        for layer, revision in current_texts
    )

    # Only standalone text: transcriptions of the same read-speech prompt are meant to match.
    current = TextRevision.id == TextLayer.current_revision_id
    key = sql_search_key(TextRevision.content_nfc)
    mine = (
        select(TextLayer.language_tag, key)
        .join(TextRevision, current)
        .where(TextLayer.submission_id == submission.id, TextLayer.layer_type == "standalone")
    )
    matches = db.scalars(
        select(TextLayer.submission_id)
        .join(TextRevision, current)
        .join(Submission, Submission.id == TextLayer.submission_id)
        .where(
            TextLayer.submission_id != submission.id,
            TextLayer.layer_type == "standalone",
            Submission.status.not_in(("draft", "withdrawn")),
            tuple_(TextLayer.language_tag, key).in_(mine),
        )
        .distinct()
        .order_by(TextLayer.submission_id)
        .limit(MAX_DUPLICATE_LINKS)
    ).all()
    for match in matches:
        pair = sorted([submission.id, match])
        db.execute(
            insert(RelatedItem)
            .values(submission_a=pair[0], submission_b=pair[1], relation="possible_duplicate")
            .on_conflict_do_nothing(constraint="uq_related_items_pair")
        )
    return JobResult(
        output_summary={
            "layers": len(current_texts),
            "script_mismatch": mismatched,
            "duplicates": len(matches),
        }
    )
