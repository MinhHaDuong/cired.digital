"""LLM_swap.py — Test different LLMs using the R2R stack and compare answers."""

from r2r_test_utils import (
    QUERY,
    TEST_CONTENT,
    client,
    create_or_get_document,
    delete_document,
    delete_test_file,
    write_test_file,
)

MODEL_NAMES = [
    "openai/gpt-4o-mini",
    "mistral/open-mistral-7b",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-reasoner",
]


def run_all_models() -> dict[str, str]:
    """
    Run RAG queries using all configured models and collect their answers.

    Returns
    -------
    dict[str, str]
        A dictionary mapping model names to their generated answers.

    """
    answers: dict[str, str] = {}
    for model in MODEL_NAMES:
        print(f"Running model: {model}")
        response = client.retrieval.rag(
            query=QUERY,
            rag_generation_config={"model": model, "temperature": 0.0},
        )
        answers[model] = response.results.generated_answer
    return answers


def main() -> None:
    """Run the end-to-end test for all models and print results."""
    write_test_file(content=TEST_CONTENT)
    document_id = create_or_get_document()

    if not document_id:
        print("Aborting: no document ID.")
        return

    print(f"\nQuery: {QUERY}\n")

    results = run_all_models()

    for model, answer in results.items():
        print(f"---- {model} ----")
        print(answer)
        print()

    delete_document(document_id)
    delete_test_file()


if __name__ == "__main__":
    main()
