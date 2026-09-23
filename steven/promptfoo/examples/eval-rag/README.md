# eval-rag (Rag Eval)

You can run this example with:

```bash
npx promptfoo@latest init --example eval-rag
cd eval-rag
```

## What this example evaluates

Each test passes a question and one local policy document to the prompt. The assertions check six parts of the response:

- A deterministic fact with `contains`.
- A required claim with `factuality`.
- Whether the answer addresses the question with `answer-relevance`.
- Whether the answer includes facts from the expected answer with `context-recall`.
- Whether the retrieved document helps answer the question with `context-relevance`.
- Whether the answer stays grounded in the document with `context-faithfulness`.

## Usage

Set the `OPENAI_API_KEY` environment variable. Then run:

```bash
npx promptfoo@latest eval
```

View the results with `npx promptfoo@latest view`.

The `context-recall` assertions include unsupported facts on purpose. The result table therefore shows both passing and failing RAG metrics. Scores from model-graded assertions can vary between runs.
