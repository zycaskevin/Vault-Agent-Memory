-- Subject Distillation SQLite schema contract v15
-- This file defines physical shape; migration/version stamping is specified in design.md §14.

PRAGMA foreign_keys = ON;

CREATE TABLE subject_principals (
    principal_id TEXT PRIMARY KEY,
    principal_type TEXT NOT NULL CHECK (principal_type IN ('human','agent','service')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','revoked')),
    status_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (
        length(subject_type) BETWEEN 1 AND 64
        AND subject_type GLOB '[a-z]*'
        AND subject_type NOT GLOB '*[^a-z0-9_.-]*'
    ),
    identity_mode TEXT NOT NULL CHECK (identity_mode IN ('canonical','opaque_reference')),
    is_root INTEGER NOT NULL DEFAULT 0 CHECK (is_root IN (0,1)),
    lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active','inactive','revoked','deleted')),
    lifecycle_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    created_at TEXT NOT NULL,
    CHECK (effective_until IS NULL OR effective_until > effective_from)
);

CREATE UNIQUE INDEX ux_subjects_one_active_root
ON subjects(is_root) WHERE is_root = 1 AND lifecycle = 'active';
CREATE INDEX ix_subjects_type_lifecycle ON subjects(subject_type, lifecycle);

CREATE TABLE subject_installation (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    capability_state TEXT NOT NULL DEFAULT 'available_uninitialized'
        CHECK (capability_state IN ('available_uninitialized','initialized_empty','active','archived')),
    schema_contract_version INTEGER NOT NULL DEFAULT 15 CHECK (schema_contract_version = 15),
    root_subject_id TEXT REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    initialized_at TEXT,
    updated_at TEXT NOT NULL,
    CHECK (
        (capability_state IN ('initialized_empty','active','archived') AND root_subject_id IS NOT NULL AND initialized_at IS NOT NULL)
        OR (capability_state = 'available_uninitialized' AND root_subject_id IS NULL AND initialized_at IS NULL)
    )
);

CREATE TABLE subject_auth_bindings (
    binding_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    issued_by_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    adapter TEXT NOT NULL CHECK (adapter IN ('cli_capability','gateway_token','mcp_process','recovery_capability')),
    kdf_algorithm TEXT NOT NULL CHECK (kdf_algorithm = 'scrypt'),
    credential_salt TEXT NOT NULL CHECK (length(credential_salt) >= 22),
    credential_digest TEXT NOT NULL CHECK (length(credential_digest) >= 43),
    kdf_n INTEGER NOT NULL CHECK (kdf_n >= 16384),
    kdf_r INTEGER NOT NULL CHECK (kdf_r >= 8),
    kdf_p INTEGER NOT NULL CHECK (kdf_p >= 1),
    credential_fingerprint TEXT NOT NULL,
    issued_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','revoked')),
    expires_at TEXT,
    revoked_at TEXT,
    revocation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK ((status = 'revoked') = (revoked_at IS NOT NULL)),
    CHECK ((status = 'revoked') = (revocation_event_id IS NOT NULL)),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at)
);

CREATE UNIQUE INDEX ux_subject_auth_active_fingerprint
ON subject_auth_bindings(adapter, credential_fingerprint) WHERE status = 'active';
CREATE INDEX ix_subject_auth_principal_status ON subject_auth_bindings(principal_id, status);

CREATE TABLE subject_events (
    event_id TEXT PRIMARY KEY,
    event_kind TEXT NOT NULL CHECK (length(event_kind) BETWEEN 1 AND 64 AND event_kind NOT GLOB '*[^a-z0-9_.:-]*'),
    subject_id TEXT REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    actor_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    actor_role TEXT NOT NULL CHECK (actor_role IN ('subject','controller','reviewer','observer','consumer','authority_source','system')),
    authority_ref TEXT CHECK (authority_ref IS NULL OR (length(authority_ref) BETWEEN 1 AND 128 AND authority_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    source_ref TEXT CHECK (source_ref IS NULL OR (length(source_ref) BETWEEN 1 AND 128 AND source_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    occurred_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    audit_id TEXT NOT NULL UNIQUE
);

CREATE INDEX ix_subject_events_subject_time ON subject_events(subject_id, recorded_at);
CREATE INDEX ix_subject_events_actor_time ON subject_events(actor_principal_id, recorded_at);

CREATE TABLE subject_role_grants (
    role_grant_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('subject','controller','reviewer','observer','consumer','authority_source')),
    domain_code TEXT NOT NULL DEFAULT '',
    authority_scope TEXT NOT NULL CHECK (length(authority_scope) BETWEEN 1 AND 128 AND authority_scope NOT GLOB '*[^a-z0-9_.:-]*'),
    confirmation_quorum INTEGER NOT NULL DEFAULT 1 CHECK (confirmation_quorum >= 1),
    issued_by_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    authority_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT,
    revocation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (expires_at IS NULL OR expires_at > effective_from),
    CHECK ((revoked_at IS NULL) = (revocation_event_id IS NULL)),
    CHECK (revoked_at IS NULL OR revoked_at >= effective_from)
);

CREATE UNIQUE INDEX ux_subject_role_active
ON subject_role_grants(principal_id, subject_id, role, domain_code)
WHERE revoked_at IS NULL;
CREATE INDEX ix_subject_role_subject_role ON subject_role_grants(subject_id, role, revoked_at, expires_at);

CREATE TABLE subject_payload_objects (
    payload_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    payload_kind TEXT NOT NULL CHECK (payload_kind IN ('policy_rules','assertion_value','candidate_value','decision_event','alias_value','private_evidence','counterparty_value')),
    storage_adapter TEXT NOT NULL DEFAULT 'local_private_fs' CHECK (length(storage_adapter) BETWEEN 1 AND 80 AND storage_adapter NOT GLOB '*[^a-z0-9_.:-]*'),
    object_ref TEXT CHECK (object_ref IS NULL OR (length(object_ref) BETWEEN 1 AND 128 AND object_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    byte_count INTEGER NOT NULL DEFAULT 0 CHECK (byte_count >= 0),
    integrity_mac TEXT,
    retention_until TEXT,
    lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active','purge_pending','purged','unavailable')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    purged_at TEXT,
    CHECK (
        (lifecycle = 'active' AND object_ref IS NOT NULL AND integrity_mac IS NOT NULL AND purged_at IS NULL)
        OR (lifecycle = 'purge_pending' AND purged_at IS NULL AND (
            (object_ref IS NOT NULL AND integrity_mac IS NOT NULL)
            OR (object_ref IS NULL AND integrity_mac IS NULL AND byte_count = 0)
        ))
        OR (lifecycle = 'purged' AND object_ref IS NULL AND integrity_mac IS NULL AND byte_count = 0 AND purged_at IS NOT NULL)
        OR (lifecycle = 'unavailable' AND purged_at IS NULL)
    ),
    UNIQUE(payload_id, subject_id)
);

CREATE INDEX ix_subject_payload_subject_state ON subject_payload_objects(subject_id, lifecycle, retention_until);
CREATE UNIQUE INDEX ux_subject_payload_active_ref
ON subject_payload_objects(storage_adapter, object_ref) WHERE object_ref IS NOT NULL;

CREATE TABLE subject_purge_jobs (
    purge_job_id TEXT PRIMARY KEY,
    payload_id TEXT NOT NULL UNIQUE REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    requested_by_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    requested_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','running','retryable','succeeded','failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error_code TEXT CHECK (last_error_code IS NULL OR (length(last_error_code) BETWEEN 1 AND 64 AND last_error_code NOT GLOB '*[^a-z0-9_.:-]*')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    object_deleted_at TEXT,
    parent_fsynced_at TEXT,
    metadata_cleared_at TEXT,
    completed_at TEXT,
    CHECK ((state IN ('succeeded','failed')) = (completed_at IS NOT NULL)),
    CHECK (state NOT IN ('pending','succeeded') OR last_error_code IS NULL),
    CHECK (object_deleted_at IS NULL OR object_deleted_at >= created_at),
    CHECK (parent_fsynced_at IS NULL OR (object_deleted_at IS NOT NULL AND parent_fsynced_at >= object_deleted_at)),
    CHECK (metadata_cleared_at IS NULL OR (parent_fsynced_at IS NOT NULL AND metadata_cleared_at >= parent_fsynced_at)),
    CHECK (completed_at IS NULL OR completed_at >= created_at),
    CHECK (state <> 'succeeded' OR (metadata_cleared_at IS NOT NULL AND completed_at >= metadata_cleared_at))
);

CREATE INDEX ix_subject_purge_state ON subject_purge_jobs(state, updated_at);

CREATE TABLE subject_policies (
    policy_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    policy_kind TEXT NOT NULL CHECK (policy_kind IN ('privacy','review','delegation','retention','counterparty','evaluation','model','access')),
    version INTEGER NOT NULL CHECK (version >= 1),
    rules_payload_id TEXT NOT NULL REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sealed','superseded','revoked')),
    approved_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    supersedes_policy_id TEXT REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (effective_until IS NULL OR effective_until > effective_from),
    CHECK ((status = 'draft') OR approved_event_id IS NOT NULL),
    UNIQUE(subject_id, policy_kind, version)
);

CREATE UNIQUE INDEX ux_subject_policy_current
ON subject_policies(subject_id, policy_kind) WHERE status = 'sealed' AND effective_until IS NULL;

CREATE TABLE subject_delegation_rules (
    delegation_rule_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    domain_code TEXT NOT NULL CHECK (length(domain_code) BETWEEN 1 AND 64 AND domain_code NOT GLOB '*[^a-z0-9_.:-]*'),
    stakes TEXT NOT NULL CHECK (stakes IN ('low','medium','high')),
    reversibility TEXT NOT NULL CHECK (reversibility IN ('reversible','partially_reversible','irreversible')),
    cost_ceiling_minor INTEGER NOT NULL CHECK (cost_ceiling_minor >= 0),
    currency_code TEXT NOT NULL CHECK (length(currency_code) = 3),
    approval_mode TEXT NOT NULL CHECK (approval_mode IN ('advisory_only','explicit_each_time','bounded_autonomy')),
    effective_from TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    revocation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (expires_at > effective_from),
    CHECK ((revoked_at IS NULL) = (revocation_event_id IS NULL)),
    CHECK (revoked_at IS NULL OR revoked_at >= effective_from),
    CHECK (NOT (stakes = 'high' OR reversibility = 'irreversible') OR approval_mode <> 'bounded_autonomy')
);

CREATE INDEX ix_subject_delegation_lookup
ON subject_delegation_rules(policy_id, domain_code, stakes, revoked_at, expires_at);

CREATE TABLE subject_access_grants (
    access_grant_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    consumer_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    purpose_code TEXT CHECK (purpose_code IS NULL OR (length(purpose_code) BETWEEN 1 AND 64 AND purpose_code NOT GLOB '*[^a-z0-9_.:-]*')),
    purpose_ref TEXT CHECK (purpose_ref IS NULL OR (length(purpose_ref) BETWEEN 1 AND 128 AND purpose_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    task_ref TEXT CHECK (task_ref IS NULL OR (length(task_ref) BETWEEN 1 AND 128 AND task_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    domain_code TEXT NOT NULL CHECK (length(domain_code) BETWEEN 1 AND 64 AND domain_code NOT GLOB '*[^a-z0-9_.:-]*'),
    output_kinds TEXT NOT NULL CHECK (length(output_kinds) BETWEEN 1 AND 256 AND output_kinds NOT GLOB '*[^a-z0-9_.:,-]*'),
    sensitivity_ceiling TEXT NOT NULL CHECK (sensitivity_ceiling IN ('public','internal','private','restricted')),
    policy_id TEXT NOT NULL REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    issued_by_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    authority_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    revocation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK ((purpose_code IS NOT NULL) <> (purpose_ref IS NOT NULL)),
    CHECK (expires_at > effective_from),
    CHECK ((revoked_at IS NULL) = (revocation_event_id IS NULL)),
    CHECK (revoked_at IS NULL OR revoked_at >= effective_from)
);

CREATE INDEX ix_subject_access_lookup
ON subject_access_grants(subject_id, consumer_principal_id, domain_code, revoked_at, expires_at);

CREATE TABLE subject_counterparty_controls (
    counterparty_control_id TEXT PRIMARY KEY,
    primary_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    counterparty_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_id TEXT REFERENCES subject_relationships(relationship_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    processing_basis TEXT NOT NULL CHECK (processing_basis IN ('subject_perspective_only','counterparty_consent','legal_obligation')),
    authority_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    purpose_code TEXT NOT NULL CHECK (
        length(purpose_code) BETWEEN 1 AND 64
        AND purpose_code GLOB '[a-z]*'
        AND purpose_code NOT GLOB '*[^a-z0-9_.:-]*'
    ),
    allow_store INTEGER NOT NULL DEFAULT 0 CHECK (allow_store IN (0,1)),
    allow_model INTEGER NOT NULL DEFAULT 0 CHECK (allow_model IN (0,1)),
    allow_export INTEGER NOT NULL DEFAULT 0 CHECK (allow_export IN (0,1)),
    export_mode TEXT NOT NULL DEFAULT 'none' CHECK (export_mode IN ('none','primary_perspective_only','counterparty_self','bilateral')),
    legal_policy_id TEXT REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    legal_policy_version INTEGER CHECK (legal_policy_version IS NULL OR legal_policy_version >= 1),
    retention_until TEXT NOT NULL,
    legal_hold_until TEXT,
    legal_hold_authority_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    legal_hold_policy_id TEXT REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    legal_hold_policy_version INTEGER CHECK (legal_hold_policy_version IS NULL OR legal_hold_policy_version >= 1),
    deletion_state TEXT NOT NULL DEFAULT 'active' CHECK (deletion_state IN ('active','purge_pending','purged','deidentified')),
    deletion_requested_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    deletion_completed_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    revocation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    supersedes_counterparty_control_id TEXT REFERENCES subject_counterparty_controls(counterparty_control_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    CHECK (primary_subject_id <> counterparty_subject_id),
    CHECK (allow_store + allow_model + allow_export >= 1),
    CHECK ((allow_export = 0 AND export_mode = 'none') OR (allow_export = 1 AND export_mode <> 'none')),
    CHECK (processing_basis <> 'subject_perspective_only' OR export_mode IN ('none','primary_perspective_only')),
    CHECK (processing_basis NOT IN ('counterparty_consent','legal_obligation') OR (legal_policy_id IS NOT NULL AND legal_policy_version IS NOT NULL)),
    CHECK (processing_basis IN ('counterparty_consent','legal_obligation') OR (legal_policy_id IS NULL AND legal_policy_version IS NULL)),
    CHECK (
        (deletion_state = 'active' AND deletion_requested_event_id IS NULL AND deletion_completed_event_id IS NULL)
        OR (deletion_state = 'purge_pending' AND deletion_requested_event_id IS NOT NULL AND deletion_completed_event_id IS NULL)
        OR (deletion_state IN ('purged','deidentified') AND deletion_requested_event_id IS NOT NULL AND deletion_completed_event_id IS NOT NULL)
    ),
    CHECK ((revoked_at IS NULL) = (revocation_event_id IS NULL)),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at),
    CHECK (retention_until >= created_at),
    CHECK (
        (legal_hold_until IS NULL AND legal_hold_authority_event_id IS NULL AND legal_hold_policy_id IS NULL AND legal_hold_policy_version IS NULL)
        OR (
            legal_hold_until > created_at
            AND legal_hold_authority_event_id IS NOT NULL
            AND legal_hold_policy_id IS NOT NULL
            AND legal_hold_policy_version IS NOT NULL
        )
    )
);

CREATE INDEX ix_subject_counterparty_scope
ON subject_counterparty_controls(primary_subject_id, counterparty_subject_id, deletion_state, revoked_at, retention_until);
CREATE UNIQUE INDEX ux_subject_counterparty_current
ON subject_counterparty_controls(primary_subject_id, counterparty_subject_id, purpose_code)
WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX ux_subject_counterparty_deletion_request_event
ON subject_counterparty_controls(deletion_requested_event_id)
WHERE deletion_requested_event_id IS NOT NULL;

CREATE TABLE subject_evidence (
    evidence_id TEXT PRIMARY KEY,
    controller_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    about_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    retention_mode TEXT NOT NULL CHECK (retention_mode IN ('pointer_only','private_copy','ephemeral')),
    source_kind TEXT NOT NULL CHECK (length(source_kind) BETWEEN 1 AND 64 AND source_kind NOT GLOB '*[^a-z0-9_.:-]*'),
    source_ref TEXT NOT NULL CHECK (length(source_ref) BETWEEN 1 AND 128 AND source_ref NOT GLOB '*[^a-z0-9_.:-]*'),
    locator_ref TEXT CHECK (locator_ref IS NULL OR (length(locator_ref) BETWEEN 1 AND 128 AND locator_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    integrity_mac TEXT NOT NULL,
    availability TEXT NOT NULL CHECK (availability IN ('available','unavailable','revoked','expired','unverifiable')),
    sensitivity TEXT NOT NULL CHECK (sensitivity IN ('public','internal','private','restricted')),
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    retention_until TEXT,
    private_payload_id TEXT REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    supersedes_evidence_id TEXT REFERENCES subject_evidence(evidence_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (effective_until IS NULL OR effective_until > effective_from),
    CHECK ((retention_mode = 'private_copy') = (private_payload_id IS NOT NULL)),
    CHECK (retention_mode <> 'ephemeral' OR private_payload_id IS NULL),
    FOREIGN KEY (private_payload_id, about_subject_id) REFERENCES subject_payload_objects(payload_id, subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX ix_subject_evidence_subject_state
ON subject_evidence(about_subject_id, availability, sensitivity, effective_from, effective_until);

CREATE TABLE subject_assertions (
    assertion_id TEXT PRIMARY KEY,
    model_owner_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    about_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    namespace TEXT NOT NULL CHECK (namespace IN ('canonical','relationship_experience','perspective')),
    relationship_id TEXT REFERENCES subject_relationships(relationship_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    assertion_class TEXT NOT NULL CHECK (assertion_class IN ('explicit','controller_attested','third_party_reported','observed','inferred','aspirational','strategic','recommendation')),
    semantic_kind TEXT NOT NULL CHECK (length(semantic_kind) BETWEEN 1 AND 64 AND semantic_kind NOT GLOB '*[^a-z0-9_.:-]*'),
    domain_code TEXT NOT NULL CHECK (length(domain_code) BETWEEN 1 AND 64 AND domain_code NOT GLOB '*[^a-z0-9_.:-]*'),
    value_payload_id TEXT REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    value_state TEXT NOT NULL CHECK (value_state IN ('known','unknown','withheld','unavailable')),
    lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active','superseded','revoked','expired','deleted')),
    actor_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    actor_role TEXT NOT NULL CHECK (actor_role IN ('subject','controller','reviewer','observer','consumer','authority_source','system')),
    authority_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    confirmation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    termination_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sensitivity TEXT NOT NULL CHECK (sensitivity IN ('public','internal','private','restricted')),
    policy_id TEXT REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    supersedes_assertion_id TEXT REFERENCES subject_assertions(assertion_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    recorded_at TEXT NOT NULL,
    CHECK (effective_until IS NULL OR effective_until > effective_from),
    CHECK ((value_state = 'known') = (value_payload_id IS NOT NULL)),
    CHECK (assertion_class <> 'explicit' OR (confirmation_event_id IS NOT NULL AND actor_role = 'subject')),
    CHECK (assertion_class <> 'inferred' OR confidence IS NOT NULL),
    CHECK (
        (lifecycle = 'active' AND termination_event_id IS NULL)
        OR (lifecycle IN ('superseded','revoked','expired','deleted') AND termination_event_id IS NOT NULL AND effective_until IS NOT NULL)
    ),
    CHECK (
        (namespace = 'canonical' AND model_owner_subject_id = about_subject_id AND relationship_id IS NULL)
        OR (namespace = 'relationship_experience' AND model_owner_subject_id = about_subject_id AND relationship_id IS NOT NULL)
        OR (namespace = 'perspective' AND model_owner_subject_id <> about_subject_id AND relationship_id IS NOT NULL)
    ),
    FOREIGN KEY (value_payload_id, model_owner_subject_id) REFERENCES subject_payload_objects(payload_id, subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX ix_subject_assertion_current
ON subject_assertions(about_subject_id, domain_code, assertion_class, lifecycle, effective_from, effective_until);
CREATE INDEX ix_subject_assertion_owner_namespace
ON subject_assertions(model_owner_subject_id, namespace, lifecycle);

CREATE TABLE subject_assertion_evidence (
    assertion_id TEXT NOT NULL REFERENCES subject_assertions(assertion_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    evidence_id TEXT NOT NULL REFERENCES subject_evidence(evidence_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    polarity TEXT NOT NULL CHECK (polarity IN ('support','counter')),
    weight REAL NOT NULL DEFAULT 1.0 CHECK (weight >= 0.0 AND weight <= 1.0),
    notes_integrity_mac TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY(assertion_id, evidence_id, polarity)
);

CREATE INDEX ix_subject_assertion_evidence_evidence ON subject_assertion_evidence(evidence_id, polarity);

CREATE TABLE subject_candidate_payloads (
    candidate_id TEXT PRIMARY KEY REFERENCES memory_candidates(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    candidate_kind TEXT NOT NULL CHECK (candidate_kind LIKE 'subject_%'),
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    payload_contract_version INTEGER NOT NULL DEFAULT 1 CHECK (payload_contract_version = 1),
    payload_id TEXT NOT NULL REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    integrity_mac TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (payload_id, subject_id) REFERENCES subject_payload_objects(payload_id, subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX ix_subject_candidate_subject_kind ON subject_candidate_payloads(subject_id, candidate_kind);

CREATE TABLE subject_candidate_reviews (
    candidate_review_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES subject_candidate_payloads(candidate_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    reviewer_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    reviewer_role TEXT NOT NULL CHECK (reviewer_role IN ('subject','controller','reviewer')),
    decision TEXT NOT NULL CHECK (decision IN ('approve','reject','block','request_changes')),
    reason_code TEXT NOT NULL CHECK (length(reason_code) BETWEEN 1 AND 64 AND reason_code NOT GLOB '*[^a-z0-9_.:-]*'),
    reason_integrity_mac TEXT,
    reviewed_at TEXT NOT NULL
);

CREATE INDEX ix_subject_candidate_review_candidate ON subject_candidate_reviews(candidate_id, reviewed_at);

CREATE TABLE subject_models (
    model_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    version INTEGER NOT NULL CHECK (version >= 1),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sealed','superseded','revoked')),
    generated_at TEXT NOT NULL,
    data_window_start TEXT NOT NULL,
    data_window_end TEXT NOT NULL,
    policy_id TEXT NOT NULL REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    producer_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    coverage_entry_count INTEGER NOT NULL DEFAULT 0 CHECK (coverage_entry_count >= 0),
    coverage_unknown_count INTEGER NOT NULL DEFAULT 0 CHECK (coverage_unknown_count >= 0),
    coverage_withheld_count INTEGER NOT NULL DEFAULT 0 CHECK (coverage_withheld_count >= 0),
    coverage_unavailable_count INTEGER NOT NULL DEFAULT 0 CHECK (coverage_unavailable_count >= 0),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    value_state TEXT NOT NULL CHECK (value_state IN ('known','unknown','withheld','unavailable')),
    integrity_mac TEXT NOT NULL,
    supersedes_model_id TEXT REFERENCES subject_models(model_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (data_window_end >= data_window_start),
    CHECK (generated_at <= created_at),
    UNIQUE(subject_id, version)
);

CREATE UNIQUE INDEX ux_subject_model_current
ON subject_models(subject_id) WHERE status = 'sealed';

CREATE TABLE subject_model_entries (
    model_entry_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES subject_models(model_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    output_kind TEXT NOT NULL CHECK (output_kind IN ('descriptive','aspirational','decision_policy','delegation_policy')),
    source_type TEXT NOT NULL CHECK (source_type IN ('assertion','policy')),
    source_id TEXT NOT NULL,
    domain_code TEXT NOT NULL CHECK (length(domain_code) BETWEEN 1 AND 64 AND domain_code NOT GLOB '*[^a-z0-9_.:-]*'),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    rendered_integrity_mac TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(model_id, output_kind, ordinal)
);

CREATE INDEX ix_subject_model_entry_source ON subject_model_entries(source_type, source_id);

CREATE TABLE subject_context_pack_runs (
    pack_run_id TEXT PRIMARY KEY,
    pack_contract_version INTEGER NOT NULL DEFAULT 1 CHECK (pack_contract_version = 1),
    state TEXT NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','sealed')),
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    model_id TEXT NOT NULL REFERENCES subject_models(model_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    access_grant_id TEXT NOT NULL REFERENCES subject_access_grants(access_grant_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    consumer_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    purpose_code TEXT CHECK (purpose_code IS NULL OR (length(purpose_code) BETWEEN 1 AND 64 AND purpose_code NOT GLOB '*[^a-z0-9_.:-]*')),
    purpose_ref TEXT CHECK (purpose_ref IS NULL OR (length(purpose_ref) BETWEEN 1 AND 128 AND purpose_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    task_ref TEXT CHECK (task_ref IS NULL OR (length(task_ref) BETWEEN 1 AND 128 AND task_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    policy_id TEXT NOT NULL REFERENCES subject_policies(policy_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    generated_at TEXT NOT NULL,
    included_entry_count INTEGER NOT NULL DEFAULT 0 CHECK (included_entry_count >= 0),
    coverage_unknown_count INTEGER NOT NULL DEFAULT 0 CHECK (coverage_unknown_count >= 0),
    excluded_auth_count INTEGER NOT NULL DEFAULT 0 CHECK (excluded_auth_count >= 0),
    excluded_grant_count INTEGER NOT NULL DEFAULT 0 CHECK (excluded_grant_count >= 0),
    excluded_purpose_count INTEGER NOT NULL DEFAULT 0 CHECK (excluded_purpose_count >= 0),
    excluded_domain_count INTEGER NOT NULL DEFAULT 0 CHECK (excluded_domain_count >= 0),
    excluded_sensitivity_count INTEGER NOT NULL DEFAULT 0 CHECK (excluded_sensitivity_count >= 0),
    excluded_minimization_count INTEGER NOT NULL DEFAULT 0 CHECK (excluded_minimization_count >= 0),
    content_integrity_mac TEXT,
    sealed_at TEXT,
    action_authority INTEGER NOT NULL DEFAULT 0 CHECK (action_authority IN (0,1)),
    delegation_rule_id TEXT REFERENCES subject_delegation_rules(delegation_rule_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    action_domain_code TEXT CHECK (action_domain_code IS NULL OR (length(action_domain_code) BETWEEN 1 AND 64 AND action_domain_code NOT GLOB '*[^a-z0-9_.:-]*')),
    action_stakes TEXT CHECK (action_stakes IS NULL OR action_stakes IN ('low','medium','high')),
    action_reversibility TEXT CHECK (action_reversibility IS NULL OR action_reversibility IN ('reversible','partially_reversible','irreversible')),
    action_cost_minor INTEGER CHECK (action_cost_minor IS NULL OR action_cost_minor >= 0),
    action_currency_code TEXT CHECK (action_currency_code IS NULL OR length(action_currency_code) = 3),
    CHECK ((purpose_code IS NOT NULL) <> (purpose_ref IS NOT NULL)),
    CHECK ((action_authority = 1) = (delegation_rule_id IS NOT NULL)),
    CHECK ((action_authority = 1) = (action_domain_code IS NOT NULL)),
    CHECK ((action_authority = 1) = (action_stakes IS NOT NULL)),
    CHECK ((action_authority = 1) = (action_reversibility IS NOT NULL)),
    CHECK ((action_authority = 1) = (action_cost_minor IS NOT NULL)),
    CHECK ((action_authority = 1) = (action_currency_code IS NOT NULL)),
    CHECK (
        (state = 'draft' AND content_integrity_mac IS NULL AND sealed_at IS NULL)
        OR (state = 'sealed' AND content_integrity_mac IS NOT NULL AND sealed_at IS NOT NULL)
    )
);

CREATE INDEX ix_subject_pack_subject_consumer ON subject_context_pack_runs(subject_id, consumer_principal_id, generated_at);

CREATE TABLE subject_context_pack_entries (
    pack_run_id TEXT NOT NULL REFERENCES subject_context_pack_runs(pack_run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    source_type TEXT NOT NULL CHECK (source_type IN ('assertion','policy','model_entry')),
    source_id TEXT NOT NULL,
    rendered_integrity_mac TEXT NOT NULL,
    PRIMARY KEY(pack_run_id, ordinal)
);

CREATE TABLE decision_episodes (
    episode_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    domain_code TEXT NOT NULL CHECK (length(domain_code) BETWEEN 1 AND 64 AND domain_code NOT GLOB '*[^a-z0-9_.:-]*'),
    lifecycle TEXT NOT NULL DEFAULT 'open' CHECK (lifecycle IN ('open','closed','revoked')),
    review_state TEXT NOT NULL DEFAULT 'unreviewed' CHECK (review_state IN ('unreviewed','reviewed','disputed')),
    created_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    projection_integrity_mac TEXT NOT NULL,
    projected_through_sequence INTEGER NOT NULL DEFAULT 0 CHECK (projected_through_sequence >= 0),
    created_at TEXT NOT NULL
);

CREATE INDEX ix_decision_episode_subject_domain ON decision_episodes(subject_id, domain_code, lifecycle);

CREATE TABLE decision_episode_events (
    decision_event_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES decision_episodes(episode_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sequence INTEGER NOT NULL CHECK (sequence >= 1),
    event_kind TEXT NOT NULL CHECK (event_kind IN ('created','context_set','options_set','constraints_set','recommendation_added','prediction_added','actual_choice_confirmed','subject_reason_added','outcome_added','feedback_added','reviewed','corrected','episode_closed','episode_revoked')),
    actor_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    actor_role TEXT NOT NULL CHECK (actor_role IN ('subject','controller','reviewer','agent','service')),
    authority_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_ref TEXT CHECK (source_ref IS NULL OR (length(source_ref) BETWEEN 1 AND 128 AND source_ref NOT GLOB '*[^a-z0-9_.:-]*')),
    payload_id TEXT REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    occurred_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    UNIQUE(episode_id, sequence)
);

CREATE INDEX ix_decision_event_episode_kind ON decision_episode_events(episode_id, event_kind, sequence);

CREATE TABLE subject_relationships (
    relationship_id TEXT PRIMARY KEY,
    from_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    to_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    formal_type TEXT NOT NULL CHECK (length(formal_type) BETWEEN 1 AND 64 AND formal_type NOT GLOB '*[^a-z0-9_.:-]*'),
    source_role TEXT NOT NULL CHECK (length(source_role) BETWEEN 1 AND 64 AND source_role NOT GLOB '*[^a-z0-9_.:-]*'),
    counterparty_role TEXT NOT NULL CHECK (length(counterparty_role) BETWEEN 1 AND 64 AND counterparty_role NOT GLOB '*[^a-z0-9_.:-]*'),
    lived_state TEXT NOT NULL CHECK (length(lived_state) BETWEEN 1 AND 64 AND lived_state NOT GLOB '*[^a-z0-9_.:-]*'),
    sensitivity TEXT NOT NULL CHECK (sensitivity IN ('public','internal','private','restricted')),
    provenance_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active','ended','revoked','deleted')),
    termination_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    created_at TEXT NOT NULL,
    CHECK (from_subject_id <> to_subject_id),
    CHECK (effective_until IS NULL OR effective_until > effective_from),
    CHECK ((lifecycle = 'active' AND termination_event_id IS NULL) OR (lifecycle <> 'active' AND termination_event_id IS NOT NULL AND effective_until IS NOT NULL))
);

CREATE INDEX ix_subject_relationship_from_time ON subject_relationships(from_subject_id, lifecycle, effective_from, effective_until);
CREATE INDEX ix_subject_relationship_to_time ON subject_relationships(to_subject_id, lifecycle, effective_from, effective_until);

CREATE TABLE subject_aliases (
    alias_id TEXT PRIMARY KEY,
    controller_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    referenced_subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_id TEXT REFERENCES subject_relationships(relationship_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    alias_payload_id TEXT NOT NULL REFERENCES subject_payload_objects(payload_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    purpose_code TEXT NOT NULL CHECK (length(purpose_code) BETWEEN 1 AND 64 AND purpose_code NOT GLOB '*[^a-z0-9_.:-]*'),
    sensitivity TEXT NOT NULL CHECK (sensitivity IN ('public','internal','private','restricted')),
    authority_event_id TEXT NOT NULL REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    revocation_event_id TEXT REFERENCES subject_events(event_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CHECK (controller_subject_id <> referenced_subject_id),
    CHECK (effective_until IS NULL OR effective_until > effective_from),
    CHECK ((revoked_at IS NULL) = (revocation_event_id IS NULL)),
    CHECK (revoked_at IS NULL OR revoked_at >= effective_from)
);

CREATE INDEX ix_subject_alias_lookup ON subject_aliases(controller_subject_id, referenced_subject_id, revoked_at, effective_until);

CREATE TABLE subject_evaluation_gates (
    gate_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    gate_version INTEGER NOT NULL CHECK (gate_version >= 1),
    manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64 AND manifest_sha256 = lower(manifest_sha256) AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'),
    eligibility_rules_version TEXT NOT NULL CHECK (length(eligibility_rules_version) BETWEEN 1 AND 64 AND eligibility_rules_version NOT GLOB '*[^a-z0-9_.:-]*'),
    eligibility_rules_sha256 TEXT NOT NULL CHECK (length(eligibility_rules_sha256) = 64 AND eligibility_rules_sha256 = lower(eligibility_rules_sha256) AND eligibility_rules_sha256 NOT GLOB '*[^0-9a-f]*'),
    exclusion_rules_version TEXT NOT NULL CHECK (length(exclusion_rules_version) BETWEEN 1 AND 64 AND exclusion_rules_version NOT GLOB '*[^a-z0-9_.:-]*'),
    exclusion_rules_sha256 TEXT NOT NULL CHECK (length(exclusion_rules_sha256) = 64 AND exclusion_rules_sha256 = lower(exclusion_rules_sha256) AND exclusion_rules_sha256 NOT GLOB '*[^0-9a-f]*'),
    denominator_rule TEXT NOT NULL DEFAULT 'all_completed_eligible_preregistered'
        CHECK (denominator_rule = 'all_completed_eligible_preregistered'),
    minimum_n INTEGER NOT NULL DEFAULT 20 CHECK (minimum_n >= 20),
    rounding_rule TEXT NOT NULL CHECK (rounding_rule = 'ceil'),
    utility_threshold REAL NOT NULL DEFAULT 0.80 CHECK (utility_threshold BETWEEN 0.0 AND 1.0),
    reason_alignment_threshold REAL NOT NULL DEFAULT 0.80 CHECK (reason_alignment_threshold BETWEEN 0.0 AND 1.0),
    abstention_minimum REAL NOT NULL DEFAULT 0.80 CHECK (abstention_minimum BETWEEN 0.0 AND 1.0),
    domain_utility_threshold REAL NOT NULL DEFAULT 0.60 CHECK (domain_utility_threshold BETWEEN 0.0 AND 1.0),
    high_confidence_threshold REAL NOT NULL DEFAULT 0.80 CHECK (high_confidence_threshold BETWEEN 0.0 AND 1.0),
    hard_failure_rules_version TEXT NOT NULL CHECK (length(hard_failure_rules_version) BETWEEN 1 AND 64 AND hard_failure_rules_version NOT GLOB '*[^a-z0-9_.:-]*'),
    hard_failure_rules_sha256 TEXT NOT NULL CHECK (length(hard_failure_rules_sha256) = 64 AND hard_failure_rules_sha256 = lower(hard_failure_rules_sha256) AND hard_failure_rules_sha256 NOT GLOB '*[^0-9a-f]*'),
    scoring_definitions_version TEXT NOT NULL CHECK (length(scoring_definitions_version) BETWEEN 1 AND 64 AND scoring_definitions_version NOT GLOB '*[^a-z0-9_.:-]*'),
    scoring_definitions_sha256 TEXT NOT NULL CHECK (length(scoring_definitions_sha256) = 64 AND scoring_definitions_sha256 = lower(scoring_definitions_sha256) AND scoring_definitions_sha256 NOT GLOB '*[^0-9a-f]*'),
    reviewer_authority_code TEXT NOT NULL CHECK (length(reviewer_authority_code) BETWEEN 1 AND 64 AND reviewer_authority_code NOT GLOB '*[^a-z0-9_.:-]*'),
    state TEXT NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','frozen','closed')),
    frozen_at TEXT,
    closed_at TEXT,
    scorecard_sha256 TEXT CHECK (scorecard_sha256 IS NULL OR (length(scorecard_sha256) = 64 AND scorecard_sha256 = lower(scorecard_sha256) AND scorecard_sha256 NOT GLOB '*[^0-9a-f]*')),
    verdict TEXT CHECK (verdict IS NULL OR verdict IN ('pass','fail','blocked')),
    created_at TEXT NOT NULL,
    CHECK ((state = 'draft' AND frozen_at IS NULL AND closed_at IS NULL AND verdict IS NULL)
        OR (state = 'frozen' AND frozen_at IS NOT NULL AND closed_at IS NULL AND verdict IS NULL)
        OR (state = 'closed' AND frozen_at IS NOT NULL AND closed_at IS NOT NULL AND verdict IS NOT NULL)),
    UNIQUE(subject_id, gate_version),
    CHECK (
        gate_version <> 1 OR (
            minimum_n = 20
            AND utility_threshold = 0.80
            AND reason_alignment_threshold = 0.80
            AND abstention_minimum = 0.80
            AND domain_utility_threshold = 0.60
            AND high_confidence_threshold = 0.80
        )
    )
);

CREATE TABLE subject_evaluation_cases (
    evaluation_case_id TEXT PRIMARY KEY,
    gate_id TEXT NOT NULL REFERENCES subject_evaluation_gates(gate_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    case_integrity_mac TEXT NOT NULL,
    primary_domain TEXT NOT NULL CHECK (length(primary_domain) BETWEEN 1 AND 64 AND primary_domain NOT GLOB '*[^a-z0-9_.:-]*'),
    is_abstention INTEGER NOT NULL DEFAULT 0 CHECK (is_abstention IN (0,1)),
    has_subject_correction INTEGER NOT NULL DEFAULT 0 CHECK (has_subject_correction IN (0,1)),
    has_counter_evidence INTEGER NOT NULL DEFAULT 0 CHECK (has_counter_evidence IN (0,1)),
    has_contextual_constraint INTEGER NOT NULL DEFAULT 0 CHECK (has_contextual_constraint IN (0,1)),
    eligible INTEGER NOT NULL CHECK (eligible IN (0,1)),
    preregistered_exclusion_code TEXT CHECK (preregistered_exclusion_code IS NULL OR (length(preregistered_exclusion_code) BETWEEN 1 AND 64 AND preregistered_exclusion_code NOT GLOB '*[^a-z0-9_.:-]*')),
    completion_state TEXT NOT NULL DEFAULT 'preregistered' CHECK (completion_state IN ('preregistered','completed','excluded','incomplete')),
    disposition_at TEXT,
    created_at TEXT NOT NULL,
    CHECK ((completion_state = 'preregistered' AND disposition_at IS NULL) OR (completion_state <> 'preregistered' AND disposition_at IS NOT NULL)),
    UNIQUE(gate_id, case_integrity_mac),
    UNIQUE(gate_id, evaluation_case_id)
);

CREATE INDEX ix_subject_eval_case_domain ON subject_evaluation_cases(gate_id, primary_domain, eligible);

CREATE TABLE subject_evaluation_events (
    evaluation_event_id TEXT PRIMARY KEY,
    gate_id TEXT NOT NULL,
    evaluation_case_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('utility','reason_alignment','abstention','hard_failure','domain_score','correction','source_gap')),
    metric_value REAL,
    passed INTEGER CHECK (passed IS NULL OR passed IN (0,1)),
    reason_code TEXT CHECK (reason_code IS NULL OR (length(reason_code) BETWEEN 1 AND 64 AND reason_code NOT GLOB '*[^a-z0-9_.:-]*')),
    actor_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_ref TEXT NOT NULL CHECK (length(source_ref) BETWEEN 1 AND 128 AND source_ref NOT GLOB '*[^a-z0-9_.:-]*'),
    occurred_at TEXT NOT NULL,
    audit_id TEXT NOT NULL UNIQUE,
    CHECK (
        (event_type IN ('utility','reason_alignment','abstention','domain_score') AND metric_value IS NOT NULL AND metric_value IN (0.0,1.0) AND passed = CAST(metric_value AS INTEGER) AND reason_code IS NOT NULL)
        OR (event_type = 'hard_failure' AND metric_value IS NULL AND passed IS NOT NULL AND reason_code IS NOT NULL)
        OR (event_type IN ('correction','source_gap') AND metric_value IS NULL AND passed IS NULL AND reason_code IS NOT NULL)
    ),
    FOREIGN KEY (gate_id, evaluation_case_id) REFERENCES subject_evaluation_cases(gate_id, evaluation_case_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    UNIQUE(gate_id, evaluation_case_id, event_type)
);

CREATE INDEX ix_subject_eval_event_case ON subject_evaluation_events(gate_id, evaluation_case_id, event_type);

CREATE TABLE subject_evaluation_prediction_assessments (
    prediction_assessment_id TEXT PRIMARY KEY,
    gate_id TEXT NOT NULL,
    evaluation_case_id TEXT NOT NULL,
    assessment_status TEXT NOT NULL CHECK (assessment_status IN ('not_emitted','reviewed')),
    predicted_choice_sha256 TEXT CHECK (predicted_choice_sha256 IS NULL OR (length(predicted_choice_sha256) = 64 AND predicted_choice_sha256 = lower(predicted_choice_sha256) AND predicted_choice_sha256 NOT GLOB '*[^0-9a-f]*')),
    prediction_confidence REAL CHECK (prediction_confidence IS NULL OR prediction_confidence BETWEEN 0.0 AND 1.0),
    actual_choice_sha256 TEXT CHECK (actual_choice_sha256 IS NULL OR (length(actual_choice_sha256) = 64 AND actual_choice_sha256 = lower(actual_choice_sha256) AND actual_choice_sha256 NOT GLOB '*[^0-9a-f]*')),
    prediction_correct INTEGER CHECK (prediction_correct IS NULL OR prediction_correct IN (0,1)),
    subject_principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    source_ref TEXT NOT NULL CHECK (length(source_ref) BETWEEN 1 AND 128 AND source_ref NOT GLOB '*[^a-z0-9_.:-]*'),
    assessed_at TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    audit_id TEXT NOT NULL UNIQUE,
    CHECK (reviewed_at >= assessed_at),
    CHECK (
        (assessment_status = 'not_emitted' AND predicted_choice_sha256 IS NULL AND prediction_confidence IS NULL
            AND actual_choice_sha256 IS NULL AND prediction_correct IS NULL)
        OR
        (assessment_status = 'reviewed' AND predicted_choice_sha256 IS NOT NULL AND prediction_confidence IS NOT NULL
            AND actual_choice_sha256 IS NOT NULL AND prediction_correct IS NOT NULL
            AND prediction_correct = (predicted_choice_sha256 = actual_choice_sha256))
    ),
    FOREIGN KEY (gate_id, evaluation_case_id) REFERENCES subject_evaluation_cases(gate_id, evaluation_case_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    UNIQUE(gate_id, evaluation_case_id)
);

CREATE INDEX ix_subject_eval_prediction_case ON subject_evaluation_prediction_assessments(gate_id, evaluation_case_id);

CREATE TABLE subject_evaluation_signoffs (
    signoff_id TEXT PRIMARY KEY,
    gate_id TEXT NOT NULL REFERENCES subject_evaluation_gates(gate_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    authority_role TEXT NOT NULL CHECK (authority_role IN ('subject','controller','fresh_reviewer')),
    principal_id TEXT NOT NULL REFERENCES subject_principals(principal_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (decision IN ('approve','reject','block')),
    scorecard_sha256 TEXT NOT NULL CHECK (length(scorecard_sha256) = 64 AND scorecard_sha256 = lower(scorecard_sha256) AND scorecard_sha256 NOT GLOB '*[^0-9a-f]*'),
    signed_at TEXT NOT NULL,
    UNIQUE(gate_id, authority_role, principal_id),
    UNIQUE(gate_id, principal_id)
);

-- Canonical scorecard bytes use UTF-8, record separator U+001E and field separator U+001F.
-- The host must register deterministic subject_sha256(text) -> lowercase 64-hex before writes.
CREATE VIEW subject_evaluation_scorecard_v1 AS
SELECT
    g.gate_id,
    subject_sha256(
        'subject-evaluation-scorecard-v1' || char(30) ||
        g.gate_id || char(31) || g.subject_id || char(31) || CAST(g.gate_version AS TEXT) || char(31) ||
        g.manifest_sha256 || char(31) ||
        g.eligibility_rules_version || char(31) || g.eligibility_rules_sha256 || char(31) ||
        g.exclusion_rules_version || char(31) || g.exclusion_rules_sha256 || char(31) ||
        g.denominator_rule || char(31) || CAST(g.minimum_n AS TEXT) || char(31) || g.rounding_rule || char(31) ||
        printf('%!.17g',g.utility_threshold) || char(31) || printf('%!.17g',g.reason_alignment_threshold) || char(31) ||
        printf('%!.17g',g.abstention_minimum) || char(31) || printf('%!.17g',g.domain_utility_threshold) || char(31) ||
        printf('%!.17g',g.high_confidence_threshold) || char(31) ||
        g.hard_failure_rules_version || char(31) || g.hard_failure_rules_sha256 || char(31) ||
        g.scoring_definitions_version || char(31) || g.scoring_definitions_sha256 || char(31) ||
        g.reviewer_authority_code || char(31) || g.created_at || char(31) || g.frozen_at || char(30) ||
        COALESCE((SELECT group_concat(row_value, char(30)) FROM (
            SELECT 'C' || char(31) || c.evaluation_case_id || char(31) || c.case_integrity_mac || char(31) ||
                   c.primary_domain || char(31) || CAST(c.is_abstention AS TEXT) || char(31) ||
                   CAST(c.has_subject_correction AS TEXT) || char(31) || CAST(c.has_counter_evidence AS TEXT) || char(31) ||
                   CAST(c.has_contextual_constraint AS TEXT) || char(31) || CAST(c.eligible AS TEXT) || char(31) ||
                   COALESCE(c.preregistered_exclusion_code,'~') || char(31) || c.completion_state || char(31) ||
                   COALESCE(c.disposition_at,'~') || char(31) || c.created_at AS row_value
            FROM subject_evaluation_cases c WHERE c.gate_id = g.gate_id ORDER BY c.evaluation_case_id
        )), '') || char(30) ||
        COALESCE((SELECT group_concat(row_value, char(30)) FROM (
            SELECT 'E' || char(31) || e.evaluation_event_id || char(31) || e.evaluation_case_id || char(31) ||
                   e.event_type || char(31) || COALESCE(printf('%!.17g',e.metric_value),'~') || char(31) ||
                   COALESCE(CAST(e.passed AS TEXT),'~') || char(31) || COALESCE(e.reason_code,'~') || char(31) ||
                   e.actor_principal_id || char(31) || e.source_ref || char(31) || e.occurred_at || char(31) || e.audit_id AS row_value
            FROM subject_evaluation_events e WHERE e.gate_id = g.gate_id ORDER BY e.evaluation_case_id, e.event_type, e.evaluation_event_id
        )), '') || char(30) ||
        COALESCE((SELECT group_concat(row_value, char(30)) FROM (
            SELECT 'P' || char(31) || p.prediction_assessment_id || char(31) || p.evaluation_case_id || char(31) ||
                   p.assessment_status || char(31) || COALESCE(p.predicted_choice_sha256,'~') || char(31) ||
                   COALESCE(printf('%!.17g',p.prediction_confidence),'~') || char(31) ||
                   COALESCE(p.actual_choice_sha256,'~') || char(31) || COALESCE(CAST(p.prediction_correct AS TEXT),'~') || char(31) ||
                   p.subject_principal_id || char(31) || p.source_ref || char(31) || p.assessed_at || char(31) ||
                   p.reviewed_at || char(31) || p.audit_id AS row_value
            FROM subject_evaluation_prediction_assessments p WHERE p.gate_id = g.gate_id
            ORDER BY p.evaluation_case_id, p.prediction_assessment_id
        )), '')
    ) AS scorecard_sha256
FROM subject_evaluation_gates g;

-- Immutable audit/domain metadata.
CREATE TRIGGER trg_subject_installation_insert_uninitialized
BEFORE INSERT ON subject_installation
WHEN NEW.capability_state <> 'available_uninitialized' OR NEW.root_subject_id IS NOT NULL OR NEW.initialized_at IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_installation_must_start_uninitialized'); END;
CREATE TRIGGER trg_subject_policy_insert_draft
BEFORE INSERT ON subject_policies
WHEN NEW.status <> 'draft' OR NEW.approved_event_id IS NOT NULL OR NEW.effective_until IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_policy_must_start_draft'); END;
CREATE TRIGGER trg_subject_model_insert_draft
BEFORE INSERT ON subject_models
WHEN NEW.status <> 'draft'
BEGIN SELECT RAISE(ABORT,'subject_model_must_start_draft'); END;
CREATE TRIGGER trg_decision_episode_insert_open
BEFORE INSERT ON decision_episodes
WHEN NEW.lifecycle <> 'open' OR NEW.review_state <> 'unreviewed' OR NEW.projected_through_sequence <> 0
 OR NOT EXISTS (
    SELECT 1 FROM subject_events e
    JOIN subject_role_grants g
      ON g.subject_id = NEW.subject_id
     AND g.principal_id = e.actor_principal_id
     AND g.role IN ('subject','controller')
     AND g.role = e.actor_role
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE e.event_id = NEW.created_event_id
      AND e.event_kind = 'decision.episode_created'
      AND e.subject_id = NEW.subject_id
      AND e.actor_role IN ('subject','controller')
      AND e.occurred_at <= NEW.created_at
 )
BEGIN SELECT RAISE(ABORT,'decision_episode_must_start_open_with_authorized_subject_event'); END;
CREATE TRIGGER trg_subject_auth_binding_insert_active
BEFORE INSERT ON subject_auth_bindings
WHEN NEW.status <> 'active' OR NEW.revoked_at IS NOT NULL OR NEW.revocation_event_id IS NOT NULL
 OR NOT EXISTS (
    SELECT 1 FROM subject_events e
    WHERE e.event_id = NEW.issued_event_id
      AND e.event_kind = 'auth.binding.issued'
      AND e.actor_principal_id = NEW.issued_by_principal_id
      AND e.actor_role = 'subject'
      AND e.subject_id IS NOT NULL
      AND e.occurred_at <= NEW.created_at
      AND EXISTS (
          SELECT 1 FROM subject_role_grants target
          WHERE target.subject_id = e.subject_id
            AND target.principal_id = NEW.principal_id
            AND (target.revoked_at IS NULL OR target.revoked_at > e.occurred_at)
            AND target.effective_from <= e.occurred_at
            AND (target.expires_at IS NULL OR target.expires_at > e.occurred_at)
      )
      AND EXISTS (
          SELECT 1 FROM subject_role_grants issuer
          WHERE issuer.subject_id = e.subject_id
            AND issuer.principal_id = NEW.issued_by_principal_id
            AND issuer.role = 'subject'
            AND issuer.role = e.actor_role
            AND (issuer.revoked_at IS NULL OR issuer.revoked_at > e.occurred_at)
            AND issuer.effective_from <= e.occurred_at
            AND (issuer.expires_at IS NULL OR issuer.expires_at > e.occurred_at)
      )
 )
BEGIN SELECT RAISE(ABORT,'subject_auth_binding_must_start_active_with_authorized_issue_event'); END;
CREATE TRIGGER trg_subject_role_grant_insert_binding
BEFORE INSERT ON subject_role_grants
WHEN NEW.revoked_at IS NOT NULL OR NEW.revocation_event_id IS NOT NULL
 OR NOT EXISTS (
    SELECT 1 FROM subject_events e
    WHERE e.event_id = NEW.authority_event_id
      AND e.event_kind = 'auth.role_grant.issued'
      AND e.subject_id = NEW.subject_id
      AND e.actor_principal_id = NEW.issued_by_principal_id
      AND e.actor_role IN ('subject','controller')
      AND e.occurred_at >= NEW.effective_from
      AND e.occurred_at <= NEW.created_at
      AND (
          EXISTS (
              SELECT 1 FROM subject_role_grants issuer
              WHERE issuer.subject_id = NEW.subject_id
                AND issuer.principal_id = NEW.issued_by_principal_id
                AND issuer.role IN ('subject','controller')
                AND issuer.role = e.actor_role
                AND (issuer.revoked_at IS NULL OR issuer.revoked_at > e.occurred_at)
                AND issuer.effective_from <= e.occurred_at
                AND (issuer.expires_at IS NULL OR issuer.expires_at > e.occurred_at)
          )
          OR (
              NEW.role = 'subject'
                   AND NEW.principal_id = NEW.issued_by_principal_id
                   AND e.actor_role = 'subject'
                   AND NOT EXISTS (
                       SELECT 1 FROM subject_role_grants existing
                       WHERE existing.subject_id = NEW.subject_id
                   )
              )
      )
 )
BEGIN SELECT RAISE(ABORT,'subject_role_grant_authority_event_mismatch'); END;
CREATE TRIGGER trg_subject_access_grant_insert_authority
BEFORE INSERT ON subject_access_grants
WHEN NEW.revoked_at IS NOT NULL OR NEW.revocation_event_id IS NOT NULL
 OR NOT EXISTS (
    SELECT 1 FROM subject_events e
    WHERE e.event_id = NEW.authority_event_id
      AND e.event_kind = 'auth.access_grant.issued'
      AND e.subject_id = NEW.subject_id
      AND e.actor_principal_id = NEW.issued_by_principal_id
      AND e.actor_role IN ('subject','controller')
      AND e.occurred_at >= NEW.effective_from
      AND e.occurred_at <= NEW.created_at
      AND EXISTS (
          SELECT 1 FROM subject_role_grants issuer
          WHERE issuer.subject_id = NEW.subject_id
            AND issuer.principal_id = NEW.issued_by_principal_id
            AND issuer.role IN ('subject','controller')
            AND issuer.role = e.actor_role
            AND (issuer.revoked_at IS NULL OR issuer.revoked_at > e.occurred_at)
            AND issuer.effective_from <= e.occurred_at
            AND (issuer.expires_at IS NULL OR issuer.expires_at > e.occurred_at)
      )
 )
 OR NOT EXISTS (
    SELECT 1 FROM subject_policies p
    WHERE p.policy_id = NEW.policy_id
      AND p.subject_id = NEW.subject_id
      AND p.policy_kind = 'access'
      AND p.status = 'sealed'
      AND p.effective_from <= (SELECT occurred_at FROM subject_events WHERE event_id = NEW.authority_event_id)
      AND (p.effective_until IS NULL OR p.effective_until > (SELECT occurred_at FROM subject_events WHERE event_id = NEW.authority_event_id))
      AND p.effective_from <= NEW.effective_from
      AND (p.effective_until IS NULL OR p.effective_until > NEW.effective_from)
 )
BEGIN SELECT RAISE(ABORT,'subject_access_grant_authority_event_mismatch'); END;
CREATE TRIGGER trg_subject_payload_insert_active
BEFORE INSERT ON subject_payload_objects
WHEN NEW.lifecycle <> 'active' OR NEW.purged_at IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_payload_must_start_active'); END;
CREATE TRIGGER trg_subject_purge_job_insert_pending
BEFORE INSERT ON subject_purge_jobs
WHEN NEW.state <> 'pending' OR NEW.attempts <> 0 OR NEW.completed_at IS NOT NULL OR NEW.last_error_code IS NOT NULL
 OR NEW.object_deleted_at IS NOT NULL OR NEW.parent_fsynced_at IS NOT NULL OR NEW.metadata_cleared_at IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_purge_job_must_start_pending'); END;
CREATE TRIGGER trg_subject_purge_job_insert_authority_scope
BEFORE INSERT ON subject_purge_jobs
WHEN NOT EXISTS (
    SELECT 1 FROM subject_payload_objects p
    JOIN subject_events e
      ON e.event_id = NEW.requested_event_id
     AND e.subject_id = p.subject_id
     AND e.event_kind = 'payload.purge_requested'
     AND e.actor_principal_id = NEW.requested_by_principal_id
     AND e.actor_role IN ('subject','controller')
     AND e.occurred_at <= NEW.created_at
    JOIN subject_role_grants g
      ON g.subject_id = p.subject_id
     AND g.principal_id = NEW.requested_by_principal_id
     AND g.role IN ('subject','controller')
     AND g.role = e.actor_role
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE p.payload_id = NEW.payload_id
)
BEGIN SELECT RAISE(ABORT,'subject_purge_job_authority_scope_mismatch'); END;
CREATE TRIGGER trg_subject_assertion_insert_active
BEFORE INSERT ON subject_assertions
WHEN NEW.lifecycle <> 'active' OR NEW.termination_event_id IS NOT NULL OR NEW.effective_until IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_assertion_must_start_active'); END;
CREATE TRIGGER trg_subject_assertion_relationship_scope
BEFORE INSERT ON subject_assertions
WHEN (
    NEW.namespace = 'perspective'
    AND NOT EXISTS (
        SELECT 1 FROM subject_relationships r
        WHERE r.relationship_id = NEW.relationship_id
          AND r.from_subject_id = NEW.model_owner_subject_id
          AND r.to_subject_id = NEW.about_subject_id
          AND r.lifecycle = 'active'
          AND r.effective_from <= NEW.effective_from
          AND (r.effective_until IS NULL OR r.effective_until > NEW.recorded_at)
    )
) OR (
    NEW.namespace = 'relationship_experience'
    AND NOT EXISTS (
        SELECT 1 FROM subject_relationships r
        WHERE r.relationship_id = NEW.relationship_id
          AND NEW.model_owner_subject_id IN (r.from_subject_id, r.to_subject_id)
          AND r.lifecycle = 'active'
          AND r.effective_from <= NEW.effective_from
          AND (r.effective_until IS NULL OR r.effective_until > NEW.recorded_at)
    )
)
BEGIN SELECT RAISE(ABORT,'subject_assertion_relationship_scope_mismatch'); END;
CREATE TRIGGER trg_subject_assertion_authority_scope
BEFORE INSERT ON subject_assertions
WHEN NOT EXISTS (
    SELECT 1 FROM subject_events e
    JOIN subject_role_grants g
      ON g.subject_id = NEW.model_owner_subject_id
     AND g.principal_id = NEW.actor_principal_id
     AND g.role = CASE NEW.actor_role
         WHEN 'system' THEN 'authority_source'
         ELSE NEW.actor_role
     END
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE e.event_id = NEW.authority_event_id
      AND e.event_kind = 'assertion.recorded'
      AND e.subject_id = NEW.model_owner_subject_id
      AND e.actor_principal_id = NEW.actor_principal_id
      AND e.occurred_at >= NEW.effective_from
      AND e.occurred_at <= NEW.recorded_at
      AND e.actor_role = CASE NEW.actor_role
          WHEN 'system' THEN 'authority_source'
          ELSE NEW.actor_role
      END
 )
 OR (NEW.assertion_class = 'explicit' AND NOT EXISTS (
    SELECT 1 FROM subject_events e
    JOIN subject_role_grants g
      ON g.subject_id = NEW.about_subject_id
     AND g.principal_id = e.actor_principal_id
     AND g.role = 'subject'
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE e.event_id = NEW.confirmation_event_id
      AND e.event_kind = 'assertion.confirmed'
      AND e.subject_id = NEW.about_subject_id
      AND e.actor_role = 'subject'
      AND e.occurred_at >= NEW.effective_from
      AND e.occurred_at <= NEW.recorded_at
      AND EXISTS (
          SELECT 1
          FROM subject_auth_bindings b
          JOIN subject_events issued
            ON issued.event_id = b.issued_event_id
           AND issued.event_kind = 'auth.binding.issued'
           AND issued.subject_id = NEW.about_subject_id
          WHERE b.principal_id = e.actor_principal_id
            AND b.created_at <= e.occurred_at
            AND (b.expires_at IS NULL OR b.expires_at > e.occurred_at)
            AND (b.revoked_at IS NULL OR b.revoked_at > e.occurred_at)
      )
 ))
 OR (NEW.value_payload_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM subject_payload_objects p
    WHERE p.payload_id = NEW.value_payload_id
      AND p.subject_id = NEW.model_owner_subject_id
      AND p.payload_kind = 'assertion_value'
      AND p.lifecycle = 'active'
 ))
BEGIN SELECT RAISE(ABORT,'subject_assertion_authority_scope_mismatch'); END;
CREATE TRIGGER trg_subject_pack_run_insert_draft
BEFORE INSERT ON subject_context_pack_runs
WHEN NEW.state <> 'draft' OR NEW.sealed_at IS NOT NULL OR NEW.content_integrity_mac IS NOT NULL OR NEW.action_authority <> 0 OR NEW.delegation_rule_id IS NOT NULL
 OR NEW.action_domain_code IS NOT NULL OR NEW.action_stakes IS NOT NULL OR NEW.action_reversibility IS NOT NULL
 OR NEW.action_cost_minor IS NOT NULL OR NEW.action_currency_code IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_pack_run_must_start_draft'); END;
CREATE TRIGGER trg_subject_evaluation_gate_insert_draft
BEFORE INSERT ON subject_evaluation_gates
WHEN NEW.state <> 'draft' OR NEW.frozen_at IS NOT NULL OR NEW.closed_at IS NOT NULL OR NEW.scorecard_sha256 IS NOT NULL OR NEW.verdict IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_evaluation_gate_must_start_draft'); END;
CREATE TRIGGER trg_subject_principal_insert_active
BEFORE INSERT ON subject_principals
WHEN NEW.status <> 'active' OR NEW.status_event_id IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_principal_must_start_active'); END;
CREATE TRIGGER trg_subject_principal_transition
BEFORE UPDATE ON subject_principals
WHEN NOT (
    NEW.principal_id = OLD.principal_id
    AND NEW.principal_type = OLD.principal_type
    AND NEW.created_at = OLD.created_at
    AND NEW.status_event_id IS NOT NULL
    AND NEW.status_event_id IS NOT OLD.status_event_id
    AND NEW.updated_at >= OLD.created_at
    AND NEW.updated_at > OLD.updated_at
    AND ((OLD.status = 'active' AND NEW.status IN ('suspended','revoked')) OR (OLD.status = 'suspended' AND NEW.status = 'revoked'))
)
BEGIN SELECT RAISE(ABORT,'subject_principal_transition_forbidden'); END;
CREATE TRIGGER trg_subject_principal_status_event_binding
BEFORE UPDATE ON subject_principals
WHEN NEW.status <> OLD.status
 AND NOT EXISTS (
    SELECT 1
    FROM subject_events e
    WHERE e.event_id = NEW.status_event_id
      AND e.event_kind = CASE NEW.status
          WHEN 'suspended' THEN 'principal.suspended'
          WHEN 'revoked' THEN 'principal.revoked'
      END
      AND e.subject_id IS NULL
      AND e.actor_principal_id = OLD.principal_id
      AND e.actor_role = 'subject'
      AND e.occurred_at = NEW.updated_at
      AND e.recorded_at >= e.occurred_at
      AND e.occurred_at >= OLD.created_at
      AND EXISTS (
          SELECT 1
          FROM subject_auth_bindings b
          WHERE b.principal_id = OLD.principal_id
            AND b.created_at <= e.occurred_at
            AND (b.expires_at IS NULL OR b.expires_at > e.occurred_at)
            AND (b.revoked_at IS NULL OR b.revoked_at > e.occurred_at)
      )
 )
BEGIN SELECT RAISE(ABORT,'subject_principal_status_event_mismatch'); END;
CREATE TRIGGER trg_subject_principal_no_delete BEFORE DELETE ON subject_principals BEGIN SELECT RAISE(ABORT,'subject_principal_history_retained'); END;
CREATE TRIGGER trg_subject_row_insert_active
BEFORE INSERT ON subjects
WHEN NEW.lifecycle <> 'active' OR NEW.lifecycle_event_id IS NOT NULL OR NEW.effective_until IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_must_start_active'); END;
CREATE TRIGGER trg_subject_row_transition
BEFORE UPDATE ON subjects
WHEN NOT (
    NEW.subject_id = OLD.subject_id
    AND NEW.subject_type = OLD.subject_type
    AND NEW.identity_mode = OLD.identity_mode
    AND NEW.is_root = OLD.is_root
    AND NEW.effective_from = OLD.effective_from
    AND NEW.created_at = OLD.created_at
    AND NEW.lifecycle_event_id IS NOT NULL
    AND NEW.lifecycle_event_id IS NOT OLD.lifecycle_event_id
    AND NEW.effective_until IS NOT NULL
    AND ((OLD.lifecycle = 'active' AND NEW.lifecycle IN ('inactive','revoked','deleted')) OR (OLD.lifecycle = 'inactive' AND NEW.lifecycle IN ('revoked','deleted')))
)
BEGIN SELECT RAISE(ABORT,'subject_lifecycle_transition_forbidden'); END;
CREATE TRIGGER trg_subject_lifecycle_event_binding
BEFORE UPDATE ON subjects
WHEN NEW.lifecycle <> OLD.lifecycle
 AND NOT EXISTS (
    SELECT 1
    FROM subject_events e
    JOIN subject_role_grants g
      ON g.subject_id = OLD.subject_id
     AND g.principal_id = e.actor_principal_id
     AND g.role = 'subject'
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
    WHERE e.event_id = NEW.lifecycle_event_id
      AND e.event_kind = CASE NEW.lifecycle
          WHEN 'inactive' THEN 'subject.inactivated'
          WHEN 'revoked' THEN 'subject.revoked'
          WHEN 'deleted' THEN 'subject.deleted'
      END
      AND e.subject_id = OLD.subject_id
      AND e.actor_role = 'subject'
      AND e.occurred_at = NEW.effective_until
      AND e.recorded_at >= e.occurred_at
      AND e.occurred_at >= OLD.effective_from
      AND e.occurred_at >= OLD.created_at
 )
BEGIN SELECT RAISE(ABORT,'subject_lifecycle_event_mismatch'); END;
CREATE TRIGGER trg_subject_row_no_delete BEFORE DELETE ON subjects BEGIN SELECT RAISE(ABORT,'subject_history_retained'); END;
CREATE TRIGGER trg_subject_evidence_insert_payload_scope
BEFORE INSERT ON subject_evidence
WHEN NEW.retention_mode = 'private_copy' AND NOT EXISTS (
    SELECT 1 FROM subject_payload_objects p
    WHERE p.payload_id = NEW.private_payload_id
      AND p.subject_id = NEW.about_subject_id
      AND p.payload_kind = 'private_evidence'
      AND p.lifecycle = 'active'
)
BEGIN SELECT RAISE(ABORT,'subject_evidence_private_payload_scope_invalid'); END;
CREATE TRIGGER trg_subject_candidate_payload_insert_scope
BEFORE INSERT ON subject_candidate_payloads
WHEN NOT EXISTS (
    SELECT 1 FROM subject_payload_objects p
    WHERE p.payload_id = NEW.payload_id
      AND p.subject_id = NEW.subject_id
      AND p.payload_kind = 'candidate_value'
      AND p.lifecycle = 'active'
)
BEGIN SELECT RAISE(ABORT,'subject_candidate_payload_scope_invalid'); END;
CREATE TRIGGER trg_subject_evidence_no_update BEFORE UPDATE ON subject_evidence BEGIN SELECT RAISE(ABORT,'subject_evidence_append_only_use_successor'); END;
CREATE TRIGGER trg_subject_evidence_no_delete BEFORE DELETE ON subject_evidence BEGIN SELECT RAISE(ABORT,'subject_evidence_history_retained'); END;
CREATE TRIGGER trg_subject_relationship_insert_active
BEFORE INSERT ON subject_relationships
WHEN NEW.lifecycle <> 'active' OR NEW.termination_event_id IS NOT NULL OR NEW.effective_until IS NOT NULL
 OR NOT EXISTS (
    SELECT 1 FROM subject_events e
    JOIN subject_role_grants g
      ON g.subject_id = NEW.from_subject_id
     AND g.principal_id = e.actor_principal_id
     AND g.role IN ('subject','controller')
     AND g.role = e.actor_role
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE e.event_id = NEW.provenance_event_id
      AND e.event_kind = 'relationship.recorded'
      AND e.subject_id = NEW.from_subject_id
      AND e.actor_role IN ('subject','controller')
      AND e.occurred_at >= NEW.effective_from
      AND e.occurred_at <= NEW.created_at
 )
BEGIN SELECT RAISE(ABORT,'subject_relationship_must_start_active_with_authorized_provenance'); END;
CREATE TRIGGER trg_subject_relationship_transition
BEFORE UPDATE ON subject_relationships
WHEN NOT (
    NEW.relationship_id = OLD.relationship_id
    AND NEW.from_subject_id = OLD.from_subject_id
    AND NEW.to_subject_id = OLD.to_subject_id
    AND NEW.formal_type = OLD.formal_type
    AND NEW.source_role = OLD.source_role
    AND NEW.counterparty_role = OLD.counterparty_role
    AND NEW.lived_state = OLD.lived_state
    AND NEW.sensitivity = OLD.sensitivity
    AND NEW.provenance_event_id = OLD.provenance_event_id
    AND NEW.effective_from = OLD.effective_from
    AND NEW.created_at = OLD.created_at
    AND OLD.lifecycle = 'active'
    AND NEW.lifecycle IN ('ended','revoked','deleted')
    AND OLD.termination_event_id IS NULL
    AND NEW.termination_event_id IS NOT NULL
    AND NEW.effective_until IS NOT NULL
    AND NEW.effective_until >= OLD.created_at
    AND NOT EXISTS (
        SELECT 1 FROM subject_aliases a
        WHERE a.relationship_id = OLD.relationship_id
          AND a.effective_from < NEW.effective_until
          AND (a.effective_until IS NULL OR a.effective_until > NEW.effective_until)
          AND (a.revoked_at IS NULL OR a.revoked_at >= NEW.effective_until)
    )
    AND NOT EXISTS (
        SELECT 1 FROM subject_assertions a
        WHERE a.relationship_id = OLD.relationship_id
          AND a.namespace IN ('relationship_experience','perspective')
          AND a.effective_from < NEW.effective_until
          AND (a.effective_until IS NULL OR a.effective_until > NEW.effective_until)
    )
    AND NOT EXISTS (
        SELECT 1 FROM subject_counterparty_controls cc
        WHERE cc.relationship_id = OLD.relationship_id
          AND cc.created_at < NEW.effective_until
          AND cc.retention_until > NEW.effective_until
          AND (cc.revoked_at IS NULL OR cc.revoked_at >= NEW.effective_until)
          AND NOT (
              cc.deletion_state = 'purge_pending'
              AND EXISTS (
                  SELECT 1
                  FROM subject_events requested
                  WHERE requested.event_id = cc.deletion_requested_event_id
                    AND requested.event_kind = 'counterparty.deletion_requested'
                    AND requested.occurred_at >= OLD.effective_from
                    AND requested.occurred_at < NEW.effective_until
              )
          )
          AND (
              cc.deletion_state NOT IN ('purged','deidentified')
              OR (SELECT occurred_at FROM subject_events WHERE event_id = cc.deletion_completed_event_id) >= NEW.effective_until
          )
    )
)
BEGIN SELECT RAISE(ABORT,'subject_relationship_transition_forbidden'); END;
CREATE TRIGGER trg_subject_relationship_event_binding
BEFORE UPDATE ON subject_relationships
WHEN NEW.lifecycle <> OLD.lifecycle
 AND NOT EXISTS (
    SELECT 1 FROM subject_events e
    JOIN subject_role_grants g
      ON g.subject_id = OLD.from_subject_id
     AND g.principal_id = e.actor_principal_id
     AND g.role IN ('subject','controller')
     AND g.role = e.actor_role
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE e.event_id = NEW.termination_event_id
      AND e.event_kind = CASE NEW.lifecycle
          WHEN 'ended' THEN 'relationship.ended'
          WHEN 'revoked' THEN 'relationship.revoked'
          WHEN 'deleted' THEN 'relationship.deleted'
      END
      AND e.subject_id = OLD.from_subject_id
      AND e.actor_role IN ('subject','controller')
      AND e.occurred_at = NEW.effective_until
      AND e.occurred_at >= OLD.created_at
 )
BEGIN SELECT RAISE(ABORT,'subject_relationship_termination_event_mismatch'); END;
CREATE TRIGGER trg_subject_relationship_no_delete BEFORE DELETE ON subject_relationships BEGIN SELECT RAISE(ABORT,'subject_relationship_history_retained'); END;
CREATE TRIGGER trg_subject_alias_insert_scope
BEFORE INSERT ON subject_aliases
WHEN NEW.revoked_at IS NOT NULL OR NEW.revocation_event_id IS NOT NULL
 OR NOT EXISTS (
    SELECT 1 FROM subject_payload_objects p
    JOIN subject_events e
      ON e.event_id = NEW.authority_event_id
     AND e.event_kind = 'relationship.alias_recorded'
     AND e.subject_id = NEW.controller_subject_id
     AND e.actor_role IN ('subject','controller')
     AND e.occurred_at >= NEW.effective_from
     AND e.occurred_at <= NEW.created_at
    JOIN subject_role_grants g
      ON g.subject_id = NEW.controller_subject_id
     AND g.principal_id = e.actor_principal_id
     AND g.role IN ('subject','controller')
     AND g.role = e.actor_role
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE p.payload_id = NEW.alias_payload_id
      AND p.subject_id = NEW.controller_subject_id
      AND p.payload_kind = 'alias_value'
      AND p.lifecycle = 'active'
 )
 OR NOT EXISTS (
    SELECT 1 FROM subject_relationships r
    WHERE r.relationship_id = NEW.relationship_id
      AND r.from_subject_id = NEW.controller_subject_id
      AND r.to_subject_id = NEW.referenced_subject_id
      AND r.lifecycle = 'active'
      AND r.effective_from <= NEW.effective_from
      AND (r.effective_until IS NULL OR r.effective_until > NEW.created_at)
 )
BEGIN SELECT RAISE(ABORT,'subject_alias_authority_or_topology_mismatch'); END;
CREATE TRIGGER trg_subject_alias_restrict_update
BEFORE UPDATE ON subject_aliases
WHEN NOT (
    OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL
    AND NEW.alias_id = OLD.alias_id
    AND NEW.controller_subject_id = OLD.controller_subject_id
    AND NEW.referenced_subject_id = OLD.referenced_subject_id
    AND NEW.relationship_id IS OLD.relationship_id
    AND NEW.alias_payload_id = OLD.alias_payload_id
    AND NEW.purpose_code = OLD.purpose_code
    AND NEW.sensitivity = OLD.sensitivity
    AND NEW.authority_event_id = OLD.authority_event_id
    AND NEW.effective_from = OLD.effective_from
    AND NEW.effective_until IS OLD.effective_until
    AND NEW.created_at = OLD.created_at
    AND OLD.revocation_event_id IS NULL AND NEW.revocation_event_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = OLD.controller_subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role IN ('subject','controller')
         AND g.role = e.actor_role
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.revocation_event_id
          AND e.event_kind = 'relationship.alias_revoked'
          AND e.subject_id = OLD.controller_subject_id
          AND e.actor_role IN ('subject','controller')
          AND e.occurred_at = NEW.revoked_at
          AND EXISTS (
              SELECT 1 FROM subject_relationships r
              WHERE r.relationship_id = OLD.relationship_id
                AND r.effective_from <= e.occurred_at
                AND (r.effective_until IS NULL OR r.effective_until > e.occurred_at)
          )
    )
)
BEGIN SELECT RAISE(ABORT,'subject_alias_update_forbidden'); END;
CREATE TRIGGER trg_subject_alias_no_delete BEFORE DELETE ON subject_aliases BEGIN SELECT RAISE(ABORT,'subject_alias_history_retained'); END;
CREATE TRIGGER trg_subject_counterparty_insert_active
BEFORE INSERT ON subject_counterparty_controls
WHEN NEW.deletion_state <> 'active' OR NEW.deletion_requested_event_id IS NOT NULL OR NEW.deletion_completed_event_id IS NOT NULL OR NEW.revoked_at IS NOT NULL OR NEW.revocation_event_id IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_counterparty_control_must_start_active'); END;
CREATE TRIGGER trg_subject_counterparty_event_binding_insert
BEFORE INSERT ON subject_counterparty_controls
WHEN NOT EXISTS (
        SELECT 1 FROM subject_relationships r
        WHERE r.relationship_id = NEW.relationship_id
          AND r.from_subject_id = NEW.primary_subject_id
          AND r.to_subject_id = NEW.counterparty_subject_id
          AND r.lifecycle = 'active'
          AND r.effective_from <= NEW.created_at
          AND (r.effective_until IS NULL OR r.effective_until > NEW.created_at)
    )
  OR (NEW.processing_basis = 'subject_perspective_only' AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = NEW.primary_subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role IN ('subject','controller')
         AND g.role = e.actor_role
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.authority_event_id
          AND e.event_kind = 'counterparty.perspective_authorized'
          AND e.subject_id = NEW.primary_subject_id
          AND e.actor_role IN ('subject','controller')
          AND e.occurred_at >= (SELECT effective_from FROM subject_relationships WHERE relationship_id = NEW.relationship_id)
          AND e.occurred_at <= NEW.created_at
    ))
  OR (NEW.processing_basis = 'counterparty_consent' AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.principal_id = e.actor_principal_id
         AND g.subject_id = NEW.counterparty_subject_id
         AND g.role = 'subject'
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        JOIN subject_policies p
          ON p.policy_id = NEW.legal_policy_id
         AND p.subject_id = NEW.primary_subject_id
         AND p.policy_kind = 'counterparty'
         AND p.status = 'sealed'
         AND p.version = NEW.legal_policy_version
         AND p.effective_from <= e.occurred_at
         AND (p.effective_until IS NULL OR p.effective_until > e.occurred_at)
        WHERE e.event_id = NEW.authority_event_id
          AND e.event_kind = 'counterparty.consent_granted'
          AND e.subject_id = NEW.counterparty_subject_id
          AND e.actor_role = 'subject'
          AND e.occurred_at >= (SELECT effective_from FROM subject_relationships WHERE relationship_id = NEW.relationship_id)
          AND e.occurred_at <= NEW.created_at
    ))
  OR (NEW.processing_basis = 'legal_obligation' AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = NEW.primary_subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role = 'authority_source'
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        JOIN subject_policies p ON p.policy_id = NEW.legal_policy_id
        WHERE e.event_id = NEW.authority_event_id
          AND e.event_kind = 'counterparty.legal_obligation_recorded'
          AND e.subject_id = NEW.primary_subject_id
          AND e.actor_role = 'authority_source'
          AND e.occurred_at >= (SELECT effective_from FROM subject_relationships WHERE relationship_id = NEW.relationship_id)
          AND e.occurred_at <= NEW.created_at
          AND p.subject_id = NEW.primary_subject_id
          AND p.policy_kind = 'counterparty'
          AND p.status = 'sealed'
          AND p.version = NEW.legal_policy_version
          AND p.effective_from <= e.occurred_at
          AND (p.effective_until IS NULL OR p.effective_until > e.occurred_at)
    ))
  OR (NEW.legal_hold_authority_event_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = NEW.primary_subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role = 'authority_source'
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        JOIN subject_policies p ON p.policy_id = NEW.legal_hold_policy_id
        WHERE e.event_id = NEW.legal_hold_authority_event_id
          AND e.event_kind = 'counterparty.legal_hold_created'
          AND e.subject_id = NEW.primary_subject_id
          AND e.actor_role = 'authority_source'
          AND e.occurred_at >= (SELECT effective_from FROM subject_relationships WHERE relationship_id = NEW.relationship_id)
          AND e.occurred_at <= NEW.created_at
          AND p.subject_id = NEW.primary_subject_id
          AND p.policy_kind = 'counterparty'
          AND p.status = 'sealed'
          AND p.version = NEW.legal_hold_policy_version
          AND p.effective_from <= e.occurred_at
          AND (p.effective_until IS NULL OR p.effective_until > e.occurred_at)
    ))
BEGIN SELECT RAISE(ABORT,'subject_counterparty_authority_event_mismatch'); END;
CREATE TRIGGER trg_subject_counterparty_event_binding_update
BEFORE UPDATE ON subject_counterparty_controls
WHEN (NEW.revocation_event_id IS NOT OLD.revocation_event_id AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = e.subject_id
         AND g.principal_id = e.actor_principal_id
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.revocation_event_id
          AND e.event_kind = 'counterparty.control_revoked'
          AND g.role = e.actor_role
          AND e.occurred_at = NEW.revoked_at
          AND e.occurred_at >= NEW.created_at
          AND EXISTS (
              SELECT 1 FROM subject_relationships r
              WHERE r.relationship_id = OLD.relationship_id
                AND r.effective_from <= e.occurred_at
                AND (r.effective_until IS NULL OR r.effective_until > e.occurred_at)
          )
          AND ((e.subject_id = NEW.primary_subject_id AND g.role IN ('subject','controller') AND e.actor_role IN ('subject','controller'))
               OR (e.subject_id = NEW.counterparty_subject_id AND g.role = 'subject' AND e.actor_role = 'subject'))
    ))
  OR (NEW.deletion_requested_event_id IS NOT OLD.deletion_requested_event_id AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = e.subject_id
         AND g.principal_id = e.actor_principal_id
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.deletion_requested_event_id
          AND e.event_kind = 'counterparty.deletion_requested'
          AND g.role = e.actor_role
          AND e.occurred_at >= NEW.created_at
          AND EXISTS (
              SELECT 1
              FROM subject_relationships r
              WHERE r.relationship_id = OLD.relationship_id
                AND r.effective_from <= e.occurred_at
                AND (r.effective_until IS NULL OR r.effective_until > e.occurred_at)
          )
          AND ((e.subject_id = NEW.primary_subject_id AND g.role IN ('subject','controller') AND e.actor_role IN ('subject','controller'))
               OR (e.subject_id = NEW.counterparty_subject_id AND g.role = 'subject' AND e.actor_role = 'subject'))
    ))
  OR (NEW.deletion_completed_event_id IS NOT OLD.deletion_completed_event_id AND NOT EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = NEW.primary_subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role IN ('controller','authority_source')
         AND g.role = e.actor_role
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.deletion_completed_event_id
          AND e.event_kind = 'counterparty.deletion_completed'
          AND e.subject_id = NEW.primary_subject_id
          AND e.actor_role IN ('controller','authority_source')
          AND e.occurred_at > (SELECT occurred_at FROM subject_events WHERE event_id = NEW.deletion_requested_event_id)
          AND (NEW.legal_hold_until IS NULL OR NEW.legal_hold_until <= e.occurred_at)
          AND EXISTS (
              SELECT 1
              FROM subject_events requested
              JOIN subject_relationships r ON r.relationship_id = OLD.relationship_id
              WHERE requested.event_id = NEW.deletion_requested_event_id
                AND requested.event_kind = 'counterparty.deletion_requested'
                AND requested.occurred_at >= r.effective_from
                AND (r.effective_until IS NULL OR r.effective_until > requested.occurred_at)
          )
    ))
BEGIN SELECT RAISE(ABORT,'subject_counterparty_lifecycle_event_mismatch'); END;
CREATE TRIGGER trg_subject_counterparty_restrict_update
BEFORE UPDATE ON subject_counterparty_controls
WHEN NOT (
    NEW.counterparty_control_id = OLD.counterparty_control_id
    AND NEW.primary_subject_id = OLD.primary_subject_id
    AND NEW.counterparty_subject_id = OLD.counterparty_subject_id
    AND NEW.relationship_id IS OLD.relationship_id
    AND NEW.processing_basis = OLD.processing_basis
    AND NEW.authority_event_id = OLD.authority_event_id
    AND NEW.purpose_code = OLD.purpose_code
    AND NEW.allow_store = OLD.allow_store
    AND NEW.allow_model = OLD.allow_model
    AND NEW.allow_export = OLD.allow_export
    AND NEW.export_mode = OLD.export_mode
    AND NEW.legal_policy_id IS OLD.legal_policy_id
    AND NEW.legal_policy_version IS OLD.legal_policy_version
    AND NEW.retention_until = OLD.retention_until
    AND NEW.legal_hold_until IS OLD.legal_hold_until
    AND NEW.legal_hold_authority_event_id IS OLD.legal_hold_authority_event_id
    AND NEW.legal_hold_policy_id IS OLD.legal_hold_policy_id
    AND NEW.legal_hold_policy_version IS OLD.legal_hold_policy_version
    AND NEW.supersedes_counterparty_control_id IS OLD.supersedes_counterparty_control_id
    AND NEW.created_at = OLD.created_at
    AND (
        (
            OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL
            AND OLD.revocation_event_id IS NULL AND NEW.revocation_event_id IS NOT NULL
            AND NEW.deletion_state = OLD.deletion_state
            AND NEW.deletion_requested_event_id IS OLD.deletion_requested_event_id
            AND NEW.deletion_completed_event_id IS OLD.deletion_completed_event_id
        )
        OR (
            NEW.revoked_at IS OLD.revoked_at AND NEW.revocation_event_id IS OLD.revocation_event_id
            AND (
                (OLD.deletion_state = 'active' AND NEW.deletion_state = 'purge_pending'
                 AND OLD.deletion_requested_event_id IS NULL AND NEW.deletion_requested_event_id IS NOT NULL
                 AND NEW.deletion_completed_event_id IS NULL)
                OR
                (OLD.deletion_state = 'purge_pending' AND NEW.deletion_state IN ('purged','deidentified')
                 AND NEW.deletion_requested_event_id = OLD.deletion_requested_event_id
                 AND OLD.deletion_completed_event_id IS NULL AND NEW.deletion_completed_event_id IS NOT NULL)
            )
        )
    )
)
BEGIN SELECT RAISE(ABORT,'subject_counterparty_control_update_forbidden'); END;
CREATE TRIGGER trg_subject_counterparty_no_delete BEFORE DELETE ON subject_counterparty_controls BEGIN SELECT RAISE(ABORT,'subject_counterparty_history_retained'); END;
CREATE TRIGGER trg_subject_auth_binding_restrict_update
BEFORE UPDATE ON subject_auth_bindings
WHEN NOT (
    OLD.status = 'active'
    AND NEW.status IN ('expired','revoked')
    AND NEW.binding_id = OLD.binding_id
    AND NEW.principal_id = OLD.principal_id
    AND NEW.issued_by_principal_id = OLD.issued_by_principal_id
    AND NEW.adapter = OLD.adapter
    AND NEW.kdf_algorithm = OLD.kdf_algorithm
    AND NEW.credential_salt = OLD.credential_salt
    AND NEW.credential_digest = OLD.credential_digest
    AND NEW.kdf_n = OLD.kdf_n
    AND NEW.kdf_r = OLD.kdf_r
    AND NEW.kdf_p = OLD.kdf_p
    AND NEW.credential_fingerprint = OLD.credential_fingerprint
    AND NEW.issued_event_id = OLD.issued_event_id
    AND NEW.expires_at IS OLD.expires_at
    AND NEW.created_at = OLD.created_at
    AND (
        (NEW.status = 'revoked' AND NEW.revoked_at IS NOT NULL
         AND OLD.revocation_event_id IS NULL AND NEW.revocation_event_id IS NOT NULL
         AND EXISTS (
             SELECT 1 FROM subject_events e
             JOIN subject_role_grants issuer
               ON issuer.subject_id = e.subject_id
              AND issuer.principal_id = OLD.issued_by_principal_id
              AND issuer.role IN ('subject','controller')
              AND issuer.role = e.actor_role
              AND (issuer.revoked_at IS NULL OR issuer.revoked_at > e.occurred_at)
              AND issuer.effective_from <= e.occurred_at
              AND (issuer.expires_at IS NULL OR issuer.expires_at > e.occurred_at)
             WHERE e.event_id = NEW.revocation_event_id
               AND e.event_kind = 'auth.binding.revoked'
               AND e.subject_id = (
                   SELECT issued.subject_id FROM subject_events issued
                   WHERE issued.event_id = OLD.issued_event_id
               )
               AND e.actor_principal_id = OLD.issued_by_principal_id
               AND e.actor_role IN ('subject','controller')
               AND e.occurred_at = NEW.revoked_at
         ))
        OR (NEW.status = 'expired' AND NEW.revoked_at IS NULL AND NEW.revocation_event_id IS NULL
            AND OLD.expires_at IS NOT NULL)
    )
)
BEGIN SELECT RAISE(ABORT,'subject_auth_binding_update_forbidden'); END;
CREATE TRIGGER trg_subject_auth_binding_no_delete BEFORE DELETE ON subject_auth_bindings BEGIN SELECT RAISE(ABORT,'subject_auth_binding_history_retained'); END;
CREATE TRIGGER trg_subject_role_grant_restrict_update
BEFORE UPDATE ON subject_role_grants
WHEN NOT (
    OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL
    AND NEW.role_grant_id = OLD.role_grant_id
    AND NEW.principal_id = OLD.principal_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.role = OLD.role
    AND NEW.domain_code = OLD.domain_code
    AND NEW.authority_scope = OLD.authority_scope
    AND NEW.confirmation_quorum = OLD.confirmation_quorum
    AND NEW.issued_by_principal_id = OLD.issued_by_principal_id
    AND NEW.authority_event_id = OLD.authority_event_id
    AND NEW.effective_from = OLD.effective_from
    AND NEW.expires_at IS OLD.expires_at
    AND NEW.created_at = OLD.created_at
    AND OLD.revocation_event_id IS NULL AND NEW.revocation_event_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants issuer
          ON issuer.subject_id = OLD.subject_id
         AND issuer.principal_id = e.actor_principal_id
         AND issuer.role IN ('subject','controller')
         AND issuer.role = e.actor_role
         AND (issuer.revoked_at IS NULL OR issuer.revoked_at > e.occurred_at)
         AND issuer.role_grant_id <> OLD.role_grant_id
         AND issuer.effective_from <= e.occurred_at
         AND (issuer.expires_at IS NULL OR issuer.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.revocation_event_id
          AND e.event_kind = 'auth.role_grant.revoked'
          AND e.subject_id = OLD.subject_id
          AND e.actor_role IN ('subject','controller')
          AND e.occurred_at = NEW.revoked_at
    )
)
BEGIN SELECT RAISE(ABORT,'subject_role_grant_update_forbidden'); END;
CREATE TRIGGER trg_subject_role_grant_no_delete BEFORE DELETE ON subject_role_grants BEGIN SELECT RAISE(ABORT,'subject_role_grant_history_retained'); END;
CREATE TRIGGER trg_subject_access_grant_restrict_update
BEFORE UPDATE ON subject_access_grants
WHEN NOT (
    OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL
    AND NEW.access_grant_id = OLD.access_grant_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.consumer_principal_id = OLD.consumer_principal_id
    AND NEW.purpose_code IS OLD.purpose_code
    AND NEW.purpose_ref IS OLD.purpose_ref
    AND NEW.task_ref IS OLD.task_ref
    AND NEW.domain_code = OLD.domain_code
    AND NEW.output_kinds = OLD.output_kinds
    AND NEW.sensitivity_ceiling = OLD.sensitivity_ceiling
    AND NEW.policy_id = OLD.policy_id
    AND NEW.issued_by_principal_id = OLD.issued_by_principal_id
    AND NEW.authority_event_id = OLD.authority_event_id
    AND NEW.effective_from = OLD.effective_from
    AND NEW.expires_at = OLD.expires_at
    AND NEW.created_at = OLD.created_at
    AND OLD.revocation_event_id IS NULL AND NEW.revocation_event_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants issuer
          ON issuer.subject_id = OLD.subject_id
         AND issuer.principal_id = e.actor_principal_id
         AND issuer.role IN ('subject','controller')
         AND issuer.role = e.actor_role
         AND (issuer.revoked_at IS NULL OR issuer.revoked_at > e.occurred_at)
         AND issuer.effective_from <= e.occurred_at
         AND (issuer.expires_at IS NULL OR issuer.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.revocation_event_id
          AND e.event_kind = 'auth.access_grant.revoked'
          AND e.subject_id = OLD.subject_id
          AND e.actor_role IN ('subject','controller')
          AND e.occurred_at = NEW.revoked_at
    )
)
BEGIN SELECT RAISE(ABORT,'subject_access_grant_update_forbidden'); END;
CREATE TRIGGER trg_subject_access_grant_no_delete BEFORE DELETE ON subject_access_grants BEGIN SELECT RAISE(ABORT,'subject_access_grant_history_retained'); END;
CREATE TRIGGER trg_subject_events_no_update BEFORE UPDATE ON subject_events BEGIN SELECT RAISE(ABORT,'subject_events_append_only'); END;
CREATE TRIGGER trg_subject_events_no_delete BEFORE DELETE ON subject_events BEGIN SELECT RAISE(ABORT,'subject_events_append_only'); END;
CREATE TRIGGER trg_subject_assertions_restrict_update
BEFORE UPDATE ON subject_assertions
WHEN NOT (
    OLD.lifecycle = 'active'
    AND NEW.lifecycle IN ('superseded','revoked','expired','deleted')
    AND NEW.assertion_id = OLD.assertion_id
    AND NEW.model_owner_subject_id = OLD.model_owner_subject_id
    AND NEW.about_subject_id = OLD.about_subject_id
    AND NEW.namespace = OLD.namespace
    AND NEW.relationship_id IS OLD.relationship_id
    AND NEW.assertion_class = OLD.assertion_class
    AND NEW.semantic_kind = OLD.semantic_kind
    AND NEW.domain_code = OLD.domain_code
    AND NEW.value_payload_id IS OLD.value_payload_id
    AND NEW.confidence IS OLD.confidence
    AND NEW.value_state = OLD.value_state
    AND NEW.actor_principal_id = OLD.actor_principal_id
    AND NEW.actor_role = OLD.actor_role
    AND NEW.authority_event_id IS OLD.authority_event_id
    AND NEW.confirmation_event_id IS OLD.confirmation_event_id
    AND OLD.termination_event_id IS NULL
    AND NEW.termination_event_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = OLD.model_owner_subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role IN ('subject','controller')
         AND g.role = e.actor_role
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.termination_event_id
          AND e.event_kind = CASE NEW.lifecycle
              WHEN 'superseded' THEN 'assertion.superseded'
              WHEN 'revoked' THEN 'assertion.revoked'
              WHEN 'expired' THEN 'assertion.expired'
              WHEN 'deleted' THEN 'assertion.deleted'
          END
          AND e.subject_id = OLD.model_owner_subject_id
          AND e.occurred_at = NEW.effective_until
    )
    AND NEW.sensitivity = OLD.sensitivity
    AND NEW.policy_id IS OLD.policy_id
    AND NEW.supersedes_assertion_id IS OLD.supersedes_assertion_id
    AND NEW.effective_from = OLD.effective_from
    AND NEW.effective_until IS NOT NULL
    AND NEW.effective_until >= OLD.effective_from
    AND NEW.effective_until >= OLD.recorded_at
    AND (
        OLD.namespace <> 'perspective'
        OR EXISTS (
            SELECT 1 FROM subject_relationships r
            JOIN subject_events e ON e.event_id = NEW.termination_event_id
            WHERE r.relationship_id = OLD.relationship_id
              AND r.effective_from <= e.occurred_at
              AND (r.effective_until IS NULL OR r.effective_until > e.occurred_at)
        )
    )
    AND NEW.recorded_at = OLD.recorded_at
    AND (
        NEW.lifecycle <> 'superseded'
        OR EXISTS (
            SELECT 1 FROM subject_assertions successor
            WHERE successor.supersedes_assertion_id = OLD.assertion_id
        )
    )
    AND (
        NEW.lifecycle <> 'deleted'
        OR OLD.value_payload_id IS NULL
        OR EXISTS (
            SELECT 1
            FROM subject_payload_objects deleted_payload
            JOIN subject_purge_jobs completed_purge ON completed_purge.payload_id = deleted_payload.payload_id
            WHERE deleted_payload.payload_id = OLD.value_payload_id
              AND deleted_payload.lifecycle = 'purged'
              AND completed_purge.state = 'succeeded'
        )
    )
)
BEGIN SELECT RAISE(ABORT,'subject_assertion_update_forbidden'); END;
CREATE TRIGGER trg_subject_assertions_no_delete BEFORE DELETE ON subject_assertions BEGIN SELECT RAISE(ABORT,'subject_assertions_immutable'); END;
CREATE TRIGGER trg_subject_assertion_evidence_no_update BEFORE UPDATE ON subject_assertion_evidence BEGIN SELECT RAISE(ABORT,'subject_assertion_evidence_immutable'); END;
CREATE TRIGGER trg_subject_assertion_evidence_no_delete BEFORE DELETE ON subject_assertion_evidence BEGIN SELECT RAISE(ABORT,'subject_assertion_evidence_immutable'); END;
CREATE TRIGGER trg_subject_candidate_reviews_no_update BEFORE UPDATE ON subject_candidate_reviews BEGIN SELECT RAISE(ABORT,'subject_candidate_reviews_append_only'); END;
CREATE TRIGGER trg_subject_candidate_reviews_no_delete BEFORE DELETE ON subject_candidate_reviews BEGIN SELECT RAISE(ABORT,'subject_candidate_reviews_append_only'); END;
CREATE TRIGGER trg_subject_delegation_rule_insert_guard
BEFORE INSERT ON subject_delegation_rules
WHEN COALESCE((SELECT status FROM subject_policies WHERE policy_id = NEW.policy_id), 'missing') <> 'draft'
BEGIN SELECT RAISE(ABORT,'delegation_rule_parent_not_draft'); END;
CREATE TRIGGER trg_subject_delegation_rule_update_guard
BEFORE UPDATE ON subject_delegation_rules
WHEN NOT (
    NEW.policy_id = OLD.policy_id
    AND (
        COALESCE((SELECT status FROM subject_policies WHERE policy_id = OLD.policy_id), 'missing') = 'draft'
        OR (
            COALESCE((SELECT status FROM subject_policies WHERE policy_id = OLD.policy_id), 'missing') = 'sealed'
            AND OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL
            AND OLD.revocation_event_id IS NULL AND NEW.revocation_event_id IS NOT NULL
            AND NEW.delegation_rule_id = OLD.delegation_rule_id
            AND NEW.domain_code = OLD.domain_code
            AND NEW.stakes = OLD.stakes
            AND NEW.reversibility = OLD.reversibility
            AND NEW.cost_ceiling_minor = OLD.cost_ceiling_minor
            AND NEW.currency_code = OLD.currency_code
            AND NEW.approval_mode = OLD.approval_mode
            AND NEW.effective_from = OLD.effective_from
            AND NEW.expires_at = OLD.expires_at
            AND NEW.created_at = OLD.created_at
            AND EXISTS (
                SELECT 1 FROM subject_events e
                JOIN subject_policies p ON p.policy_id = OLD.policy_id
                JOIN subject_role_grants g
                  ON g.subject_id = p.subject_id
                 AND g.principal_id = e.actor_principal_id
                 AND g.role IN ('subject','controller')
                 AND g.role = e.actor_role
                 AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
                 AND g.effective_from <= e.occurred_at
                 AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
                WHERE e.event_id = NEW.revocation_event_id
                  AND e.event_kind = 'delegation.rule_revoked'
                  AND e.subject_id = p.subject_id
                  AND e.actor_role IN ('subject','controller')
                  AND e.occurred_at = NEW.revoked_at
            )
        )
    )
)
BEGIN SELECT RAISE(ABORT,'sealed_delegation_rule_immutable_or_reparent_forbidden'); END;
CREATE TRIGGER trg_subject_delegation_rule_delete_guard
BEFORE DELETE ON subject_delegation_rules
WHEN COALESCE((SELECT status FROM subject_policies WHERE policy_id = OLD.policy_id), 'missing') <> 'draft'
BEGIN SELECT RAISE(ABORT,'sealed_delegation_rule_immutable'); END;
CREATE TRIGGER trg_subject_model_entries_insert_guard
BEFORE INSERT ON subject_model_entries
WHEN COALESCE((SELECT status FROM subject_models WHERE model_id = NEW.model_id), 'missing') <> 'draft'
 OR (NEW.source_type = 'assertion' AND NOT EXISTS (
    SELECT 1 FROM subject_models m
    JOIN subject_assertions a ON a.assertion_id = NEW.source_id
    WHERE m.model_id = NEW.model_id
      AND a.model_owner_subject_id = m.subject_id
      AND a.domain_code = NEW.domain_code
      AND a.lifecycle = 'active'
      AND a.recorded_at <= m.generated_at
      AND a.effective_from <= m.data_window_end
      AND (a.effective_until IS NULL OR a.effective_until > m.data_window_start)
      AND NEW.output_kind IN ('descriptive','aspirational')
      AND (
          a.assertion_class = 'explicit'
          OR EXISTS (
              SELECT 1 FROM subject_assertion_evidence ae
              JOIN subject_evidence ev ON ev.evidence_id = ae.evidence_id
              WHERE ae.assertion_id = a.assertion_id
                AND ae.polarity = 'support'
                AND ev.about_subject_id = a.about_subject_id
          )
      )
 ))
 OR (NEW.source_type = 'policy' AND NOT EXISTS (
    SELECT 1 FROM subject_models m
    JOIN subject_policies p ON p.policy_id = NEW.source_id
    WHERE m.model_id = NEW.model_id
      AND p.subject_id = m.subject_id
      AND p.status = 'sealed'
      AND p.effective_from <= m.data_window_end
      AND (p.effective_until IS NULL OR p.effective_until > m.data_window_start)
      AND p.effective_from <= m.generated_at
      AND (
          (NEW.output_kind = 'delegation_policy' AND p.policy_kind = 'delegation')
          OR (NEW.output_kind = 'decision_policy' AND p.policy_kind IN ('model','review','privacy','counterparty'))
      )
 ))
BEGIN SELECT RAISE(ABORT,'model_entry_parent_or_source_topology_invalid'); END;
CREATE TRIGGER trg_subject_model_entries_no_update BEFORE UPDATE ON subject_model_entries BEGIN SELECT RAISE(ABORT,'subject_model_entries_immutable'); END;
CREATE TRIGGER trg_subject_model_entries_no_delete BEFORE DELETE ON subject_model_entries BEGIN SELECT RAISE(ABORT,'subject_model_entries_immutable'); END;
CREATE TRIGGER trg_subject_pack_runs_seal
BEFORE UPDATE ON subject_context_pack_runs
WHEN NOT (
    OLD.state = 'draft' AND NEW.state = 'sealed'
    AND NEW.pack_run_id = OLD.pack_run_id
    AND NEW.pack_contract_version = OLD.pack_contract_version
    AND NEW.subject_id = OLD.subject_id
    AND NEW.model_id = OLD.model_id
    AND NEW.access_grant_id = OLD.access_grant_id
    AND NEW.consumer_principal_id = OLD.consumer_principal_id
    AND NEW.purpose_code IS OLD.purpose_code
    AND NEW.purpose_ref IS OLD.purpose_ref
    AND NEW.task_ref IS OLD.task_ref
    AND NEW.policy_id = OLD.policy_id
    AND NEW.generated_at = OLD.generated_at
    AND NEW.included_entry_count = (SELECT COUNT(*) FROM subject_context_pack_entries e WHERE e.pack_run_id = OLD.pack_run_id)
    AND NEW.coverage_unknown_count >= 0
    AND NEW.excluded_auth_count >= 0
    AND NEW.excluded_grant_count >= 0
    AND NEW.excluded_purpose_count >= 0
    AND NEW.excluded_domain_count >= 0
    AND NEW.excluded_sensitivity_count >= 0
    AND NEW.excluded_minimization_count >= 0
    AND NEW.content_integrity_mac IS NOT NULL
    AND NEW.sealed_at IS NOT NULL
    AND NEW.sealed_at >= NEW.generated_at
    AND EXISTS (
        SELECT 1
        FROM subject_models m
        JOIN subject_policies mp ON mp.policy_id = m.policy_id
        JOIN subject_access_grants g ON g.access_grant_id = NEW.access_grant_id
        JOIN subject_policies gp ON gp.policy_id = g.policy_id
        WHERE m.model_id = NEW.model_id
          AND m.subject_id = NEW.subject_id
          AND m.status = 'sealed'
          AND m.generated_at <= NEW.generated_at
          AND mp.policy_id = NEW.policy_id
          AND mp.subject_id = NEW.subject_id
          AND mp.policy_kind = 'model'
          AND mp.status = 'sealed'
          AND mp.effective_from <= NEW.generated_at
          AND (mp.effective_until IS NULL OR mp.effective_until > NEW.generated_at)
          AND mp.effective_from <= NEW.sealed_at
          AND (mp.effective_until IS NULL OR mp.effective_until > NEW.sealed_at)
          AND g.subject_id = NEW.subject_id
          AND g.consumer_principal_id = NEW.consumer_principal_id
          AND g.purpose_code IS NEW.purpose_code
          AND g.purpose_ref IS NEW.purpose_ref
          AND g.task_ref IS NEW.task_ref
          AND (g.revoked_at IS NULL OR g.revoked_at > NEW.generated_at)
          AND (g.revoked_at IS NULL OR g.revoked_at > NEW.sealed_at)
          AND g.effective_from <= NEW.generated_at
          AND g.expires_at > NEW.generated_at
          AND g.effective_from <= NEW.sealed_at
          AND g.expires_at > NEW.sealed_at
          AND gp.subject_id = NEW.subject_id
          AND gp.policy_kind = 'access'
          AND gp.status = 'sealed'
          AND gp.effective_from <= NEW.generated_at
          AND (gp.effective_until IS NULL OR gp.effective_until > NEW.generated_at)
          AND gp.effective_from <= NEW.sealed_at
          AND (gp.effective_until IS NULL OR gp.effective_until > NEW.sealed_at)
    )
    AND NOT EXISTS (
        SELECT 1 FROM subject_context_pack_entries pe
        WHERE pe.pack_run_id = OLD.pack_run_id
          AND NOT EXISTS (
              SELECT 1
              FROM subject_model_entries me
              JOIN subject_access_grants eg ON eg.access_grant_id = NEW.access_grant_id
              WHERE me.model_id = NEW.model_id
                AND eg.subject_id = NEW.subject_id
                AND eg.consumer_principal_id = NEW.consumer_principal_id
                AND eg.purpose_code IS NEW.purpose_code
                AND eg.purpose_ref IS NEW.purpose_ref
                AND eg.task_ref IS NEW.task_ref
                AND (eg.revoked_at IS NULL OR eg.revoked_at > NEW.sealed_at)
                AND eg.effective_from <= NEW.sealed_at
                AND eg.expires_at > NEW.sealed_at
                AND eg.domain_code = me.domain_code
                AND instr(',' || eg.output_kinds || ',', ',' || me.output_kind || ',') > 0
                AND ((pe.source_type = 'model_entry' AND pe.source_id = me.model_entry_id)
                  OR (pe.source_type IN ('assertion','policy') AND pe.source_type = me.source_type AND pe.source_id = me.source_id))
                AND ((me.source_type = 'assertion' AND EXISTS (
                    SELECT 1 FROM subject_assertions sa
                    WHERE sa.assertion_id = me.source_id
                      AND sa.model_owner_subject_id = NEW.subject_id
                      AND sa.lifecycle = 'active'
                      AND sa.domain_code = eg.domain_code
                      AND sa.recorded_at <= NEW.generated_at
                      AND sa.effective_from <= NEW.generated_at
                      AND (sa.effective_until IS NULL OR sa.effective_until > NEW.generated_at)
                      AND (sa.effective_until IS NULL OR sa.effective_until > NEW.sealed_at)
                      AND CASE sa.sensitivity WHEN 'public' THEN 1 WHEN 'internal' THEN 2 WHEN 'private' THEN 3 ELSE 4 END
                          <= CASE eg.sensitivity_ceiling WHEN 'public' THEN 1 WHEN 'internal' THEN 2 WHEN 'private' THEN 3 ELSE 4 END
                )) OR (me.source_type = 'policy' AND EXISTS (
                    SELECT 1 FROM subject_policies sp
                    WHERE sp.policy_id = me.source_id
                      AND sp.subject_id = NEW.subject_id
                      AND sp.status = 'sealed'
                      AND sp.effective_from <= NEW.generated_at
                      AND (sp.effective_until IS NULL OR sp.effective_until > NEW.generated_at)
                      AND (sp.effective_until IS NULL OR sp.effective_until > NEW.sealed_at)
                )))
          )
    )
    AND (
        (NEW.action_authority = 0 AND NEW.delegation_rule_id IS NULL)
        OR
        (NEW.action_authority = 1 AND NEW.delegation_rule_id IS NOT NULL AND EXISTS (
            SELECT 1
            FROM subject_delegation_rules r
            JOIN subject_policies p ON p.policy_id = r.policy_id
            JOIN subject_access_grants g ON g.access_grant_id = NEW.access_grant_id
            WHERE r.delegation_rule_id = NEW.delegation_rule_id
              AND p.subject_id = NEW.subject_id
              AND p.policy_kind = 'delegation'
              AND p.status = 'sealed'
              AND p.effective_from <= NEW.generated_at
              AND (p.effective_until IS NULL OR p.effective_until > NEW.generated_at)
              AND p.effective_from <= NEW.sealed_at
              AND (p.effective_until IS NULL OR p.effective_until > NEW.sealed_at)
              AND r.approval_mode = 'bounded_autonomy'
              AND (r.revoked_at IS NULL OR r.revoked_at > NEW.generated_at)
              AND (r.revoked_at IS NULL OR r.revoked_at > NEW.sealed_at)
              AND r.effective_from <= NEW.generated_at
              AND r.expires_at > NEW.generated_at
              AND r.effective_from <= NEW.sealed_at
              AND r.expires_at > NEW.sealed_at
              AND r.domain_code = NEW.action_domain_code
              AND g.domain_code = NEW.action_domain_code
              AND r.stakes = NEW.action_stakes
              AND r.reversibility = NEW.action_reversibility
              AND r.cost_ceiling_minor >= NEW.action_cost_minor
              AND r.currency_code = NEW.action_currency_code
        ))
    )
)
BEGIN SELECT RAISE(ABORT,'invalid_subject_pack_seal'); END;
CREATE TRIGGER trg_subject_pack_runs_no_delete BEFORE DELETE ON subject_context_pack_runs BEGIN SELECT RAISE(ABORT,'subject_pack_runs_immutable'); END;
CREATE TRIGGER trg_subject_pack_entries_insert_guard
BEFORE INSERT ON subject_context_pack_entries
WHEN COALESCE((SELECT state FROM subject_context_pack_runs WHERE pack_run_id = NEW.pack_run_id), 'missing') <> 'draft'
 OR NOT EXISTS (
    SELECT 1
    FROM subject_context_pack_runs p
    JOIN subject_access_grants g ON g.access_grant_id = p.access_grant_id
    JOIN subject_model_entries me ON me.model_id = p.model_id
    WHERE p.pack_run_id = NEW.pack_run_id
      AND g.subject_id = p.subject_id
      AND g.consumer_principal_id = p.consumer_principal_id
      AND g.domain_code = me.domain_code
      AND instr(',' || g.output_kinds || ',', ',' || me.output_kind || ',') > 0
      AND (g.revoked_at IS NULL OR g.revoked_at > p.generated_at)
      AND g.effective_from <= p.generated_at
      AND g.expires_at > p.generated_at
      AND (
          (NEW.source_type = 'model_entry' AND me.model_entry_id = NEW.source_id)
          OR (NEW.source_type IN ('assertion','policy') AND me.source_type = NEW.source_type AND me.source_id = NEW.source_id)
      )
      AND (
          (me.source_type = 'policy' AND EXISTS (
              SELECT 1 FROM subject_policies sp
              WHERE sp.policy_id = me.source_id
                AND sp.subject_id = p.subject_id
                AND sp.status = 'sealed'
                AND sp.effective_from <= p.generated_at
                AND (sp.effective_until IS NULL OR sp.effective_until > p.generated_at)
          ))
          OR (me.source_type = 'assertion' AND EXISTS (
              SELECT 1 FROM subject_assertions sa
              WHERE sa.assertion_id = me.source_id
                AND sa.model_owner_subject_id = p.subject_id
                AND sa.lifecycle = 'active'
                AND sa.domain_code = g.domain_code
                AND sa.recorded_at <= p.generated_at
                AND sa.effective_from <= p.generated_at
                AND (sa.effective_until IS NULL OR sa.effective_until > p.generated_at)
                AND CASE sa.sensitivity
                    WHEN 'public' THEN 1 WHEN 'internal' THEN 2 WHEN 'private' THEN 3 ELSE 4
                END <= CASE g.sensitivity_ceiling
                    WHEN 'public' THEN 1 WHEN 'internal' THEN 2 WHEN 'private' THEN 3 ELSE 4
                END
          ))
      )
 )
BEGIN SELECT RAISE(ABORT,'subject_pack_entry_parent_or_authorized_source_invalid'); END;
CREATE TRIGGER trg_subject_pack_entries_no_update BEFORE UPDATE ON subject_context_pack_entries BEGIN SELECT RAISE(ABORT,'subject_pack_entries_immutable'); END;
CREATE TRIGGER trg_subject_pack_entries_no_delete BEFORE DELETE ON subject_context_pack_entries BEGIN SELECT RAISE(ABORT,'subject_pack_entries_immutable'); END;
CREATE TRIGGER trg_decision_event_insert_guard
BEFORE INSERT ON decision_episode_events
WHEN NEW.authority_event_id IS NULL
 OR NEW.sequence <> COALESCE((SELECT MAX(sequence) + 1 FROM decision_episode_events WHERE episode_id = NEW.episode_id), 1)
 OR NOT EXISTS (
    SELECT 1 FROM decision_episodes d
    JOIN subject_events e
      ON e.event_id = NEW.authority_event_id
     AND e.event_kind = 'decision.' || NEW.event_kind
     AND e.subject_id = d.subject_id
     AND e.actor_principal_id = NEW.actor_principal_id
     AND e.occurred_at = NEW.occurred_at
     AND NEW.occurred_at <= NEW.recorded_at
     AND e.actor_role = CASE NEW.actor_role
         WHEN 'agent' THEN 'observer'
         WHEN 'service' THEN 'authority_source'
         ELSE NEW.actor_role
     END
    JOIN subject_role_grants g
      ON g.subject_id = d.subject_id
     AND g.principal_id = NEW.actor_principal_id
     AND g.role = CASE NEW.actor_role
         WHEN 'agent' THEN 'observer'
         WHEN 'service' THEN 'authority_source'
         ELSE NEW.actor_role
     END
     AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
     AND g.effective_from <= e.occurred_at
     AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
    WHERE d.episode_id = NEW.episode_id
      AND d.lifecycle = 'open'
      AND d.projected_through_sequence = NEW.sequence - 1
      AND (NEW.payload_id IS NULL OR EXISTS (
          SELECT 1 FROM subject_payload_objects p
          WHERE p.payload_id = NEW.payload_id
            AND p.subject_id = d.subject_id
            AND p.payload_kind = 'decision_event'
            AND p.lifecycle = 'active'
      ))
      AND (NEW.event_kind <> 'created' OR NEW.sequence = 1)
      AND (NEW.event_kind = 'created' OR NEW.sequence > 1)
      AND (NEW.event_kind NOT IN ('actual_choice_confirmed','subject_reason_added') OR NEW.actor_role = 'subject')
      AND (NEW.event_kind NOT IN ('reviewed','corrected') OR NEW.actor_role IN ('subject','controller','reviewer'))
      AND (NEW.event_kind NOT IN ('episode_closed','episode_revoked') OR NEW.actor_role IN ('subject','controller'))
 )
BEGIN SELECT RAISE(ABORT,'decision_event_authority_sequence_or_payload_invalid'); END;
CREATE TRIGGER trg_decision_episode_projection_update
BEFORE UPDATE ON decision_episodes
WHEN NOT (
    NEW.episode_id = OLD.episode_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.domain_code = OLD.domain_code
    AND NEW.created_event_id = OLD.created_event_id
    AND NEW.created_at = OLD.created_at
    AND NEW.projected_through_sequence = OLD.projected_through_sequence + 1
    AND NEW.projected_through_sequence = (SELECT MAX(sequence) FROM decision_episode_events WHERE episode_id = OLD.episode_id)
    AND NEW.projection_integrity_mac <> OLD.projection_integrity_mac
    AND NEW.lifecycle = CASE
        WHEN (SELECT event_kind FROM decision_episode_events WHERE episode_id = OLD.episode_id AND sequence = NEW.projected_through_sequence) = 'episode_closed' THEN 'closed'
        WHEN (SELECT event_kind FROM decision_episode_events WHERE episode_id = OLD.episode_id AND sequence = NEW.projected_through_sequence) = 'episode_revoked' THEN 'revoked'
        ELSE OLD.lifecycle
    END
    AND NEW.review_state = CASE
        WHEN (SELECT event_kind FROM decision_episode_events WHERE episode_id = OLD.episode_id AND sequence = NEW.projected_through_sequence) = 'reviewed' THEN 'reviewed'
        WHEN (SELECT event_kind FROM decision_episode_events WHERE episode_id = OLD.episode_id AND sequence = NEW.projected_through_sequence) = 'corrected' THEN 'disputed'
        ELSE OLD.review_state
    END
    AND (NEW.lifecycle = OLD.lifecycle OR EXISTS (
        SELECT 1 FROM decision_episode_events de
        WHERE de.episode_id = OLD.episode_id
          AND de.sequence = NEW.projected_through_sequence
          AND de.event_kind = CASE NEW.lifecycle WHEN 'closed' THEN 'episode_closed' ELSE 'episode_revoked' END
    ))
    AND (NEW.review_state = OLD.review_state OR EXISTS (
        SELECT 1 FROM decision_episode_events de
        WHERE de.episode_id = OLD.episode_id
          AND de.sequence = NEW.projected_through_sequence
          AND de.event_kind = CASE NEW.review_state WHEN 'reviewed' THEN 'reviewed' ELSE 'corrected' END
    ))
)
BEGIN SELECT RAISE(ABORT,'decision_episode_projection_update_forbidden'); END;
CREATE TRIGGER trg_decision_episode_no_delete BEFORE DELETE ON decision_episodes BEGIN SELECT RAISE(ABORT,'decision_episode_history_retained'); END;
CREATE TRIGGER trg_decision_events_no_update BEFORE UPDATE ON decision_episode_events BEGIN SELECT RAISE(ABORT,'decision_events_append_only'); END;
CREATE TRIGGER trg_decision_events_no_delete BEFORE DELETE ON decision_episode_events BEGIN SELECT RAISE(ABORT,'decision_events_append_only'); END;
CREATE TRIGGER trg_subject_eval_events_no_update BEFORE UPDATE ON subject_evaluation_events BEGIN SELECT RAISE(ABORT,'subject_evaluation_events_append_only'); END;
CREATE TRIGGER trg_subject_eval_events_no_delete BEFORE DELETE ON subject_evaluation_events BEGIN SELECT RAISE(ABORT,'subject_evaluation_events_append_only'); END;
CREATE TRIGGER trg_subject_eval_signoffs_no_update BEFORE UPDATE ON subject_evaluation_signoffs BEGIN SELECT RAISE(ABORT,'subject_evaluation_signoffs_append_only'); END;
CREATE TRIGGER trg_subject_eval_signoffs_no_delete BEFORE DELETE ON subject_evaluation_signoffs BEGIN SELECT RAISE(ABORT,'subject_evaluation_signoffs_append_only'); END;

-- Only the documented installation transition is mutable.
CREATE TRIGGER trg_subject_installation_transition
BEFORE UPDATE ON subject_installation
WHEN NOT (
    NEW.singleton_id = OLD.singleton_id
    AND NEW.schema_contract_version = OLD.schema_contract_version
    AND (
        (
            OLD.capability_state = 'available_uninitialized'
            AND NEW.capability_state = 'initialized_empty'
            AND OLD.root_subject_id IS NULL
            AND NEW.root_subject_id IS NOT NULL
            AND OLD.initialized_at IS NULL
            AND NEW.initialized_at IS NOT NULL
        )
        OR (
            OLD.capability_state = 'initialized_empty'
            AND NEW.capability_state = 'active'
            AND NEW.root_subject_id = OLD.root_subject_id
            AND NEW.initialized_at = OLD.initialized_at
            AND EXISTS (
                SELECT 1 FROM subject_models current_model
                WHERE current_model.subject_id = OLD.root_subject_id
                  AND current_model.status = 'sealed'
            )
        )
        OR (
            OLD.capability_state = 'active'
            AND NEW.capability_state = 'archived'
            AND NEW.root_subject_id = OLD.root_subject_id
            AND NEW.initialized_at = OLD.initialized_at
        )
        OR (
            OLD.capability_state = 'initialized_empty'
            AND NEW.capability_state = 'archived'
            AND NEW.root_subject_id = OLD.root_subject_id
            AND NEW.initialized_at = OLD.initialized_at
        )
    )
)
BEGIN SELECT RAISE(ABORT,'invalid_subject_installation_transition'); END;
CREATE TRIGGER trg_subject_installation_no_delete BEFORE DELETE ON subject_installation BEGIN SELECT RAISE(ABORT,'subject_installation_singleton'); END;

-- Payload metadata permits only fail-closed purge/unavailable transitions; content is never in SQLite.
CREATE TRIGGER trg_subject_payload_transition
BEFORE UPDATE ON subject_payload_objects
WHEN NOT (
    NEW.payload_id = OLD.payload_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.payload_kind = OLD.payload_kind
    AND NEW.storage_adapter = OLD.storage_adapter
    AND NEW.retention_until IS OLD.retention_until
    AND NEW.created_at = OLD.created_at
    AND (
        (
            OLD.lifecycle = 'active' AND NEW.lifecycle = 'unavailable'
            AND NEW.object_ref IS OLD.object_ref
            AND NEW.byte_count = OLD.byte_count
            AND NEW.integrity_mac IS OLD.integrity_mac
            AND NEW.purged_at IS NULL
        )
        OR (
            OLD.lifecycle IN ('active','unavailable') AND NEW.lifecycle = 'purge_pending'
            AND NEW.object_ref IS OLD.object_ref
            AND NEW.byte_count = OLD.byte_count
            AND NEW.integrity_mac IS OLD.integrity_mac
            AND NEW.purged_at IS NULL
            AND EXISTS (
                SELECT 1 FROM subject_purge_jobs pending_job
                WHERE pending_job.payload_id = OLD.payload_id
                  AND pending_job.state IN ('pending','running','retryable')
            )
        )
        OR (
            OLD.lifecycle = 'purge_pending' AND NEW.lifecycle = 'purged'
            AND NEW.object_ref IS NULL
            AND NEW.byte_count = 0
            AND NEW.integrity_mac IS NULL
            AND NEW.purged_at IS NOT NULL
            AND EXISTS (
                SELECT 1 FROM subject_purge_jobs succeeded_job
                WHERE succeeded_job.payload_id = OLD.payload_id
                  AND succeeded_job.state = 'succeeded'
            )
        )
        OR (
            OLD.lifecycle = 'purge_pending' AND NEW.lifecycle = 'purge_pending'
            AND OLD.object_ref IS NOT NULL
            AND NEW.object_ref IS NULL
            AND NEW.byte_count = 0
            AND NEW.integrity_mac IS NULL
            AND NEW.purged_at IS NULL
            AND EXISTS (
                SELECT 1 FROM subject_purge_jobs deleting_job
                WHERE deleting_job.payload_id = OLD.payload_id
                  AND deleting_job.state = 'running'
                  AND deleting_job.object_deleted_at IS NOT NULL
                  AND deleting_job.parent_fsynced_at IS NOT NULL
                  AND deleting_job.metadata_cleared_at IS NULL
            )
        )
        OR (
            OLD.lifecycle = 'purge_pending' AND NEW.lifecycle = 'unavailable'
            AND NEW.object_ref IS OLD.object_ref
            AND NEW.byte_count = OLD.byte_count
            AND NEW.integrity_mac IS OLD.integrity_mac
            AND NEW.purged_at IS NULL
            AND EXISTS (
                SELECT 1 FROM subject_purge_jobs failed_job
                WHERE failed_job.payload_id = OLD.payload_id
                  AND failed_job.state = 'failed'
            )
        )
    )
)
BEGIN SELECT RAISE(ABORT,'invalid_subject_payload_transition'); END;
CREATE TRIGGER trg_subject_payload_no_delete BEFORE DELETE ON subject_payload_objects BEGIN SELECT RAISE(ABORT,'subject_payload_metadata_retained'); END;
CREATE TRIGGER trg_subject_purge_job_transition
BEFORE UPDATE ON subject_purge_jobs
WHEN NOT (
    NEW.purge_job_id = OLD.purge_job_id
    AND NEW.payload_id = OLD.payload_id
    AND NEW.requested_by_principal_id = OLD.requested_by_principal_id
    AND NEW.requested_event_id = OLD.requested_event_id
    AND NEW.created_at = OLD.created_at
    AND NEW.updated_at >= OLD.updated_at
    AND (
        (OLD.state = 'pending' AND NEW.state = 'running' AND NEW.attempts = OLD.attempts + 1 AND NEW.completed_at IS NULL
         AND NEW.object_deleted_at IS NULL AND NEW.parent_fsynced_at IS NULL AND NEW.metadata_cleared_at IS NULL)
        OR (OLD.state = 'running' AND NEW.state = 'running' AND NEW.attempts = OLD.attempts AND NEW.completed_at IS NULL
            AND OLD.object_deleted_at IS NULL AND OLD.parent_fsynced_at IS NULL AND OLD.metadata_cleared_at IS NULL
            AND NEW.object_deleted_at IS NOT NULL AND NEW.parent_fsynced_at IS NULL AND NEW.metadata_cleared_at IS NULL
            AND NEW.last_error_code IS NULL)
        OR (OLD.state = 'running' AND NEW.state = 'running' AND NEW.attempts = OLD.attempts AND NEW.completed_at IS NULL
            AND OLD.object_deleted_at IS NOT NULL AND OLD.parent_fsynced_at IS NULL AND OLD.metadata_cleared_at IS NULL
            AND NEW.object_deleted_at = OLD.object_deleted_at AND NEW.parent_fsynced_at IS NOT NULL AND NEW.metadata_cleared_at IS NULL
            AND NEW.last_error_code IS NULL)
        OR (OLD.state = 'running' AND NEW.state = 'retryable' AND NEW.attempts = OLD.attempts AND NEW.last_error_code IS NOT NULL AND NEW.completed_at IS NULL
            AND NEW.object_deleted_at IS OLD.object_deleted_at AND NEW.parent_fsynced_at IS OLD.parent_fsynced_at AND NEW.metadata_cleared_at IS NULL)
        OR (OLD.state = 'retryable' AND NEW.state = 'running' AND NEW.attempts = OLD.attempts + 1 AND NEW.completed_at IS NULL
            AND NEW.object_deleted_at IS OLD.object_deleted_at AND NEW.parent_fsynced_at IS OLD.parent_fsynced_at AND NEW.metadata_cleared_at IS NULL)
        OR (OLD.state = 'running' AND NEW.state = 'succeeded' AND NEW.attempts = OLD.attempts AND NEW.last_error_code IS NULL AND NEW.completed_at IS NOT NULL
            AND OLD.object_deleted_at IS NOT NULL AND OLD.parent_fsynced_at IS NOT NULL AND OLD.metadata_cleared_at IS NULL
            AND NEW.object_deleted_at = OLD.object_deleted_at AND NEW.parent_fsynced_at = OLD.parent_fsynced_at AND NEW.metadata_cleared_at IS NOT NULL
            AND EXISTS (
                SELECT 1 FROM subject_payload_objects p
                WHERE p.payload_id = OLD.payload_id AND p.lifecycle = 'purge_pending'
                  AND p.object_ref IS NULL AND p.integrity_mac IS NULL AND p.byte_count = 0
            ))
        OR (OLD.state IN ('running','retryable') AND NEW.state = 'failed' AND NEW.attempts = OLD.attempts AND NEW.last_error_code IS NOT NULL AND NEW.completed_at IS NOT NULL
            AND NEW.object_deleted_at IS OLD.object_deleted_at AND NEW.parent_fsynced_at IS OLD.parent_fsynced_at AND NEW.metadata_cleared_at IS NULL)
    )
)
BEGIN SELECT RAISE(ABORT,'invalid_subject_purge_job_transition'); END;
CREATE TRIGGER trg_subject_purge_job_no_delete BEFORE DELETE ON subject_purge_jobs BEGIN SELECT RAISE(ABORT,'subject_purge_job_history_retained'); END;

-- Sealed policies/models cannot be edited; successor rows must be inserted.
CREATE TRIGGER trg_subject_policy_draft_transition
BEFORE UPDATE ON subject_policies
WHEN OLD.status = 'draft' AND NOT (
    NEW.status = 'sealed'
    AND NEW.policy_id = OLD.policy_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.policy_kind = OLD.policy_kind
    AND NEW.version = OLD.version
    AND NEW.rules_payload_id = OLD.rules_payload_id
    AND NEW.approved_event_id IS NOT NULL
    AND NEW.effective_from = OLD.effective_from
    AND NEW.effective_until IS NULL
    AND NEW.supersedes_policy_id IS OLD.supersedes_policy_id
    AND NEW.created_at = OLD.created_at
    AND EXISTS (
        SELECT 1 FROM subject_events e
        JOIN subject_role_grants g
          ON g.subject_id = OLD.subject_id
         AND g.principal_id = e.actor_principal_id
         AND g.role IN ('subject','controller')
         AND g.role = e.actor_role
         AND (g.revoked_at IS NULL OR g.revoked_at > e.occurred_at)
         AND g.effective_from <= e.occurred_at
         AND (g.expires_at IS NULL OR g.expires_at > e.occurred_at)
        WHERE e.event_id = NEW.approved_event_id
          AND e.event_kind = 'policy.approved'
          AND e.subject_id = OLD.subject_id
          AND e.actor_role IN ('subject','controller')
          AND e.occurred_at >= OLD.created_at
          AND e.occurred_at <= NEW.effective_from
    )
    AND EXISTS (SELECT 1 FROM subject_payload_objects po WHERE po.payload_id = OLD.rules_payload_id AND po.subject_id = OLD.subject_id AND po.lifecycle = 'active')
)
BEGIN SELECT RAISE(ABORT,'invalid_subject_policy_draft_transition'); END;
CREATE TRIGGER trg_subject_policy_sealed
BEFORE UPDATE ON subject_policies
WHEN OLD.status <> 'draft' AND NOT (
    OLD.status = 'sealed' AND NEW.status IN ('superseded','revoked')
    AND NEW.policy_id = OLD.policy_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.policy_kind = OLD.policy_kind
    AND NEW.version = OLD.version
    AND NEW.rules_payload_id = OLD.rules_payload_id
    AND NEW.approved_event_id = OLD.approved_event_id
    AND NEW.effective_from = OLD.effective_from
    AND NEW.supersedes_policy_id IS OLD.supersedes_policy_id
    AND NEW.created_at = OLD.created_at
    AND NEW.effective_until IS NOT NULL
)
BEGIN SELECT RAISE(ABORT,'sealed_subject_policy_immutable'); END;
CREATE TRIGGER trg_subject_policy_no_delete BEFORE DELETE ON subject_policies BEGIN SELECT RAISE(ABORT,'subject_policy_history_retained'); END;
CREATE TRIGGER trg_subject_model_draft_transition
BEFORE UPDATE ON subject_models
WHEN OLD.status = 'draft' AND NOT (
    NEW.status = 'sealed'
    AND NEW.model_id = OLD.model_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.version = OLD.version
    AND NEW.generated_at = OLD.generated_at
    AND NEW.data_window_start = OLD.data_window_start
    AND NEW.data_window_end = OLD.data_window_end
    AND NEW.policy_id = OLD.policy_id
    AND NEW.producer_principal_id = OLD.producer_principal_id
    AND NEW.coverage_entry_count = (SELECT COUNT(*) FROM subject_model_entries e WHERE e.model_id = OLD.model_id)
    AND NEW.coverage_unknown_count >= 0
    AND NEW.coverage_withheld_count >= 0
    AND NEW.coverage_unavailable_count >= 0
    AND NEW.confidence IS OLD.confidence
    AND NEW.value_state = OLD.value_state
    AND NEW.integrity_mac IS NOT NULL
    AND NEW.supersedes_model_id IS OLD.supersedes_model_id
    AND NEW.created_at = OLD.created_at
    AND EXISTS (
        SELECT 1 FROM subject_policies p
        WHERE p.policy_id = OLD.policy_id AND p.subject_id = OLD.subject_id
          AND p.policy_kind = 'model' AND p.status = 'sealed'
          AND p.effective_from <= OLD.generated_at
          AND (p.effective_until IS NULL OR p.effective_until > OLD.generated_at)
    )
    AND NOT EXISTS (
        SELECT 1 FROM subject_model_entries me
        WHERE me.model_id = OLD.model_id
          AND (
              (me.source_type = 'assertion' AND NOT EXISTS (
                  SELECT 1 FROM subject_assertions a
                  WHERE a.assertion_id = me.source_id
                    AND a.model_owner_subject_id = OLD.subject_id
                    AND a.domain_code = me.domain_code
                    AND a.lifecycle = 'active'
                    AND a.recorded_at <= OLD.generated_at
                    AND a.effective_from <= OLD.data_window_end
                    AND (a.effective_until IS NULL OR a.effective_until > OLD.data_window_start)
              ))
              OR (me.source_type = 'policy' AND NOT EXISTS (
                  SELECT 1 FROM subject_policies sp
                  WHERE sp.policy_id = me.source_id
                    AND sp.subject_id = OLD.subject_id
                    AND sp.status = 'sealed'
                    AND sp.effective_from <= OLD.data_window_end
                    AND (sp.effective_until IS NULL OR sp.effective_until > OLD.data_window_start)
                    AND sp.effective_from <= OLD.generated_at
              ))
          )
    )
)
BEGIN SELECT RAISE(ABORT,'invalid_subject_model_draft_transition'); END;
CREATE TRIGGER trg_subject_model_sealed
BEFORE UPDATE ON subject_models
WHEN OLD.status <> 'draft' AND NOT (
    OLD.status = 'sealed' AND NEW.status IN ('superseded','revoked')
    AND NEW.model_id = OLD.model_id
    AND NEW.subject_id = OLD.subject_id
    AND NEW.version = OLD.version
    AND NEW.generated_at = OLD.generated_at
    AND NEW.data_window_start = OLD.data_window_start
    AND NEW.data_window_end = OLD.data_window_end
    AND NEW.policy_id = OLD.policy_id
    AND NEW.producer_principal_id = OLD.producer_principal_id
    AND NEW.coverage_entry_count = OLD.coverage_entry_count
    AND NEW.coverage_unknown_count = OLD.coverage_unknown_count
    AND NEW.coverage_withheld_count = OLD.coverage_withheld_count
    AND NEW.coverage_unavailable_count = OLD.coverage_unavailable_count
    AND NEW.confidence IS OLD.confidence
    AND NEW.value_state = OLD.value_state
    AND NEW.integrity_mac = OLD.integrity_mac
    AND NEW.supersedes_model_id IS OLD.supersedes_model_id
    AND NEW.created_at = OLD.created_at
)
BEGIN SELECT RAISE(ABORT,'sealed_subject_model_immutable'); END;
CREATE TRIGGER trg_subject_model_no_delete BEFORE DELETE ON subject_models BEGIN SELECT RAISE(ABORT,'subject_model_history_retained'); END;

-- Pilot gate lifecycle is one-way: draft -> frozen -> closed. Cases are preregistered in draft,
-- then receive one immutable completion disposition while frozen; events/signoffs are append-only.
CREATE TRIGGER trg_subject_eval_gate_transition
BEFORE UPDATE ON subject_evaluation_gates
WHEN NOT (
    (
        OLD.state = 'draft' AND NEW.state = 'frozen'
        AND NEW.gate_id = OLD.gate_id
        AND NEW.subject_id = OLD.subject_id
        AND NEW.gate_version = OLD.gate_version
        AND NEW.manifest_sha256 = OLD.manifest_sha256
        AND NEW.eligibility_rules_version = OLD.eligibility_rules_version
        AND NEW.eligibility_rules_sha256 = OLD.eligibility_rules_sha256
        AND NEW.exclusion_rules_version = OLD.exclusion_rules_version
        AND NEW.exclusion_rules_sha256 = OLD.exclusion_rules_sha256
        AND NEW.denominator_rule = OLD.denominator_rule
        AND NEW.minimum_n = OLD.minimum_n
        AND NEW.rounding_rule = OLD.rounding_rule
        AND NEW.utility_threshold = OLD.utility_threshold
        AND NEW.reason_alignment_threshold = OLD.reason_alignment_threshold
        AND NEW.abstention_minimum = OLD.abstention_minimum
        AND NEW.domain_utility_threshold = OLD.domain_utility_threshold
        AND NEW.high_confidence_threshold = OLD.high_confidence_threshold
        AND NEW.hard_failure_rules_version = OLD.hard_failure_rules_version
        AND NEW.hard_failure_rules_sha256 = OLD.hard_failure_rules_sha256
        AND NEW.scoring_definitions_version = OLD.scoring_definitions_version
        AND NEW.scoring_definitions_sha256 = OLD.scoring_definitions_sha256
        AND NEW.reviewer_authority_code = OLD.reviewer_authority_code
        AND OLD.frozen_at IS NULL AND NEW.frozen_at IS NOT NULL
        AND NEW.frozen_at >= OLD.created_at
        AND NEW.closed_at IS NULL AND NEW.scorecard_sha256 IS NULL AND NEW.verdict IS NULL
        AND NEW.created_at = OLD.created_at
    )
    OR
    (
        OLD.state = 'frozen' AND NEW.state = 'closed'
        AND NEW.gate_id = OLD.gate_id
        AND NEW.subject_id = OLD.subject_id
        AND NEW.gate_version = OLD.gate_version
        AND NEW.manifest_sha256 = OLD.manifest_sha256
        AND NEW.eligibility_rules_version = OLD.eligibility_rules_version
        AND NEW.eligibility_rules_sha256 = OLD.eligibility_rules_sha256
        AND NEW.exclusion_rules_version = OLD.exclusion_rules_version
        AND NEW.exclusion_rules_sha256 = OLD.exclusion_rules_sha256
        AND NEW.denominator_rule = OLD.denominator_rule
        AND NEW.minimum_n = OLD.minimum_n
        AND NEW.rounding_rule = OLD.rounding_rule
        AND NEW.utility_threshold = OLD.utility_threshold
        AND NEW.reason_alignment_threshold = OLD.reason_alignment_threshold
        AND NEW.abstention_minimum = OLD.abstention_minimum
        AND NEW.domain_utility_threshold = OLD.domain_utility_threshold
        AND NEW.high_confidence_threshold = OLD.high_confidence_threshold
        AND NEW.hard_failure_rules_version = OLD.hard_failure_rules_version
        AND NEW.hard_failure_rules_sha256 = OLD.hard_failure_rules_sha256
        AND NEW.scoring_definitions_version = OLD.scoring_definitions_version
        AND NEW.scoring_definitions_sha256 = OLD.scoring_definitions_sha256
        AND NEW.reviewer_authority_code = OLD.reviewer_authority_code
        AND NEW.frozen_at = OLD.frozen_at
        AND NEW.closed_at IS NOT NULL AND NEW.scorecard_sha256 IS NOT NULL AND NEW.verdict IS NOT NULL
        AND NEW.closed_at >= OLD.frozen_at
        AND NEW.created_at = OLD.created_at
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_cases c
            WHERE c.gate_id = OLD.gate_id AND c.disposition_at IS NOT NULL
              AND (c.disposition_at < OLD.frozen_at OR c.disposition_at > NEW.closed_at)
        )
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_events e
            WHERE e.gate_id = OLD.gate_id
              AND (e.occurred_at < OLD.frozen_at OR e.occurred_at > NEW.closed_at)
        )
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_signoffs s
            WHERE s.gate_id = OLD.gate_id
              AND (s.signed_at < OLD.frozen_at OR s.signed_at > NEW.closed_at)
        )
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_prediction_assessments p
            WHERE p.gate_id = OLD.gate_id
              AND (p.assessed_at < OLD.frozen_at OR p.assessed_at > NEW.closed_at
                   OR p.reviewed_at < OLD.frozen_at OR p.reviewed_at > NEW.closed_at)
        )
        AND NEW.scorecard_sha256 = (
            SELECT scorecard_sha256 FROM subject_evaluation_scorecard_v1 WHERE gate_id = OLD.gate_id
        )
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_cases c
            WHERE c.gate_id = OLD.gate_id AND c.completion_state = 'preregistered'
        )
        AND (SELECT COUNT(*) FROM subject_evaluation_cases c
             WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed') >= OLD.minimum_n
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_cases c
            WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed'
              AND (SELECT COUNT(*) FROM subject_evaluation_prediction_assessments p
                   WHERE p.gate_id = c.gate_id AND p.evaluation_case_id = c.evaluation_case_id) <> 1
        )
        AND NOT EXISTS (
            SELECT 1 FROM subject_evaluation_cases c
            WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed'
              AND (NOT EXISTS (SELECT 1 FROM subject_evaluation_events e WHERE e.gate_id = c.gate_id AND e.evaluation_case_id = c.evaluation_case_id AND e.event_type = 'utility')
                   OR NOT EXISTS (SELECT 1 FROM subject_evaluation_events e WHERE e.gate_id = c.gate_id AND e.evaluation_case_id = c.evaluation_case_id AND e.event_type = 'reason_alignment')
                   OR NOT EXISTS (SELECT 1 FROM subject_evaluation_events e WHERE e.gate_id = c.gate_id AND e.evaluation_case_id = c.evaluation_case_id AND e.event_type = 'hard_failure')
                   OR (c.is_abstention = 1 AND NOT EXISTS (SELECT 1 FROM subject_evaluation_events e WHERE e.gate_id = c.gate_id AND e.evaluation_case_id = c.evaluation_case_id AND e.event_type = 'abstention')))
        )
        AND (NEW.verdict <> 'pass' OR (
            (SELECT COUNT(DISTINCT c.primary_domain) FROM subject_evaluation_cases c
             WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed') >= 3
            AND NOT EXISTS (
                SELECT c.primary_domain FROM subject_evaluation_cases c
                WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed'
                GROUP BY c.primary_domain HAVING COUNT(*) < 5
            )
            AND (SELECT COUNT(*) FROM subject_evaluation_cases c
                 WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed' AND c.is_abstention = 1) >= 5
            AND (SELECT COUNT(*) FROM subject_evaluation_cases c
                 WHERE c.gate_id = OLD.gate_id AND c.eligible = 1 AND c.completion_state = 'completed'
                   AND (c.has_subject_correction = 1 OR c.has_counter_evidence = 1 OR c.has_contextual_constraint = 1)) >= 3
            AND (SELECT COALESCE(SUM(e.passed),0) FROM subject_evaluation_events e
                 JOIN subject_evaluation_cases c ON c.gate_id=e.gate_id AND c.evaluation_case_id=e.evaluation_case_id
                 WHERE e.gate_id=OLD.gate_id AND e.event_type='utility' AND c.eligible=1 AND c.completion_state='completed')
                >= OLD.utility_threshold * (SELECT COUNT(*) FROM subject_evaluation_cases c WHERE c.gate_id=OLD.gate_id AND c.eligible=1 AND c.completion_state='completed')
            AND (SELECT COALESCE(SUM(e.passed),0) FROM subject_evaluation_events e
                 JOIN subject_evaluation_cases c ON c.gate_id=e.gate_id AND c.evaluation_case_id=e.evaluation_case_id
                 WHERE e.gate_id=OLD.gate_id AND e.event_type='reason_alignment' AND c.eligible=1 AND c.completion_state='completed')
                >= OLD.reason_alignment_threshold * (SELECT COUNT(*) FROM subject_evaluation_cases c WHERE c.gate_id=OLD.gate_id AND c.eligible=1 AND c.completion_state='completed')
            AND (SELECT COALESCE(SUM(e.passed),0) FROM subject_evaluation_events e
                 JOIN subject_evaluation_cases c ON c.gate_id=e.gate_id AND c.evaluation_case_id=e.evaluation_case_id
                 WHERE e.gate_id=OLD.gate_id AND e.event_type='abstention' AND c.eligible=1 AND c.completion_state='completed' AND c.is_abstention=1)
                >= OLD.abstention_minimum * (SELECT COUNT(*) FROM subject_evaluation_cases c WHERE c.gate_id=OLD.gate_id AND c.eligible=1 AND c.completion_state='completed' AND c.is_abstention=1)
            AND NOT EXISTS (
                SELECT c.primary_domain FROM subject_evaluation_cases c
                JOIN subject_evaluation_events e ON e.gate_id=c.gate_id AND e.evaluation_case_id=c.evaluation_case_id AND e.event_type='utility'
                WHERE c.gate_id=OLD.gate_id AND c.eligible=1 AND c.completion_state='completed'
                GROUP BY c.primary_domain HAVING AVG(e.passed) < OLD.domain_utility_threshold
            )
            AND NOT EXISTS (
                SELECT 1 FROM subject_evaluation_events e
                WHERE e.gate_id=OLD.gate_id AND e.event_type='hard_failure' AND e.passed=0
            )
            AND NOT EXISTS (
                SELECT 1 FROM subject_evaluation_prediction_assessments p
                WHERE p.gate_id=OLD.gate_id AND p.assessment_status='reviewed'
                  AND p.prediction_confidence > OLD.high_confidence_threshold
                  AND p.prediction_correct=0
            )
        ))
        AND EXISTS (
            SELECT 1 FROM subject_evaluation_signoffs s
            WHERE s.gate_id = OLD.gate_id AND s.authority_role IN ('subject','controller')
              AND s.scorecard_sha256 = NEW.scorecard_sha256
              AND (NEW.verdict <> 'pass' OR s.decision = 'approve')
        )
        AND EXISTS (
            SELECT 1 FROM subject_evaluation_signoffs s
            WHERE s.gate_id = OLD.gate_id AND s.authority_role = 'fresh_reviewer'
              AND s.scorecard_sha256 = NEW.scorecard_sha256
              AND (NEW.verdict <> 'pass' OR s.decision = 'approve')
        )
    )
)
BEGIN SELECT RAISE(ABORT,'subject_evaluation_gate_transition_invalid_or_incomplete'); END;
CREATE TRIGGER trg_subject_eval_gate_no_delete BEFORE DELETE ON subject_evaluation_gates BEGIN SELECT RAISE(ABORT,'subject_evaluation_gate_history_retained'); END;
CREATE TRIGGER trg_subject_eval_case_insert_guard
BEFORE INSERT ON subject_evaluation_cases
WHEN COALESCE((SELECT state FROM subject_evaluation_gates WHERE gate_id = NEW.gate_id), 'missing') <> 'draft'
  OR NEW.completion_state <> 'preregistered' OR NEW.disposition_at IS NOT NULL
BEGIN SELECT RAISE(ABORT,'subject_evaluation_case_must_be_preregistered_in_draft'); END;
CREATE TRIGGER trg_subject_eval_event_window_insert
BEFORE INSERT ON subject_evaluation_events
WHEN COALESCE((SELECT state FROM subject_evaluation_gates WHERE gate_id = NEW.gate_id), 'missing') <> 'frozen'
 OR NOT EXISTS (
    SELECT 1 FROM subject_evaluation_gates eg
    JOIN subject_role_grants rg
      ON rg.subject_id = eg.subject_id
     AND rg.principal_id = NEW.actor_principal_id
     AND rg.role IN ('subject','controller','reviewer')
     AND (rg.revoked_at IS NULL OR rg.revoked_at > NEW.occurred_at)
     AND rg.effective_from <= NEW.occurred_at
     AND (rg.expires_at IS NULL OR rg.expires_at > NEW.occurred_at)
    WHERE eg.gate_id = NEW.gate_id
      AND NEW.occurred_at >= eg.frozen_at
 )
BEGIN SELECT RAISE(ABORT,'subject_evaluation_event_outside_frozen_window_or_unauthorized'); END;
CREATE TRIGGER trg_subject_eval_signoff_window_insert
BEFORE INSERT ON subject_evaluation_signoffs
WHEN COALESCE((SELECT state FROM subject_evaluation_gates WHERE gate_id = NEW.gate_id), 'missing') <> 'frozen'
 OR NOT EXISTS (
    SELECT 1
    FROM subject_evaluation_gates g
    JOIN subject_role_grants rg
      ON rg.subject_id = g.subject_id
     AND rg.principal_id = NEW.principal_id
     AND rg.role = CASE WHEN NEW.authority_role = 'fresh_reviewer' THEN 'reviewer' ELSE NEW.authority_role END
     AND (rg.revoked_at IS NULL OR rg.revoked_at > NEW.signed_at)
     AND rg.effective_from <= NEW.signed_at
     AND (rg.expires_at IS NULL OR rg.expires_at > NEW.signed_at)
    WHERE g.gate_id = NEW.gate_id
      AND NEW.signed_at >= g.frozen_at
      AND (NEW.authority_role <> 'fresh_reviewer' OR rg.authority_scope = g.reviewer_authority_code)
 )
BEGIN SELECT RAISE(ABORT,'subject_evaluation_signoff_outside_frozen_window'); END;
CREATE TRIGGER trg_subject_eval_prediction_insert_guard
BEFORE INSERT ON subject_evaluation_prediction_assessments
WHEN COALESCE((SELECT state FROM subject_evaluation_gates WHERE gate_id = NEW.gate_id), 'missing') <> 'frozen'
 OR NOT EXISTS (
    SELECT 1 FROM subject_evaluation_gates g
    JOIN subject_evaluation_cases c ON c.gate_id = g.gate_id AND c.evaluation_case_id = NEW.evaluation_case_id
    JOIN subject_role_grants rg ON rg.subject_id = g.subject_id
      AND rg.principal_id = NEW.subject_principal_id AND rg.role = 'subject'
      AND rg.effective_from <= NEW.assessed_at
      AND (rg.expires_at IS NULL OR rg.expires_at > NEW.assessed_at)
      AND (rg.revoked_at IS NULL OR rg.revoked_at > NEW.assessed_at)
      AND rg.effective_from <= NEW.reviewed_at
      AND (rg.expires_at IS NULL OR rg.expires_at > NEW.reviewed_at)
      AND (rg.revoked_at IS NULL OR rg.revoked_at > NEW.reviewed_at)
    WHERE g.gate_id = NEW.gate_id AND c.eligible = 1 AND c.completion_state = 'completed'
      AND NEW.assessed_at >= g.frozen_at AND NEW.reviewed_at >= g.frozen_at
 )
BEGIN SELECT RAISE(ABORT,'subject_evaluation_prediction_assessment_invalid_or_unauthorized'); END;
CREATE TRIGGER trg_subject_eval_case_update_guard
BEFORE UPDATE ON subject_evaluation_cases
WHEN NOT (
    NEW.evaluation_case_id = OLD.evaluation_case_id
    AND NEW.gate_id = OLD.gate_id
    AND (
        (
            (SELECT state FROM subject_evaluation_gates WHERE gate_id = OLD.gate_id) = 'draft'
            AND NEW.completion_state = 'preregistered' AND NEW.disposition_at IS NULL
        )
        OR
        (
            (SELECT state FROM subject_evaluation_gates WHERE gate_id = OLD.gate_id) = 'frozen'
            AND OLD.completion_state = 'preregistered' AND NEW.completion_state IN ('completed','excluded','incomplete')
            AND OLD.disposition_at IS NULL AND NEW.disposition_at IS NOT NULL
            AND NEW.disposition_at >= (SELECT frozen_at FROM subject_evaluation_gates WHERE gate_id = OLD.gate_id)
            AND NEW.case_integrity_mac = OLD.case_integrity_mac
            AND NEW.primary_domain = OLD.primary_domain
            AND NEW.is_abstention = OLD.is_abstention
            AND NEW.has_subject_correction = OLD.has_subject_correction
            AND NEW.has_counter_evidence = OLD.has_counter_evidence
            AND NEW.has_contextual_constraint = OLD.has_contextual_constraint
            AND NEW.eligible = OLD.eligible
            AND NEW.preregistered_exclusion_code IS OLD.preregistered_exclusion_code
            AND NEW.created_at = OLD.created_at
        )
    )
)
BEGIN SELECT RAISE(ABORT,'subject_evaluation_case_update_forbidden'); END;
CREATE TRIGGER trg_subject_eval_case_frozen_delete
BEFORE DELETE ON subject_evaluation_cases
WHEN (SELECT state FROM subject_evaluation_gates WHERE gate_id = OLD.gate_id) <> 'draft'
BEGIN SELECT RAISE(ABORT,'frozen_subject_evaluation_case_immutable'); END;
CREATE TRIGGER trg_subject_eval_event_no_update BEFORE UPDATE ON subject_evaluation_events BEGIN SELECT RAISE(ABORT,'subject_evaluation_event_append_only'); END;
CREATE TRIGGER trg_subject_eval_event_no_delete BEFORE DELETE ON subject_evaluation_events BEGIN SELECT RAISE(ABORT,'subject_evaluation_event_history_retained'); END;
CREATE TRIGGER trg_subject_eval_signoff_no_update BEFORE UPDATE ON subject_evaluation_signoffs BEGIN SELECT RAISE(ABORT,'subject_evaluation_signoff_append_only'); END;
CREATE TRIGGER trg_subject_eval_signoff_no_delete BEFORE DELETE ON subject_evaluation_signoffs BEGIN SELECT RAISE(ABORT,'subject_evaluation_signoff_history_retained'); END;
CREATE TRIGGER trg_subject_eval_prediction_no_update BEFORE UPDATE ON subject_evaluation_prediction_assessments BEGIN SELECT RAISE(ABORT,'subject_evaluation_prediction_assessment_append_only'); END;
CREATE TRIGGER trg_subject_eval_prediction_no_delete BEFORE DELETE ON subject_evaluation_prediction_assessments BEGIN SELECT RAISE(ABORT,'subject_evaluation_prediction_assessment_append_only'); END;
