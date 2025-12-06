# Note Evaluation History Endpoint - Implementation Plan

## Overview

Add a single API endpoint to expose evaluation history for individual notes. This enables tracking AI context quality over time, comparing prompt improvements, and measuring the impact of model changes on the same note content.

**Scope**: Simplified implementation focusing on the most actionable feature - historical tracking per note.

## Current State Analysis

### What We Have
- **265 evaluations** collected since August 2025
- **Average score**: 0.906 (high quality)
- **Score distribution**: 89% at 0.9, 11% at other values (0.8-1.0)
- **Data collected**: score, analysis, prompt, response, model_name, note_id, timestamp
- **Repository**: Basic `EvaluationRepository` with only `add()` and `get_by_note_id()`

### What's Missing
- No API endpoints to access evaluation data
- Cannot track quality improvements when regenerating context
- Cannot compare evaluation scores before/after prompt changes
- No way to validate if model upgrades improved quality

## Implementation Plan

### Phase 1: Repository Layer (Minimal Changes)

**File**: `src/repositories/evaluation_repository.py`

**Status**: ✅ Method already exists!

```python
def get_by_note_id(self, note_id: int) -> list[Evaluation]:
    """Get all evaluations for a specific note, ordered chronologically"""
    statement = select(Evaluation).where(Evaluation.note_id == note_id)
    return list(self.session.exec(statement))
```

**Action**: No changes needed - repository method is already implemented.

### Phase 2: Response Model

**File**: `src/repositories/models.py`

Add simple response wrapper:

```python
class NoteEvaluationHistory(SQLModel):
    """Historical evaluations for a single note"""
    note_id: int
    evaluations: list[Evaluation]
    count: int
```

### Phase 3: New Router

**File**: `src/routers/evaluations.py` (NEW)

Create new router with single endpoint:

```python
from fastapi import APIRouter, Depends, HTTPException
from src.repositories.interfaces import EvaluationRepositoryInterface, NoteRepositoryInterface
from src.repositories.models import NoteEvaluationHistory
from src.dependencies import get_evaluation_repository, get_note_repository

router = APIRouter(tags=["evaluations"])

@router.get(
    "/notes/{note_id}/evaluations",
    summary="Get evaluation history for a note",
    description="""
    Retrieve all historical evaluations for a specific note.

    This endpoint returns chronological evaluation history, enabling:
    - Tracking quality improvements over time
    - Comparing before/after when regenerating context
    - Validating prompt or model changes
    - A/B testing different approaches on the same content

    Evaluations are ordered by creation time (oldest to newest).
    Returns empty list if note has never been evaluated.
    """,
    response_description="Historical evaluation records for the note",
    responses={
        404: {"description": "Note not found"},
        200: {"description": "Evaluation history (may be empty list)"},
    },
)
async def get_note_evaluation_history(
    note_id: int,
    evaluation_repository: EvaluationRepositoryInterface = Depends(get_evaluation_repository),
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
) -> NoteEvaluationHistory:
    # Verify note exists
    note = note_repository.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    # Get all evaluations for this note
    evaluations = evaluation_repository.get_by_note_id(note_id)

    return NoteEvaluationHistory(
        note_id=note_id,
        evaluations=evaluations,
        count=len(evaluations)
    )
```

### Phase 4: Main App Integration

**File**: `src/main.py`

1. Import new evaluations router
2. Add router to app with `app.include_router(evaluations.router)`
3. Add "evaluations" tag to OpenAPI tags list with description:
   ```python
   {
       "name": "evaluations",
       "description": "Analytics and insights from AI quality evaluations"
   }
   ```

### Phase 5: Dependency Injection

**File**: `src/dependencies.py`

**Status**: ✅ Already exists!

Verify `get_evaluation_repository()` dependency exists and is properly configured.

### Phase 6: Tests

Create comprehensive test suite:

**File**: `src/routers/test_evaluations.py` (NEW)

Test coverage for single endpoint:
- ✅ 200 response when note exists with evaluations
- ✅ 200 response when note exists with no evaluations (empty list)
- ✅ 404 response when note doesn't exist
- ✅ Chronological ordering (oldest to newest)
- ✅ Count matches list length
- ✅ Multiple evaluations for same note (regeneration scenario)

## Database Query Reference

Simple single-table query (already implemented in repository):

```sql
-- Get all evaluations for a note, chronologically ordered
SELECT *
FROM evaluation
WHERE note_id = ?
ORDER BY created_at ASC;
```

## Future Enhancements (Deferred)

Additional analytics endpoints that could be valuable later:

1. **Global Statistics**: `GET /evaluations/stats` - Overall quality metrics across all notes
2. **Low Performers**: `GET /evaluations/low-performers` - Find worst-scoring evaluations to debug
3. **Book-Level Quality**: `GET /books/{book_id}/quality` - Aggregate quality by book
4. **Model Comparison**: `GET /evaluations/models` - Compare gpt-4 vs gpt-4o performance
5. **Score Distribution**: `GET /evaluations/distribution` - Histogram of score patterns
6. **Recent Monitoring**: `GET /evaluations/recent` - Live quality monitoring feed

Product enhancements enabled by evaluation data:

7. **Quality-Based Filtering**: Prefer high-scoring notes in `/random` endpoint
8. **Automatic Regeneration**: Retry context generation when score < 0.85
9. **Prompt A/B Testing**: Use evaluation scores to optimize prompts
10. **User Feedback Loop**: Collect user ratings and compare to AI evaluations
11. **Quality Alerts**: Notify when average score drops below threshold

## Testing Checklist

- [ ] Endpoint returns 200 for existing note with evaluations
- [ ] Endpoint returns 200 for existing note with zero evaluations
- [ ] Endpoint returns 404 for non-existent note
- [ ] Evaluations ordered chronologically (oldest first)
- [ ] Response count matches evaluations list length
- [ ] Response model serializes correctly
- [ ] Test with multiple evaluations for same note
- [ ] OpenAPI/Swagger documentation renders correctly
- [ ] Run `uv run pytest` - all tests pass
- [ ] Run `uv run ruff format` - code formatted
- [ ] Run `uv run pyright` - no type errors

## Success Metrics

After implementation, we should be able to:

1. ✅ View evaluation history for any note via API
2. ✅ Track quality changes when regenerating context for the same note
3. ✅ Compare scores before/after prompt improvements
4. ✅ Validate if model upgrades improved quality for specific notes
5. ✅ Enable future "regenerate context" feature with quality tracking

## Rollout Strategy

1. Implement and test in development environment
2. Verify with existing 265 evaluations
3. Document new endpoints in API docs
4. Deploy to production
5. Monitor endpoint usage and performance
6. Iterate based on actual usage patterns

## Design Decisions

### Why Not Include Evaluation in Streaming Response?
**Decision**: Keep evaluation separate from SSE streaming endpoints (`/random`, `/books/{id}/notes/{id}`)

**Rationale**:
- Evaluation happens in background task AFTER streaming completes
- Including evaluation would require either:
  - Waiting for evaluation before streaming (slow UX)
  - Showing previous evaluation (confusing - not current context)
  - Complex dual-event pattern (over-engineered)
- Clean separation: streaming is fast, evaluation history is separate query

### Why Single Endpoint vs Full Analytics Suite?
**Decision**: Implement only `/notes/{note_id}/evaluations` initially

**Rationale**:
- Most actionable feature: enables iterative quality improvement
- Repository method already exists (zero new DB code)
- Simple to implement and test (2-3 hours vs 6-9 hours)
- Can add more endpoints later if needed (see Future Enhancements)
- Follows YAGNI principle (You Aren't Gonna Need It)

## Estimated Effort

- Repository layer: **0 hours** (already exists!)
- Response model: **15 minutes**
- Router/endpoint: **30 minutes**
- Tests: **1 hour**
- Integration & docs: **15 minutes**
- **Total: 2-3 hours**

## Files to Create/Modify

### Create
- [ ] `src/routers/evaluations.py` - New router with single endpoint (~40 lines)
- [ ] `src/routers/test_evaluations.py` - Test suite (~80 lines)

### Modify
- [ ] `src/repositories/models.py` - Add `NoteEvaluationHistory` response model (~6 lines)
- [ ] `src/main.py` - Register new router and OpenAPI tag (~3 lines)

### No Changes Needed
- ✅ `src/repositories/evaluation_repository.py` - `get_by_note_id()` already exists
- ✅ `src/repositories/interfaces.py` - `get_by_note_id()` already in protocol
- ✅ `src/dependencies.py` - `get_evaluation_repository()` already configured

## References

- Existing evaluation model: [src/repositories/models.py:126-138](src/repositories/models.py#L126-L138)
- Current repository: [src/repositories/evaluation_repository.py](src/repositories/evaluation_repository.py)
- Example router pattern: [src/routers/books.py](src/routers/books.py)
- Background evaluation trigger: [src/routers/notes.py:119-125](src/routers/notes.py#L119-L125)
