"""
Semantic and Contextual Retriever for API Changes (RAG Subsystem).
Retrieves relevant migration context and explanations for breaking changes.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from .document_indexer import DocumentIndexer, IndexedDocument
from ..core.models import APIChange, ModuleInfo


@dataclass
class RetrievalMatch:
    document: IndexedDocument
    relevance_score: float
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.document.symbol_name,
            "relevance_score": round(self.relevance_score, 3),
            "source": self.document.source,
            "snippet": self.snippet,
        }


class SemanticRetriever:
    """
    RAG engine for retrieving context, rationale, and docs for breaking changes.
    """

    def __init__(self, indexer: Optional[DocumentIndexer] = None):
        self.indexer = indexer or DocumentIndexer()

    def index_module(self, module_info: ModuleInfo, version_tag: str = "upstream") -> None:
        """
        Indexes docstrings from functions and classes in a parsed module.
        """
        for fn in module_info.functions:
            if fn.docstring:
                doc_id = f"{version_tag}:{fn.qualified_name}"
                self.indexer.add_document(
                    doc_id=doc_id,
                    symbol_name=fn.qualified_name,
                    content=fn.docstring,
                    source=f"{version_tag} docstring",
                )

        for cls in module_info.classes:
            if cls.docstring:
                doc_id = f"{version_tag}:{cls.qualified_name}"
                self.indexer.add_document(
                    doc_id=doc_id,
                    symbol_name=cls.qualified_name,
                    content=cls.docstring,
                    source=f"{version_tag} class docstring",
                )
            for m in cls.methods:
                if m.docstring:
                    doc_id = f"{version_tag}:{m.qualified_name}"
                    self.indexer.add_document(
                        doc_id=doc_id,
                        symbol_name=m.qualified_name,
                        content=m.docstring,
                        source=f"{version_tag} method docstring",
                    )

    def query(self, query_text: str, top_k: int = 3) -> List[RetrievalMatch]:
        query_tokens = self.indexer.tokenize(query_text)
        if not query_tokens:
            return []

        doc_scores: Dict[str, float] = {}
        for token in query_tokens:
            matches = self.indexer.inverted_index.get(token, set())
            for doc_id in matches:
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + 1.0

        ranked = sorted(doc_scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        results = []
        for doc_id, score in ranked:
            doc = self.indexer.documents[doc_id]
            norm_score = min(1.0, score / max(1, len(query_tokens)))
            results.append(
                RetrievalMatch(
                    document=doc,
                    relevance_score=norm_score,
                    snippet=doc.content[:300],
                )
            )

        return results

    def explain_change(self, change: APIChange) -> str:
        """
        Synthesizes a contextual explanation for an API change using indexed documentation.
        """
        matches = self.query(f"{change.qualified_name} {change.parameter_name or ''}")
        explanation = [f"### Context for `{change.qualified_name}`:"]
        explanation.append(f"- **Detected Drift:** {change.description}")

        if matches:
            explanation.append("\n**Relevant Documentation Context:**")
            for m in matches:
                explanation.append(f"- *From {m.document.source}:* {m.snippet}")
        else:
            explanation.append("- *No additional docstring context found.*")

        if change.suggested_migration:
            explanation.append(f"- **Remediation Advice:** {change.suggested_migration}")

        return "\n".join(explanation)
