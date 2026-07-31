from django.conf import settings
from django.db import migrations, models

_using_postgres = settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'


class Migration(migrations.Migration):
    """
    Record which pipeline produced each embedding.

    The AlterField below is deliberately skipped on PostgreSQL. makemigrations
    generated it while running against SQLite, where `embedding` really is a
    JSONField; applying it to PostgreSQL would convert the vector(512) column
    created by 0002 back to JSON, dropping the HNSW index with it. On
    PostgreSQL the column is already correct and needs no change.
    """

    dependencies = [
        ("students", "0002_embedding_pgvector"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentembedding",
            name="backend",
            field=models.CharField(db_index=True, default="deepface", max_length=20),
        ),
    ] + ([] if _using_postgres else [
        migrations.AlterField(
            model_name="studentembedding",
            name="embedding",
            field=models.JSONField(default=list),
        ),
    ])
