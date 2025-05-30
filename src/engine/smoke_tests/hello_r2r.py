# hello_r2r.py
"""hello_r2r.py — Smoke test for R2R stack."""

from r2r_test_utils import (
    MODEL,
    QUERY,
    TEMPERATURE,
    client,
    create_or_get_document,
    delete_document,
    delete_test_file,
    write_test_file,
)


def main() -> None:
    """
    Run a basic smoke test for the R2R stack.

    This script creates or fetches a document, performs a RAG query on it,
    prints the generated answer, and cleans up test files and documents.

    Raises
    ------
        RuntimeError: If document creation fails and no ID is returned.

    """
    write_test_file()
    document_id = create_or_get_document()

    if document_id:
        rag_response = client.retrieval.rag(
            query=QUERY,
            rag_generation_config={"model": MODEL, "temperature": TEMPERATURE},
        )
        print(f"Completion:\n{rag_response.results.generated_answer}")
        delete_document(document_id)
    else:
        print("Skipping RAG query: no document ID available.")

    delete_test_file()


if __name__ == "__main__":
    main()
