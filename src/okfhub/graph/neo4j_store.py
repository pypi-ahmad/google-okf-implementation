"""Neo4j graph persistence for OKF concept relationships."""

from dataclasses import dataclass

from neo4j import Driver, GraphDatabase

from okfhub.models import ConceptDocument


@dataclass(slots=True)
class GraphNeighbor:
    """Neighbor node returned from graph neighborhood queries."""

    concept_id: str
    title: str
    relation: str


class Neo4jGraphStore:
    """Persist and query concept relationship graph in Neo4j."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def ensure_schema(self) -> None:
        """Create basic indexes/constraints for concept graph."""

        queries = [
            "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE",
            "CREATE INDEX concept_type_idx IF NOT EXISTS FOR (c:Concept) ON (c.type)",
        ]
        with self._driver.session() as session:
            for query in queries:
                session.run(query)

    def upsert_documents(self, documents: list[ConceptDocument]) -> None:
        """Upsert concept nodes and links from OKF documents."""

        path_to_id = {doc.relative_path: doc.concept_id for doc in documents}

        with self._driver.session() as session:
            for doc in documents:
                session.run(
                    """
                    MERGE (c:Concept {concept_id: $concept_id})
                    SET c.title = $title,
                        c.type = $type,
                        c.description = $description,
                        c.resource = $resource,
                        c.tags = $tags,
                        c.relative_path = $relative_path
                    """,
                    {
                        "concept_id": doc.concept_id,
                        "title": doc.frontmatter.title,
                        "type": doc.frontmatter.type,
                        "description": doc.frontmatter.description,
                        "resource": doc.frontmatter.resource,
                        "tags": doc.frontmatter.tags,
                        "relative_path": doc.relative_path,
                    },
                )

            for doc in documents:
                for raw_link in doc.links:
                    normalized = raw_link.strip().lstrip("/")
                    target_id = path_to_id.get(normalized)
                    if not target_id:
                        continue
                    session.run(
                        """
                        MATCH (a:Concept {concept_id: $source_id})
                        MATCH (b:Concept {concept_id: $target_id})
                        MERGE (a)-[r:LINKS_TO]->(b)
                        SET r.context = 'markdown_link'
                        """,
                        {"source_id": doc.concept_id, "target_id": target_id},
                    )

    def neighbors(self, concept_id: str, depth: int = 1, limit: int = 25) -> list[GraphNeighbor]:
        """Return outbound neighbors from a concept node."""

        query = (
            "MATCH (c:Concept {concept_id: $concept_id})-[r:LINKS_TO*1..$depth]->(n:Concept) "
            "RETURN DISTINCT n.concept_id AS concept_id, n.title AS title, 'LINKS_TO' AS relation LIMIT $limit"
        )
        with self._driver.session() as session:
            result = session.run(query, {"concept_id": concept_id, "depth": depth, "limit": limit})
            return [
                GraphNeighbor(
                    concept_id=row["concept_id"],
                    title=row["title"] or row["concept_id"],
                    relation=row["relation"],
                )
                for row in result
            ]
