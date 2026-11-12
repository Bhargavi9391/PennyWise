CREATE TABLE lifecycle_events (
    event_id VARCHAR(60) NOT NULL,
    entity_type VARCHAR(40) NOT NULL,
    entity_id VARCHAR(60) NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    old_value VARCHAR(500),
    new_value VARCHAR(500),
    actor VARCHAR(100) NOT NULL DEFAULT 'system',
    reason VARCHAR(500),
    event_timestamp DATETIME NOT NULL,
    PRIMARY KEY (event_id),
    CONSTRAINT check_lifecycle_entity_type
        CHECK (entity_type IN ('Transaction', 'RecurringSeries', 'Budget', 'Insight')),
    CONSTRAINT check_lifecycle_event_type
        CHECK (event_type IN ('Created', 'Updated', 'Status Changed', 'Deleted'))
);

CREATE INDEX ix_lifecycle_entity
    ON lifecycle_events (entity_type, entity_id);

CREATE INDEX ix_lifecycle_timestamp
    ON lifecycle_events (event_timestamp);
