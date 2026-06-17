PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS contractors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    nip TEXT,
    contractor_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contractors_nip
    ON contractors (nip);

CREATE TABLE IF NOT EXISTS investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    start_date TEXT,
    planned_end_date TEXT,
    budget REAL NOT NULL DEFAULT 0 CHECK (budget >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    payment_date TEXT,
    contractor_id INTEGER NOT NULL,
    investment_id INTEGER,
    category_id INTEGER,
    invoice_type TEXT NOT NULL CHECK (
        invoice_type IN (
            'COST',
            'SALES',
            'CORRECTION_COST',
            'CORRECTION_SALES'
        )
    ),
    status TEXT NOT NULL CHECK (
        status IN (
            'DRAFT_AI',
            'DRAFT_MANUAL',
            'NEEDS_REVIEW',
            'APPROVED',
            'REJECTED',
            'DELETED'
        )
    ),
    net_amount REAL NOT NULL,
    vat_amount REAL NOT NULL,
    gross_amount REAL NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'UNPAID',
    source_file TEXT,
    file_hash TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contractor_id) REFERENCES contractors (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (investment_id) REFERENCES investments (id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_invoices_number_contractor
    ON invoices (invoice_number, contractor_id);

CREATE INDEX IF NOT EXISTS idx_invoices_status
    ON invoices (status);

CREATE INDEX IF NOT EXISTS idx_invoices_investment
    ON invoices (investment_id);
