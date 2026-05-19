from django.db import migrations
from pgvector.django import HnswIndex, VectorField


class Migration(migrations.Migration):
    """
    Requires PostgreSQL with the pgvector extension available.
    Run: CREATE EXTENSION IF NOT EXISTS vector;
    (this migration does it automatically via RunSQL).
    """

    dependencies = [
        ('students', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL('CREATE EXTENSION IF NOT EXISTS vector'),

        # Convert the JSONField column to a native vector(512) column.
        # SeparateDatabaseAndState lets us write raw SQL for the DB while
        # updating Django's migration state cleanly via AlterField.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='''
                        ALTER TABLE student_embeddings
                            ADD COLUMN embedding_v vector(512);
                        UPDATE student_embeddings
                            SET embedding_v = (
                                SELECT array_agg(v::double precision)::vector(512)
                                FROM jsonb_array_elements_text(embedding) v
                            );
                        ALTER TABLE student_embeddings DROP COLUMN embedding;
                        ALTER TABLE student_embeddings RENAME COLUMN embedding_v TO embedding;
                    ''',
                    reverse_sql='''
                        ALTER TABLE student_embeddings
                            ADD COLUMN embedding_j jsonb;
                        UPDATE student_embeddings
                            SET embedding_j = to_jsonb(embedding::double precision[]);
                        ALTER TABLE student_embeddings DROP COLUMN embedding;
                        ALTER TABLE student_embeddings RENAME COLUMN embedding_j TO embedding;
                    ''',
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='studentembedding',
                    name='embedding',
                    field=VectorField(dimensions=512),
                ),
            ],
        ),

        migrations.AddIndex(
            model_name='studentembedding',
            index=HnswIndex(
                name='idx_student_embeddings_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
