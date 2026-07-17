"""FULLTEXT index on document_chunks.content for hybrid retrieval

Revision ID: d4a7c2f91b6e
Revises: b2c9f4a17e30
Create Date: 2026-07-17

Adds the lexical half of hybrid search. Dense retrieval alone cannot find a rare
proper noun: MiniLM has no vector for a token it never saw in training, so it
embeds the nearest everyday word instead. "Impeccable" (a project name) embeds
as the adjective meaning flawless, lands 0.10 away from anything about software,
and scores below the similarity floor even though the literal string sits in the
chunk three times.

A FULLTEXT index answers the one question cosine similarity cannot: is this
string actually present? See ADR-009.

Schema-only and rebuildable — MySQL builds the index from rows already in the
table, so no data migration is needed and the downgrade loses nothing.
"""

from alembic import op

revision = "d4a7c2f91b6e"
down_revision = "b2c9f4a17e30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # InnoDB FULLTEXT. Note the two server defaults this relies on:
    # innodb_ft_min_token_size=3 (shorter words are not indexed) and the
    # built-in 36-word stopword list. Both are fine here — the queries this
    # exists to serve are proper nouns, which are neither short nor stopwords.
    op.create_index(
        "ix_chunk_content_fulltext",
        "document_chunks",
        ["content"],
        mysql_prefix="FULLTEXT",
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_content_fulltext", table_name="document_chunks")
