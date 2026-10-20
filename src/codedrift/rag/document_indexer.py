"""
Document and Docstring Indexer for CodeDrift RAG Engine.
Indexes code documentation, docstrings, and release notes for semantic retrieval.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any


@dataclass
class IndexedDocument:
    doc_id: str
    symbol_name: str
    content: str
    source: str
    tokens: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "symbol_name": self.symbol_name,
            "content": self.content,
            "source": self.source,
        }


class DocumentIndexer:
    """
    Builds an inverted index over API docstrings and changelogs.
    """

    def __init__(self):
        self.documents: Dict[str, IndexedDocument] = {}
        self.inverted_index: Dict[str, Set[str]] = {}

    def tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())
        return set(words)

    def add_document(self, doc_id: str, symbol_name: str, content: str, source: str = "docstring") -> None:
        if not content:
            return
        tokens = self.tokenize(content) | self.tokenize(symbol_name)
        doc = IndexedDocument(
            doc_id=doc_id,
            symbol_name=symbol_name,
            content=content,
            source=source,
            tokens=tokens,
        )
        self.documents[doc_id] = doc

        for token in tokens:
            self.inverted_index.setdefault(token, set()).add(doc_id)

    def clear(self) -> None:
        self.documents.clear( )
        self.inverted_index.clear()
