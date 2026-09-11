"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { ApiError, askInvoiceQuestion, type ChatResponse } from "@/lib/api";

type ChatMessage =
  | {
      role: "user";
      content: string;
    }
  | {
      role: "assistant";
      content: string;
      sql: string;
      rows: Array<Record<string, unknown>>;
    };

const suggestedQuestions = [
  "What is the total amount across all invoices?",
  "Which vendor has the highest invoice total?",
  "Show the latest saved invoices.",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendQuestion(nextQuestion = question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || isSending) return;

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: trimmed,
      },
    ]);
    setQuestion("");
    setError(null);
    setIsSending(true);

    try {
      const response: ChatResponse = await askInvoiceQuestion(trimmed);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          sql: response.sql,
          rows: response.rows,
        },
      ]);
    } catch (chatError) {
      setError(
        chatError instanceof ApiError
          ? chatError.message
          : "Could not answer this invoice question.",
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendQuestion();
  }

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col">
        <nav className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-editorial text-5xl font-medium tracking-tight">
              Chat with invoices
            </h1>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              className="rounded-full border border-ink/15 bg-white px-5 py-3 text-sm font-extrabold text-ink transition hover:border-forest hover:text-forest"
              href="/invoices"
            >
              Saved invoices
            </Link>
            <Link
              className="rounded-full bg-ink px-5 py-3 text-sm font-extrabold text-white transition hover:bg-forest"
              href="/"
            >
              Upload invoice
            </Link>
          </div>
        </nav>

        <div className="mt-8 flex flex-1 flex-col rounded-[2rem] border border-white/80 bg-white/80 shadow-card backdrop-blur">
          <div className="flex-1 space-y-5 overflow-y-auto p-5 sm:p-7">
            {messages.length === 0 ? (
              <div className="grid h-full min-h-[24rem] place-items-center text-center">
                <div>
                  <h2 className="font-editorial text-3xl">
                    Ask about saved invoice data.
                  </h2>
                  <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-ink/55">
                    Answers are generated from PostgreSQL query results only.
                    The SQL and rows are shown with each answer so you can
                    inspect the evidence.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {suggestedQuestions.map((item) => (
                      <button
                        className="rounded-full border border-ink/10 bg-cream px-4 py-2 text-xs font-bold text-ink/70 transition hover:border-forest hover:text-forest"
                        disabled={isSending}
                        key={item}
                        onClick={() => sendQuestion(item)}
                        type="button"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <article
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                  key={`${message.role}-${index}`}
                >
                  <div
                    className={`max-w-[90%] rounded-3xl px-5 py-4 ${
                      message.role === "user"
                        ? "bg-ink text-white"
                        : "bg-cream text-ink"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-6">
                      {message.content}
                    </p>

                    {message.role === "assistant" && (
                      <details className="mt-4 rounded-2xl border border-ink/10 bg-white/70 p-4">
                        <summary className="cursor-pointer text-xs font-extrabold uppercase tracking-wider text-ink/45">
                          SQL and returned rows
                        </summary>
                        <pre className="mt-3 overflow-auto rounded-xl bg-ink px-4 py-3 text-xs leading-5 text-cream">
                          {message.sql}
                        </pre>
                        <pre className="mt-3 max-h-60 overflow-auto rounded-xl bg-ink px-4 py-3 text-xs leading-5 text-cream">
                          {JSON.stringify(message.rows, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </article>
              ))
            )}

            {error && (
              <p className="rounded-xl bg-coral/10 px-4 py-3 text-sm font-semibold text-[#a23f2a]">
                {error}
              </p>
            )}
          </div>

          <form
            className="border-t border-ink/10 p-4 sm:p-5"
            onSubmit={handleSubmit}
          >
            <div className="flex gap-3 rounded-full border border-ink/10 bg-white p-2">
              <input
                className="min-w-0 flex-1 bg-transparent px-4 text-sm font-semibold text-ink outline-none placeholder:text-ink/35"
                disabled={isSending}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a question about saved invoices..."
                value={question}
              />
              <button
                className="rounded-full bg-ink px-5 py-3 text-sm font-extrabold text-white transition enabled:hover:bg-forest disabled:cursor-not-allowed disabled:opacity-40"
                disabled={!question.trim() || isSending}
                type="submit"
              >
                {isSending ? "Thinking..." : "Send"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
}
