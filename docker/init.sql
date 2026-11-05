-- TimeTracker Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the database schema
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    role VARCHAR(20) DEFAULT 'user' NOT NULL,  -- 'user' or 'admin'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    client VARCHAR(200) NOT NULL,
    description TEXT,
    billable BOOLEAN DEFAULT true NOT NULL,
    hourly_rate NUMERIC(9, 2),
    billing_ref VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS time_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    notes TEXT,
    tags VARCHAR(500),
    source VARCHAR(20) DEFAULT 'manual' NOT NULL,
    billable BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    timezone VARCHAR(50) DEFAULT 'Europe/Rome' NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR' NOT NULL,
    rounding_minutes INTEGER DEFAULT 1 NOT NULL,
    single_active_timer BOOLEAN DEFAULT true NOT NULL,
    allow_self_register BOOLEAN DEFAULT true NOT NULL,
    idle_timeout_minutes INTEGER DEFAULT 30 NOT NULL,
    backup_retention_days INTEGER DEFAULT 30 NOT NULL,
    backup_time VARCHAR(5) DEFAULT '02:00' NOT NULL,  -- HH:MM format
    export_delimiter VARCHAR(1) DEFAULT ',' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_time_entries_user_id ON time_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_project_id ON time_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_start_time ON time_entries(start_time);


-- Insert default admin user (password: admin)
INSERT INTO users (username, role, is_active)
VALUES ('admin', 'admin', true)
ON CONFLICT (username) DO NOTHING;

-- Insert default project
INSERT INTO projects (name, client, description, billable, status)
VALUES ('General', 'Default Client', 'Default project for general tasks', true, 'active')
ON CONFLICT DO NOTHING;



-- Insert default settings
INSERT INTO settings (timezone, currency, rounding_minutes, single_active_timer, allow_self_register, idle_timeout_minutes, backup_retention_days, backup_time, export_delimiter)
VALUES ('Europe/Rome', 'EUR', 1, true, true, 30, 30, '02:00', ',')
ON CONFLICT (id) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_time_entries_updated_at BEFORE UPDATE ON time_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO timetracker;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO timetracker;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO timetracker;
