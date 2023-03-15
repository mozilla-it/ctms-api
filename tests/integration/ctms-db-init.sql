INSERT INTO api_client (
    client_id,
    email,
    enabled,
    hashed_secret,
    create_timestamp,
    update_timestamp
) VALUES (
    'id_integration-test', -- client_id
    'master@local.host', -- email
    true, -- enabled
    -- client_id=id_integration-test
    -- secret=secret_xPS8MJSswx1IYOniwXZUV3vNQ5YnYJz5H1UkOSLKqrk
    -- To generate it, we used:
    --   $ CTMS_DB_URL="postgresql://ctmsuser:ctmsuser@localhost/ctms" CTMS_SECRET_KEY="some-secret" poetry run ctms/bin/client_credentials.py -e master@local.host integration-test
    -- Use the same secret key when running CTMS, or integration tests authentication won't work.
    '$argon2id$v=19$m=65536,t=3,p=4$onSu9d57T+kdg5CyVgoBAA$ZDXuQvC5siA7XEaT+2I+FKprSb6tUL0mWP6qYGdotOQ', -- hashed_secret
    '2023-03-15 16:52:38.542769+01'::timestamp, -- create_timestamp
    '2023-03-15 16:52:38.542769+01'::timestamp -- update_timestamp
) ON CONFLICT DO NOTHING;
