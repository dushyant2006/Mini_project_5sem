"""
Unit Tests for CodeDrift RAG and Semantic Documentation Retrieval.
"""
from codedrift.rag import DocumentIndexer, SemanticRetriever
from codedrift.parser import PythonParser
from codedrift.core.models import APIChange


def test_rag_indexes_and_retrieves_docstrings():
    code = """
def process_refund(tx_id: str) -> bool:
    '''Refunds a customer transaction after manager approval.'''
    return True
"""
    parser = PythonParser()
    mod = parser.parse_code(code, module_name="billing")

    retriever = SemanticRetriever()
    retriever.index_module(mod)

    matches = retriever.query("refund customer")
    assert len(matches) > 0
    assert matches[0].document.symbol_name == "billing.process_refund"


def test_rag_explains_change_with_context():
    retriever = SemanticRetriever()
    retriever.indexer.add_document(
        doc_id="doc1",
        symbol_name="auth.login",
        content="Logs in user. Note: deprecated in favor of OAuth2 authenticate().",
    )

    change = APIChange(
        change_type="FUNCTION_REMOVED",
        qualified_name="auth.login",
        is_breaking=True,
        description="Public function was removed.",
        suggested_migration="Switch to OAuth2 authenticate().",
    )

    explanation = retriever.explain_change(change)
    assert "Context for `auth.login`" in explanation
    assert "OAuth2 authenticate" in explanation
