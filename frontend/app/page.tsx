import Link from "next/link";

import { InvoiceDropzone } from "@/components/invoice-dropzone";

export default function UploadPage() {
  return (
    <main className="min-h-screen px-5 py-6 sm:px-8 sm:py-8">
      <nav className="mx-auto flex max-w-6xl items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-full bg-ink text-sm font-extrabold text-cream">
            IL
          </div>
          <div>
            <p className="text-sm font-extrabold tracking-tight">Invoice Lens</p>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ink/45">
              Processing pipeline
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            className="text-xs font-extrabold uppercase tracking-wider text-ink/55 underline decoration-ink/20 underline-offset-4 hover:text-forest"
            href="/chat"
          >
            Chat
          </Link>
          <Link
            className="text-xs font-extrabold uppercase tracking-wider text-ink/55 underline decoration-ink/20 underline-offset-4 hover:text-forest"
            href="/invoices"
          >
            Saved invoices
          </Link>
        </div>
      </nav>

      <section className="mx-auto grid max-w-6xl gap-10 py-14 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:py-24">
        <div>
          <h1 className="font-editorial max-w-xl text-5xl font-medium leading-[0.98] tracking-[-0.045em] sm:text-6xl">
            Extract invoice fields
            <br />
            and save them.
          </h1>
        </div>

        <InvoiceDropzone />
      </section>
    </main>
  );
}
