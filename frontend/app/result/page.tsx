"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";

import {
  ApiError,
  updateInvoice,
  type ExtractResult,
  type InvoiceData,
  type InvoiceRecord,
} from "@/lib/api";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

const fieldLabels: Record<keyof InvoiceData, string> = {
  invoice_number: "Invoice number",
  vendor_name: "Vendor name",
  date: "Date",
  total_amount: "Total amount",
  vat: "VAT",
  currency: "Currency",
};

function invoiceRecordToData(invoice: InvoiceRecord): InvoiceData {
  return {
    invoice_number: invoice.invoice_number ?? "",
    vendor_name: invoice.vendor_name ?? "",
    date: invoice.date ?? "",
    total_amount: invoice.total_amount ?? 0,
    vat: invoice.vat ?? 0,
    currency: invoice.currency ?? "",
  };
}

export default function ResultPage() {
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [formData, setFormData] = useState<InvoiceData | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const savedResult = window.sessionStorage.getItem("invoice-extract-result");
    if (savedResult) {
      try {
        const parsed = JSON.parse(savedResult) as ExtractResult;
        setResult(parsed);
        setFormData(parsed.data);
      } catch {
        window.sessionStorage.removeItem("invoice-extract-result");
      }
    }
    setLoaded(true);
  }, []);

  function updateField(
    field: keyof InvoiceData,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    if (!formData) return;

    const rawValue = event.target.value;
    setSaveMessage(null);
    setSaveError(null);
    setFormData({
      ...formData,
      [field]:
        field === "total_amount" || field === "vat"
          ? Number(rawValue)
          : rawValue,
    });
  }

  async function handleSaveChanges() {
    if (!result || !formData || isSaving) return;

    setIsSaving(true);
    setSaveMessage(null);
    setSaveError(null);

    try {
      const updatedInvoice = await updateInvoice(result.invoice_id, formData);
      const updatedData = invoiceRecordToData(updatedInvoice);
      const updatedResult: ExtractResult = {
        ...result,
        data: updatedData,
        message: "Invoice changes saved successfully.",
      };

      setResult(updatedResult);
      setFormData(updatedData);
      window.sessionStorage.setItem(
        "invoice-extract-result",
        JSON.stringify(updatedResult),
      );
      setSaveMessage("Invoice changes saved successfully.");
    } catch (error) {
      setSaveError(
        error instanceof ApiError
          ? error.message
          : "Could not save invoice changes.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-5 py-12">
      <section className="w-full max-w-4xl rounded-[2rem] border border-white/80 bg-white/80 p-6 shadow-card backdrop-blur sm:p-10">
        {!loaded ? (
          <p className="text-center text-sm text-ink/55">
            Loading extraction result...
          </p>
        ) : result && formData ? (
          <>
            <div className="grid h-16 w-16 place-items-center rounded-full bg-sage text-3xl text-forest">
              ✓
            </div>
            <p className="mt-7 text-xs font-extrabold uppercase tracking-[0.2em] text-forest">
              Saved invoice
            </p>
            <h1 className="font-editorial mt-2 text-4xl font-medium tracking-tight">
              Structured invoice data is saved.
            </h1>
            <p className="mt-4 text-sm leading-6 text-ink/60">
              {result.message}
            </p>

            <dl className="mt-8 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-cream/60 px-5">
              {[
                ["File", result.filename],
                ["Type", result.content_type],
                ["Size", formatBytes(result.size_bytes)],
                ["Saved ID", result.invoice_id],
                ["Phase", "5 - Editable PostgreSQL record"],
              ].map(([label, value]) => (
                <div
                  className="grid gap-1 py-4 sm:grid-cols-[7rem_1fr]"
                  key={label}
                >
                  <dt className="text-xs font-extrabold uppercase tracking-wider text-ink/40">
                    {label}
                  </dt>
                  <dd className="break-all text-sm font-semibold text-ink/80">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>

            <section className="mt-8">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-sm font-extrabold uppercase tracking-wider text-ink/45">
                    Editable invoice fields
                  </h2>
                  <p className="mt-1 text-sm text-ink/55">
                    Update fields here, then save changes back to PostgreSQL.
                    Raw OCR text is not modified.
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {(Object.keys(fieldLabels) as Array<keyof InvoiceData>).map(
                  (field) => (
                    <label className="block" key={field}>
                      <span className="text-xs font-extrabold uppercase tracking-wider text-ink/45">
                        {fieldLabels[field]}
                      </span>
                      <input
                        className="mt-2 w-full rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm font-semibold text-ink outline-none transition focus:border-forest focus:ring-4 focus:ring-forest/15"
                        onChange={(event) => updateField(field, event)}
                        type={
                          field === "total_amount" || field === "vat"
                            ? "number"
                            : "text"
                        }
                        value={String(formData[field])}
                      />
                    </label>
                  ),
                )}
              </div>

              {saveMessage && (
                <p className="mt-4 rounded-xl bg-forest/10 px-4 py-3 text-sm font-semibold text-forest">
                  {saveMessage}
                </p>
              )}

              {saveError && (
                <p className="mt-4 rounded-xl bg-coral/10 px-4 py-3 text-sm font-semibold text-[#a23f2a]">
                  {saveError}
                </p>
              )}

              <button
                className="mt-5 inline-flex rounded-full bg-forest px-5 py-3 text-sm font-extrabold text-white transition enabled:hover:bg-ink disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-4 focus:ring-forest/20"
                disabled={isSaving}
                onClick={handleSaveChanges}
                type="button"
              >
                {isSaving ? "Saving..." : "Save changes"}
              </button>
            </section>

            <section className="mt-8">
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-ink/45">
                Raw OCR text
              </h2>
              <pre className="mt-3 max-h-[22rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-ink/10 bg-ink px-5 py-4 text-sm leading-6 text-cream shadow-inner">
                {result.raw_text}
              </pre>
            </section>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                className="inline-flex rounded-full bg-ink px-5 py-3 text-sm font-extrabold text-white transition hover:bg-forest focus:outline-none focus:ring-4 focus:ring-forest/20"
                href="/"
              >
                Upload another invoice
              </Link>
              <Link
                className="inline-flex rounded-full border border-ink/15 bg-white px-5 py-3 text-sm font-extrabold text-ink transition hover:border-forest hover:text-forest focus:outline-none focus:ring-4 focus:ring-forest/20"
                href="/invoices"
              >
                View saved invoices
              </Link>
              <Link
                className="inline-flex rounded-full border border-forest/20 bg-sage/60 px-5 py-3 text-sm font-extrabold text-forest transition hover:bg-sage focus:outline-none focus:ring-4 focus:ring-forest/20"
                href="/chat"
              >
                Chat with invoices
              </Link>
            </div>
          </>
        ) : (
          <div className="text-center">
            <h1 className="font-editorial text-4xl">
              No extraction result found.
            </h1>
            <p className="mt-3 text-sm text-ink/55">
              Upload an invoice first, then the saved invoice fields will appear
              here.
            </p>
            <Link
              className="mt-7 inline-flex rounded-full bg-ink px-5 py-3 text-sm font-extrabold text-white"
              href="/"
            >
              Go to upload
            </Link>
          </div>
        )}
      </section>
    </main>
  );
}
