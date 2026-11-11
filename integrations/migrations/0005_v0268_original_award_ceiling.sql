-- AVRONE CONTROL12 v0.26.8: preserve an operator-approved competitive task ceiling.
-- Mandatory forward migration after 0004. Use an isolated, backed-up, writer-drained PostgreSQL instance.
-- Historical cheap awards have no recoverable original cap in v0.26.7: conservatively
-- preserve their CURRENT cap as the ceiling; never reconstruct a higher limit.
BEGIN;
ALTER TABLE tasks ADD COLUMN original_cap INTEGER;
UPDATE tasks SET original_cap = cap WHERE original_cap IS NULL;
ALTER TABLE tasks ALTER COLUMN original_cap SET NOT NULL;
ALTER TABLE tasks ADD CONSTRAINT ck_tasks_original_cap
    CHECK (original_cap BETWEEN 1 AND 2000000000 AND original_cap >= cap);
COMMIT;
