-- AVRONE CONTROL12 v0.26.7: immutable task settlement acknowledgements.
-- Apply AFTER 0003, on a backed-up and write-drained PostgreSQL database.
-- Do not deploy runtime v0.26.7 without this migration.
BEGIN;
CREATE TABLE settlement_receipts (
    id VARCHAR(36) PRIMARY KEY,
    tenant VARCHAR(100) NOT NULL,
    principal VARCHAR(120) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    lease_hash VARCHAR(64) NOT NULL,
    outcome VARCHAR(16) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL,
    response_payload JSON NOT NULL,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_settlement_one_per_task UNIQUE (tenant, task_id),
    CONSTRAINT fk_settlement_tenant_task FOREIGN KEY (tenant, task_id)
        REFERENCES tasks (tenant, id),
    CONSTRAINT ck_settlement_lease_digest CHECK (length(lease_hash) = 64),
    CONSTRAINT ck_settlement_payload_digest CHECK (length(payload_sha256) = 64),
    CONSTRAINT ck_settlement_outcome CHECK (outcome IN ('succeeded','failed'))
);
CREATE INDEX ix_settlement_principal ON settlement_receipts (tenant, principal, task_id);
COMMIT;
