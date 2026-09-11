const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UploadReceipt = {
  upload_id: string;
  status: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  message: string;
};

export type OcrResult = {
  filename: string;
  content_type: string;
  size_bytes: number;
  raw_text: string;
  message: string;
};

export type InvoiceData = {
  invoice_number: string;
  vendor_name: string;
  date: string;
  total_amount: number;
  vat: number;
  currency: string;
};

export type ExtractResult = {
  invoice_id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  raw_text: string;
  data: InvoiceData;
  message: string;
};

export type InvoiceRecord = {
  id: number;
  invoice_number: string | null;
  vendor_name: string | null;
  date: string | null;
  total_amount: number | null;
  vat: number | null;
  currency: string | null;
  raw_text: string | null;
  created_at: string;
};

export type ChatResponse = {
  answer: string;
  sql: string;
  rows: Array<Record<string, unknown>>;
};

type ErrorResponse = {
  detail?: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function uploadInvoice(file: File): Promise<UploadReceipt> {
  return postInvoiceFile<UploadReceipt>("/upload", file);
}

export async function extractInvoiceText(file: File): Promise<OcrResult> {
  return postInvoiceFile<OcrResult>("/ocr", file);
}

export async function extractInvoiceData(file: File): Promise<ExtractResult> {
  return postInvoiceFile<ExtractResult>("/extract", file);
}

export async function listInvoices(): Promise<InvoiceRecord[]> {
  return getJson<InvoiceRecord[]>("/invoices");
}

export async function getInvoice(id: number): Promise<InvoiceRecord> {
  return getJson<InvoiceRecord>(`/invoice/${id}`);
}

export async function updateInvoice(
  id: number,
  data: InvoiceData,
): Promise<InvoiceRecord> {
  return patchJson<InvoiceRecord>(`/invoice/${id}`, data);
}

export async function askInvoiceQuestion(
  question: string,
): Promise<ChatResponse> {
  return postJson<ChatResponse>("/chat", { question });
}

async function postInvoiceFile<TResponse>(
  path: "/upload" | "/ocr" | "/extract",
  file: File,
): Promise<TResponse> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ApiError(
      "Could not reach the API. Confirm FastAPI is running on port 8000.",
      0,
    );
  }

  if (!response.ok) {
    let errorBody: ErrorResponse = {};
    try {
      errorBody = (await response.json()) as ErrorResponse;
    } catch {
      // Keep the fallback message when the server does not return JSON.
    }
    throw new ApiError(
      errorBody.detail ?? "The API could not accept this invoice.",
      response.status,
    );
  }

  return (await response.json()) as TResponse;
}

async function postJson<TResponse>(
  path: "/chat",
  payload: Record<string, unknown>,
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
      method: "POST",
    });
  } catch {
    throw new ApiError(
      "Could not reach the API. Confirm FastAPI is running on port 8000.",
      0,
    );
  }

  if (!response.ok) {
    let errorBody: ErrorResponse = {};
    try {
      errorBody = (await response.json()) as ErrorResponse;
    } catch {
      // Keep the fallback message when the server does not return JSON.
    }
    throw new ApiError(
      errorBody.detail ?? "The API could not answer this invoice question.",
      response.status,
    );
  }

  return (await response.json()) as TResponse;
}

async function patchJson<TResponse>(
  path: string,
  payload: Record<string, unknown>,
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
      method: "PATCH",
    });
  } catch {
    throw new ApiError(
      "Could not reach the API. Confirm FastAPI is running on port 8000.",
      0,
    );
  }

  if (!response.ok) {
    let errorBody: ErrorResponse = {};
    try {
      errorBody = (await response.json()) as ErrorResponse;
    } catch {
      // Keep the fallback message when the server does not return JSON.
    }
    throw new ApiError(
      errorBody.detail ?? "The API could not update this invoice.",
      response.status,
    );
  }

  return (await response.json()) as TResponse;
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "GET",
    });
  } catch {
    throw new ApiError(
      "Could not reach the API. Confirm FastAPI is running on port 8000.",
      0,
    );
  }

  if (!response.ok) {
    let errorBody: ErrorResponse = {};
    try {
      errorBody = (await response.json()) as ErrorResponse;
    } catch {
      // Keep the fallback message when the server does not return JSON.
    }
    throw new ApiError(
      errorBody.detail ?? "The API could not load invoice data.",
      response.status,
    );
  }

  return (await response.json()) as TResponse;
}
