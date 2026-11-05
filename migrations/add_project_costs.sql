-- Migration: Add project_costs table for tracking expenses beyond hourly work
-- Date: 2024-01-01
-- Description: This migration adds support for tracking project costs/expenses
--              such as travel, materials, services, equipment, etc.

-- Create project_costs table
CREATE TABLE IF NOT EXISTS project_costs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    category VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR',
    billable BOOLEAN NOT NULL DEFAULT TRUE,
    invoiced BOOLEAN NOT NULL DEFAULT FALSE,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    cost_date DATE NOT NULL,
    notes TEXT,
    receipt_path VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_project_costs_project_id ON project_costs(project_id);
CREATE INDEX IF NOT EXISTS ix_project_costs_user_id ON project_costs(user_id);
CREATE INDEX IF NOT EXISTS ix_project_costs_cost_date ON project_costs(cost_date);
CREATE INDEX IF NOT EXISTS ix_project_costs_invoice_id ON project_costs(invoice_id);

-- Add comment to table
COMMENT ON TABLE project_costs IS 'Tracks project expenses beyond hourly work (travel, materials, services, etc.)';
COMMENT ON COLUMN project_costs.category IS 'Category of cost: travel, materials, services, equipment, software, other';
COMMENT ON COLUMN project_costs.billable IS 'Whether this cost should be billed to the client';
COMMENT ON COLUMN project_costs.invoiced IS 'Whether this cost has been included in an invoice';
