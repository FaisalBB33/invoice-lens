"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, extractInvoiceData } from "@/lib/api";

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
];
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return "Choose a PDF, PNG, JPEG, or WebP file.";
  }
  if (file.size === 0) {
    return "The selected file is empty.";
  }
  if (file.size > MAX_FILE_SIZE) {
    return "The file must be 10 MB or smaller.";
  }
  return null;
}

export function InvoiceDropzone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function chooseFile(selectedFile: File | undefined) {
    if (!selectedFile) return;
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setFile(null);
      setError(validationError);
      return;
    }
    setError(null);
    setFile(selectedFile);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    chooseFile(event.dataTransfer.files?.[0]);
  }

  async function handleUpload() {
    if (!file || isUploading) return;

    setIsUploading(true);
    setError(null);
    try {
      const result = await extractInvoiceData(file);
      window.sessionStorage.setItem(
        "invoice-extract-result",
        JSON.stringify(result),
      );
      router.push("/result");
    } catch (uploadError) {
      setError(
        uploadError instanceof ApiError
          ? uploadError.message
          : "Extraction failed. Check that the API, Tesseract, OpenAI key, and database are configured.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="rounded-[2rem] border border-white/90 bg-white/75 p-4 shadow-card backdrop-blur sm:p-6">
      <div
        className={`relative grid min-h-[21rem] place-items-center rounded-[1.4rem] border-2 border-dashed p-7 text-center transition ${
          isDragging
            ? "border-forest bg-sage/55"
            : file
              ? "border-forest/45 bg-sage/25"
              : "border-ink/15 bg-cream/45 hover:border-forest/45"
        }`}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          className="sr-only"
          onChange={handleInputChange}
          type="file"
        />

        <div>
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-white shadow-sm">
            <svg
              aria-hidden="true"
              className="h-7 w-7 text-forest"
              fill="none"
              viewBox="0 0 24 24"
            >
              <path
                d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.8"
              />
            </svg>
          </div>

          {file ? (
            <>
              <p className="mt-5 break-all text-base font-extrabold">
                {file.name}
              </p>
              <p className="mt-1 text-sm text-ink/50">
                {formatBytes(file.size)}
              </p>
              <button
                className="mt-4 text-xs font-extrabold uppercase tracking-wider text-coral underline decoration-coral/25 underline-offset-4"
                onClick={() => inputRef.current?.click()}
                type="button"
              >
                Replace file
              </button>
            </>
          ) : (
            <>
              <p className="mt-5 text-lg font-extrabold">
                Drop your invoice here
              </p>
              <p className="mt-2 text-sm text-ink/50">
                or choose one from your computer
              </p>
              <button
                className="mt-6 rounded-full border border-ink/15 bg-white px-5 py-2.5 text-sm font-extrabold transition hover:border-forest hover:text-forest focus:outline-none focus:ring-4 focus:ring-forest/15"
                onClick={() => inputRef.current?.click()}
                type="button"
              >
                Browse files
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <p
          className="mt-4 rounded-xl bg-coral/10 px-4 py-3 text-sm font-semibold text-[#a23f2a]"
          role="alert"
        >
          {error}
        </p>
      )}

      <button
        className="mt-4 flex w-full items-center justify-center rounded-full bg-ink px-5 py-3.5 text-sm font-extrabold text-white transition enabled:hover:bg-forest disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-4 focus:ring-forest/20"
        disabled={!file || isUploading}
        onClick={handleUpload}
        type="button"
      >
        {isUploading ? "Extracting and saving..." : "Extract and save invoice"}
      </button>
    </div>
  );
}
