-- 0010_reference_provenance.sql  (STAGED — DO NOT RUN ON PROD UNREHEARSED)
-- @orchestrator Magnus Smárason | smarason.is  @created 2026-07-27
-- SPEC-REFERENCE-PROVENANCE-FIX v1.0: ISC-3/7/8/11.
-- Provenance store + DB-level live enforcement. Rehearse on a staging copy of
-- `arctic` first. Idempotent where practical.

BEGIN;

-- ISC-3/11: superset of every candidate ever retrieved (bound AND rejected),
-- so the reject-log lives in the same queryable place as accepted bindings and
-- section attribution is preserved going forward.
CREATE TABLE IF NOT EXISTS arctic.reference_candidates (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id      uuid NOT NULL REFERENCES arctic.species(id),
    profile_id      uuid REFERENCES arctic.conservation_profiles(id),
    reference_id    uuid REFERENCES arctic.references(id),
    query_text      text,
    section_theme   text,
    retrieved_at    timestamptz,
    retrieval_tool  text,
    retrieval_model text,
    scite_version   text,
    response_sha256 text,
    candidate_doi   text,
    candidate_title text,
    gate_method     text,          -- lexical-binomial | lexical-common | allowlist | genus-only | no-species-signal | incident-audit
    gate_verdict    text,          -- ACCEPT | REVIEW | REJECT | MISMATCH
    gate_reason     text,
    gate_checked_at timestamptz DEFAULT now(),
    binding_status  text NOT NULL DEFAULT 'pending_human'
        CHECK (binding_status IN ('bound','rejected','allowlisted','pending_human','legacy'))
);

-- ISC-3: append-only provenance event trail (one row per retrieval/gate event).
CREATE TABLE IF NOT EXISTS arctic.reference_provenance (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id  uuid NOT NULL REFERENCES arctic.reference_candidates(id),
    event_type    text NOT NULL,   -- retrieved | gated | signed_off | tombstoned
    event_at      timestamptz NOT NULL DEFAULT now(),
    detail        jsonb
);

-- ISC-6: human-expert-review sign-off. A boolean is not enough; carry rationale.
CREATE TABLE IF NOT EXISTS arctic.profile_review (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id   uuid NOT NULL REFERENCES arctic.conservation_profiles(id),
    reviewer     text NOT NULL,
    verdict      text NOT NULL CHECK (verdict IN ('approved','rejected','pending')),
    rationale    text NOT NULL,
    reviewed_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (profile_id, reviewer)
);

-- ISC-7/8: status on the live binding table (tombstone instead of delete).
ALTER TABLE arctic.profile_references
    ADD COLUMN IF NOT EXISTS binding_status text NOT NULL DEFAULT 'legacy'
        CHECK (binding_status IN ('live','rejected','legacy'));

-- ISC-7: DB-level live enforcement. References are servable ONLY for a profile
-- with an approved profile_review row AND only bindings marked 'live'. Even if
-- the API/upload layer regresses, nothing unsigned is reachable through this view.
CREATE OR REPLACE VIEW arctic.servable_profile_references AS
SELECT pr.*
FROM arctic.profile_references pr
JOIN arctic.conservation_profiles p ON p.id = pr.profile_id
WHERE pr.binding_status = 'live'
  AND EXISTS (
      SELECT 1 FROM arctic.profile_review r
      WHERE r.profile_id = p.id AND r.verdict = 'approved'
  );

COMMENT ON VIEW arctic.servable_profile_references IS
    'ISC-7: the ONLY sanctioned read path for species references. App/API must read this, not profile_references directly. Unsigned or non-live bindings are invisible here.';

CREATE INDEX IF NOT EXISTS idx_reference_candidates_species ON arctic.reference_candidates(species_id);
CREATE INDEX IF NOT EXISTS idx_reference_candidates_status  ON arctic.reference_candidates(binding_status);

COMMIT;
