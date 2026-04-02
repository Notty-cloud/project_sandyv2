-- V001__create_admins_table.sql
CREATE TABLE admins (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL,
    admin_name          VARCHAR(255) NOT NULL,
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255) NOT NULL,
    role                VARCHAR(50) NOT NULL CHECK (role IN ('teacher', 'admin', 'principal')),
    authorization_level INTEGER DEFAULT 1,           -- 1=teacher, 2=admin, 3=principal
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_admins_tenant ON admins(tenant_id);
CREATE INDEX idx_admins_email ON admins(email);
