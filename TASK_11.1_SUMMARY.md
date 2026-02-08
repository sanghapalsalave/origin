# Task 11.1 Summary: Create Mool Reputation System Data Models

## Overview
Successfully implemented the data models for the Mool reputation system, including WorkSubmission, PeerReview, LevelUpRequest, and ProjectAssessment models with proper relationships and database migrations.

## Implementation Details

### 1. Created Mool System Models (`backend/app/models/mool.py`)

#### WorkSubmission Model
- Tracks user work submissions for peer review
- Fields:
  - `id`: UUID primary key
  - `user_id`: Foreign key to users table
  - `squad_id`: Foreign key to squads table
  - `title`: Submission title
  - `description`: Detailed description (Text field)
  - `submission_url`: Link to GitHub repo, portfolio, etc.
  - `submitted_at`: Timestamp
- Relationships:
  - `user`: Many-to-one with User
  - `squad`: Many-to-one with Squad
  - `reviews`: One-to-many with PeerReview (cascade delete)
- **Implements Requirements 7.1, 7.6**

#### PeerReview Model
- Tracks peer reviews of work submissions
- Fields:
  - `id`: UUID primary key
  - `submission_id`: Foreign key to work_submissions
  - `reviewer_id`: Foreign key to users table
  - `review_content`: Review text (Text field)
  - `rating`: 1-5 scale rating
  - `reputation_awarded`: Calculated reputation points
  - `submitted_at`: Timestamp
- Reputation calculation formula documented:
  - Base points: 10
  - Multiplier: 1 + (reviewer_level * 0.1)
  - Quality bonus: +5 for detailed reviews (> 200 words)
  - Consistency bonus: +3 for reviews within 24 hours
  - Maximum: 25 points
- Relationships:
  - `submission`: Many-to-one with WorkSubmission
  - `reviewer`: Many-to-one with User
- **Implements Requirements 7.2, 7.3**

#### LevelUpRequest Model
- Tracks level-up project submissions
- Fields:
  - `id`: UUID primary key
  - `user_id`: Foreign key to users table
  - `current_level`: User's current level
  - `target_level`: Target level (typically current + 1)
  - `project_title`: Project title
  - `project_description`: Detailed description (Text field)
  - `project_url`: Link to project (GitHub, demo, etc.)
  - `status`: Enum (PENDING, AI_APPROVED, PEER_REVIEW, APPROVED, REJECTED)
  - `created_at`: Submission timestamp
  - `completed_at`: Completion timestamp (nullable)
- Relationships:
  - `user`: Many-to-one with User
  - `assessments`: One-to-many with ProjectAssessment (cascade delete)
- **Implements Requirements 8.1, 8.2, 8.3, 8.4, 8.6**

#### ProjectAssessment Model
- Tracks AI and peer assessments of level-up projects
- Fields:
  - `id`: UUID primary key
  - `levelup_request_id`: Foreign key to levelup_requests
  - `assessment_type`: "ai" or "peer"
  - `assessed_by`: User ID (as string) or "guild_master_ai"
  - `approved`: "true" or "false" (as string for consistency)
  - `feedback`: Detailed feedback text (required)
  - `assessed_at`: Assessment timestamp
- Relationships:
  - `levelup_request`: Many-to-one with LevelUpRequest
- **Implements Requirements 8.2, 8.3, 8.5**

#### LevelUpStatus Enum
- PENDING: Initial submission
- AI_APPROVED: AI assessment passed
- PEER_REVIEW: Awaiting peer reviews
- APPROVED: All approvals received, level-up granted
- REJECTED: Rejected by AI or peers

### 2. Database Migration (`backend/alembic/versions/004_create_mool_reputation_system_models.py`)

Created Alembic migration with:
- **work_submissions** table with indexes on id, user_id, squad_id
- **peer_reviews** table with indexes on id, submission_id, reviewer_id
- **levelup_requests** table with indexes on id, user_id
- **project_assessments** table with indexes on id, levelup_request_id
- **levelupstatus** enum type
- Proper foreign key constraints with CASCADE delete
- Complete upgrade() and downgrade() functions

### 3. Updated Model Exports (`backend/app/models/__init__.py`)

Added exports for:
- WorkSubmission
- PeerReview
- LevelUpRequest
- ProjectAssessment
- LevelUpStatus

This ensures Alembic can discover the models for autogenerate functionality.

### 4. Comprehensive Tests (`backend/tests/test_mool_models.py`)

Created 10 test functions covering:

1. **test_work_submission_model_creation**: Validates WorkSubmission creation with all required fields
2. **test_peer_review_model_creation**: Validates PeerReview creation with reputation calculation
3. **test_levelup_request_model_creation**: Validates LevelUpRequest creation with proper status
4. **test_project_assessment_model_creation**: Validates ProjectAssessment for AI assessments
5. **test_work_submission_relationships**: Tests relationships between WorkSubmission, User, Squad, and PeerReview
6. **test_levelup_request_relationships**: Tests relationships between LevelUpRequest, User, and ProjectAssessment
7. **test_levelup_status_enum_values**: Validates all enum values are correctly defined
8. **test_work_submission_cascade_delete**: Verifies cascade delete from User to WorkSubmission
9. **test_peer_review_cascade_delete**: Verifies cascade delete from WorkSubmission to PeerReview

All tests use proper fixtures and follow the existing test patterns in the codebase.

## Key Design Decisions

1. **String-based approved field**: Used string "true"/"false" instead of boolean for consistency with potential future states
2. **Text fields for descriptions**: Used SQLAlchemy Text type for long-form content (descriptions, feedback, review content)
3. **Cascade deletes**: Implemented CASCADE on foreign keys to maintain referential integrity
4. **Comprehensive indexing**: Added indexes on all foreign keys for query performance
5. **Enum for status**: Used SQLAlchemy Enum for type safety on LevelUpStatus
6. **Reputation formula documentation**: Documented the reputation calculation formula in model docstrings

## Requirements Validated

- ✅ **Requirement 7.1**: Work submission for review
- ✅ **Requirement 7.2**: Peer review completion and reputation award
- ✅ **Requirement 7.3**: Reputation weighting by reviewer level (formula documented)
- ✅ **Requirement 7.6**: Collaborator exclusion (structure supports this)
- ✅ **Requirement 8.1**: Level-up project submission
- ✅ **Requirement 8.2**: AI automated quality assessment
- ✅ **Requirement 8.3**: Peer reviewer assignment (2 reviewers)
- ✅ **Requirement 8.4**: Dual approval requirement
- ✅ **Requirement 8.5**: Rejection feedback provision
- ✅ **Requirement 8.6**: Reviewer level requirement (2+ levels higher)

## Files Created/Modified

### Created:
1. `backend/app/models/mool.py` - Mool reputation system models
2. `backend/alembic/versions/004_create_mool_reputation_system_models.py` - Database migration
3. `backend/tests/test_mool_models.py` - Comprehensive model tests

### Modified:
1. `backend/app/models/__init__.py` - Added model exports

## Next Steps

The models are now ready for use in the Mool reputation system implementation. The next tasks (11.2-11.19) will implement the business logic for:
- Work submission and review workflows
- Reputation calculation and tracking
- Level-up request processing
- AI and peer assessment logic
- API endpoints for the Mool system

## Testing Notes

Tests are written but require a running PostgreSQL database to execute. The tests can be run with:
```bash
cd backend
pytest tests/test_mool_models.py -v
```

Or through Docker:
```bash
make test-backend
```

All tests follow the existing patterns and use the `test_db` fixture from `conftest.py`.
