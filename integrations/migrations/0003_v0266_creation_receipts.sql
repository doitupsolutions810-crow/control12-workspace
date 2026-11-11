-- AVRONE CONTROL12 v0.26.6: forward-only durable creation idempotency receipts.
-- Apply after 0001 and 0002, after controlled backup, staging and write drain.
-- The service checks uniqueness at readiness; do not enable required keys before migration.
BEGIN;
CREATE TABLE creation_receipts (
    id VARCHAR(36) PRIMARY KEY,
    tenant VARCHAR(100) NOT NULL,
    principal VARCHAR(120) NOT NULL,
    method VARCHAR(8) NOT NULL,
    path VARCHAR(256) NOT NULL,
    request_key VARCHAR(128) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL,
    response_payload JSON NOT NULL,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_creation_receipt_identity UNIQUE (tenant, principal, method, path, request_key),
    CONSTRAINT ck_receipt_key_length CHECK (length(request_key) BETWEEN 16 AND 128),
    CONSTRAINT ck_receipt_digest_length CHECK (length(payload_sha256) = 64),
    CONSTRAINT ck_receipt_post_only CHECK (method = 'POST')
);
CREATE INDEX ix_receipt_lookup ON creation_receipts (tenant, principal, request_key);
COMMIT;
