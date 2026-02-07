# Pinecone Vector Similarity Search Service

## Overview

The `PineconeService` provides vector similarity search functionality for the ORIGIN Learning Platform's squad matching system. It handles storage, retrieval, and similarity queries for user embeddings in Pinecone's vector database.

## Features

- **Store Embeddings**: Store 384-dimensional user embeddings with metadata
- **Query Similar Users**: Find compatible users based on cosine similarity
- **Update Embeddings**: Update existing embeddings when user profiles change
- **Delete Embeddings**: Remove embeddings when users are deleted
- **Calculate Similarity**: Compute pairwise cosine similarity between users
- **Retry Logic**: Automatic retry with exponential backoff for API failures
- **Filtering**: Filter by interest area, timezone, and language

## Requirements

### Environment Variables

```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1  # or your preferred region
```

### Dependencies

- `pinecone-client==3.0.0`
- `numpy` (for similarity calculations)

## Usage

### Initialize Service

```python
from app.services.pinecone_service import PineconeService
from app.db.session import SessionLocal

db = SessionLocal()
service = PineconeService(db)
```

### Store User Embedding

```python
from uuid import uuid4

user_id = uuid4()
embedding_vector = [0.1] * 384  # 384-dimensional vector

metadata = {
    "skill_level": 7,
    "learning_velocity": 2.5,
    "timezone": "America/New_York",
    "timezone_offset": -5.0,
    "language": "en",
    "interest_area": "Python Development"
}

pinecone_id = service.store_embedding(user_id, embedding_vector, metadata)
print(f"Stored embedding: {pinecone_id}")
```

### Query Similar Users

```python
# Find similar users for squad matching
similar_users = service.query_similar_users(
    user_id=user_id,
    guild_interest_area="Python Development",
    top_k=50,
    min_similarity=0.7,
    timezone_tolerance_hours=3.0,
    language="en"
)

for user in similar_users:
    print(f"User: {user['user_id']}")
    print(f"Similarity: {user['similarity_score']:.4f}")
    print(f"Skill Level: {user['skill_level']}")
```

### Calculate Pairwise Similarity

```python
# Calculate similarity between two specific users
similarity = service.calculate_similarity(user_id_1, user_id_2)
print(f"Cosine similarity: {similarity:.4f}")

if similarity >= 0.7:
    print("Users are compatible for squad matching!")
```

### Update Embedding

```python
# Update when user's profile changes
updated_embedding = [0.2] * 384
updated_metadata = {
    "skill_level": 8,  # User leveled up
    "learning_velocity": 3.0,
    "timezone": "America/New_York",
    "timezone_offset": -5.0,
    "language": "en",
    "interest_area": "Python Development"
}

service.update_embedding(user_id, updated_embedding, updated_metadata)
```

### Delete Embedding

```python
# Delete when user is removed
service.delete_embedding(user_id)
```

### Get Index Statistics

```python
stats = service.get_index_stats()
print(f"Total vectors: {stats['total_vectors']}")
print(f"Dimensions: {stats['dimension']}")
print(f"Index fullness: {stats['index_fullness']:.2%}")
```

## Architecture

### Index Configuration

- **Index Name**: `origin-user-embeddings`
- **Dimensions**: 384 (from Sentence Transformers `all-MiniLM-L6-v2` model)
- **Metric**: Cosine similarity
- **Cloud**: AWS Serverless

### Vector ID Format

Vectors are stored with IDs in the format: `user_{user_id}`

Example: `user_123e4567-e89b-12d3-a456-426614174000`

### Metadata Schema

Each vector includes the following metadata:

```python
{
    "user_id": str,              # UUID as string
    "skill_level": int,          # 1-10
    "learning_velocity": float,  # tasks per day
    "timezone": str,             # IANA timezone (e.g., "America/New_York")
    "timezone_offset": float,    # UTC offset in hours
    "language": str,             # ISO 639-1 code (e.g., "en")
    "interest_area": str,        # Guild interest area
    "embedding_version": str,    # Version for tracking algorithm changes
    "created_at": str,           # ISO timestamp
    "updated_at": str            # ISO timestamp
}
```

## Filtering

### Interest Area Filtering

All queries filter by interest area to ensure users are matched within the same guild:

```python
filter_dict = {
    "interest_area": {"$eq": "Python Development"}
}
```

### Timezone Filtering

Queries filter by timezone offset to find users with compatible schedules:

```python
# Find users within ±3 hours
filter_dict["timezone_offset"] = {
    "$gte": user_timezone_offset - 3.0,
    "$lte": user_timezone_offset + 3.0
}
```

### Language Filtering

Optional language filtering for multilingual support:

```python
filter_dict["language"] = {"$eq": "en"}
```

## Similarity Threshold

The squad matching algorithm uses a **cosine similarity threshold of 0.7** as specified in the design document. Users with similarity scores below this threshold are not considered compatible for squad formation.

### Similarity Score Interpretation

- **0.9 - 1.0**: Highly compatible (very similar profiles)
- **0.7 - 0.9**: Compatible (suitable for squad matching)
- **0.5 - 0.7**: Somewhat similar (not recommended for matching)
- **< 0.5**: Not compatible

## Error Handling

### Retry Logic

All Pinecone operations use exponential backoff retry logic:

- **Max Retries**: 3
- **Initial Delay**: 1 second
- **Max Delay**: 16 seconds
- **Exponential Base**: 2x
- **Jitter**: ±25% random variation

### Common Errors

#### ValueError: Pinecone API key not configured

**Solution**: Set `PINECONE_API_KEY` in your `.env` file

#### ValueError: Expected 384-dimensional embedding

**Solution**: Ensure embeddings are generated with the correct model (`all-MiniLM-L6-v2`)

#### ValueError: No vector embedding found for user

**Solution**: Ensure the user has a `VectorEmbedding` record in the database before querying

## Integration with Squad Matching

The Pinecone service is used by the Node Logic matching engine (Task 6.5) to:

1. **Store embeddings** when users complete onboarding
2. **Query similar users** when forming new squads
3. **Update embeddings** when user profiles change (skill level, velocity)
4. **Delete embeddings** when users are removed from the system

### Workflow

```
User Onboarding
    ↓
Generate Vector Embedding (PortfolioAnalysisService)
    ↓
Store in Pinecone (PineconeService.store_embedding)
    ↓
User Joins Guild
    ↓
Query Similar Users (PineconeService.query_similar_users)
    ↓
Form Squad (NodeLogicMatcher)
```

## Performance Considerations

### Query Performance

- Pinecone queries are typically < 100ms for indexes with millions of vectors
- Use `top_k` parameter to limit results and improve performance
- Metadata filtering is applied server-side for efficiency

### Index Capacity

- Serverless indexes scale automatically
- Monitor index fullness with `get_index_stats()`
- Consider index sharding for very large deployments (millions of users)

### Cost Optimization

- Batch upsert operations when possible
- Use appropriate `top_k` values (50-100 for squad matching)
- Delete embeddings for inactive users

## Testing

### Unit Tests

Run unit tests with mocked Pinecone client:

```bash
pytest backend/tests/test_pinecone_service.py -v
```

### Integration Tests

Run integration tests with real Pinecone instance:

```bash
# Set test API key
export PINECONE_API_KEY=your_test_api_key

# Run examples
python backend/examples/pinecone_service_example.py
```

## Design Document References

- **Requirement 2.1**: Vector embedding generation and storage
- **Requirement 2.2**: Interest area filtering for squad matching
- **Requirement 2.3**: Cosine similarity calculation
- **Property 5**: Squad Matching Interest Area Filtering
- **Property 6**: Cosine Similarity Bounds

## Related Services

- **PortfolioAnalysisService**: Generates vector embeddings from user profiles
- **NodeLogicMatcher** (Task 6.5): Uses Pinecone service for squad formation
- **UserService**: Manages user profiles and triggers embedding updates

## Future Enhancements

- [ ] Batch operations for bulk embedding storage
- [ ] Hybrid search combining vector similarity and keyword filters
- [ ] A/B testing for different similarity thresholds
- [ ] Embedding versioning and migration support
- [ ] Real-time embedding updates via webhooks
