"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, listInvoices, type InvoiceRecord } from "@/lib/api";

function formatMoney(amount: number | null, currency: string | null): string {
  if (amount === null) return "-";
  return `${currency ?? ""} ${amount.toFixed(2)}`.trim();
}

function formatDate(value: string | null): string {
  if (!value) return "-";
  return value.slice(0, 10);
}

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadInvoices() {
      try {
        setInvoices(await listInvoices());
      } catch (loadError) {
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : "Could not load invoices.",
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadInvoices();
  }, []);

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8">
      <section className="mx-auto max-w-6xl">
        <nav className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-editorial text-5xl font-medium tracking-tight">
              Saved invoices
            </h1>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              className="rounded-full border border-ink/15 bg-white px-5 py-3 text-sm font-extrabold text-ink transition hover:border-forest hover:text-forest focus:outline-none focus:ring-4 focus:ring-forest/20"
              href="/chat"
            >
              Chat
            </Link>
            <Link
              className="rounded-full bg-ink px-5 py-3 text-sm font-extrabold text-white transition hover:bg-forest focus:outline-none focus:ring-4 focus:ring-forest/20"
              href="/"
            >
              Upload invoice
            </Link>
          </div>
        </nav>

        <div className="mt-8 overflow-hidden rounded-[2rem] border border-white/80 bg-white/80 shadow-card backdrop-blur">
          {isLoading ? (
            <p className="p-6 text-sm font-semibold text-ink/55">
              Loading invoices...
            </p>
          ) : error ? (
            <p className="m-6 rounded-xl bg-coral/10 px-4 py-3 text-sm font-semibold text-[#a23f2a]">
              {error}
            </p>
          ) : invoices.length === 0 ? (
            <div className="p-8 text-center">
              <h2 className="font-editorial text-3xl">No invoices saved yet.</h2>
              <p className="mt-2 text-sm text-ink/55">
                Upload and extract an invoice first. It will appear here after
                PostgreSQL saves it.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-ink/10 text-left text-sm">
                <thead className="bg-cream/70 text-xs uppercase tracking-wider text-ink/45">
                  <tr>
                    <th className="px-5 py-4 font-extrabold">ID</th>
                    <th className="px-5 py-4 font-extrabold">Invoice #</th>
                    <th className="px-5 py-4 font-extrabold">Vendor</th>
                    <th className="px-5 py-4 font-extrabold">Date</th>
                    <th className="px-5 py-4 font-extrabold">Total</th>
                    <th className="px-5 py-4 font-extrabold">VAT</th>
                    <th className="px-5 py-4 font-extrabold">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/10">
                  {invoices.map((invoice) => (
                    <tr className="align-top" key={invoice.id}>
                      <td className="px-5 py-4 font-bold text-forest">
                        {invoice.id}
                      </td>
                      <td className="px-5 py-4 font-semibold">
                        {invoice.invoice_number ?? "-"}
                      </td>
                      <td className="px-5 py-4">
                        {invoice.vendor_name ?? "-"}
                      </td>
                      <td className="px-5 py-4">{formatDate(invoice.date)}</td>
                      <td className="px-5 py-4">
                        {formatMoney(invoice.total_amount, invoice.currency)}
                      </td>
                      <td className="px-5 py-4">
                        {formatMoney(invoice.vat, invoice.currency)}
                      </td>
                      <td className="px-5 py-4 text-ink/55">
                        {new Date(invoice.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
