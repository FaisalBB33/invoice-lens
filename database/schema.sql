-- Phase 4 PostgreSQL schema.
-- Apply this before using POST /extract, GET /invoices, or GET /invoice/{id}.

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number TEXT,
    vendor_name TEXT,
    date DATE,
    total_amount FLOAT,
    vat FLOAT,
    currency TEXT,
    raw_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
