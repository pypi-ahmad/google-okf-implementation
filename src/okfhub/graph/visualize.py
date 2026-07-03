"""Graph visualization helpers."""

from pathlib import Path

from pyvis.network import Network

from okfhub.models import ConceptDocument


def export_pyvis_graph(documents: list[ConceptDocument], output_path: Path) -> None:
    """Render a static HTML visualization from concept links."""

    net = Network(height="800px", width="100%", directed=True, bgcolor="#ffffff", font_color="#1f2937")

    path_to_id = {doc.relative_path: doc.concept_id for doc in documents}

    for doc in documents:
        net.add_node(doc.concept_id, label=doc.frontmatter.title, title=doc.frontmatter.type)

    for doc in documents:
        for raw_link in doc.links:
            target = path_to_id.get(raw_link.strip().lstrip("/"))
            if target:
                net.add_edge(doc.concept_id, target, title="LINKS_TO")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output_path))
