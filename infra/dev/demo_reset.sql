\set QUIET on
\pset footer off
\echo 'demo-reset: rows of workspace' :'workspace_id'

SELECT table_name, rows FROM (
  SELECT 1 AS ord, 'campaign__campaigns' AS table_name, count(*) AS rows FROM campaign__campaigns WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 2, 'campaign__steps', count(*) FROM campaign__steps WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 3, 'campaign__leads', count(*) FROM campaign__leads WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 4, 'campaign__send_jobs', count(*) FROM campaign__send_jobs WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 5, 'campaign__processed_events', count(*) FROM campaign__processed_events WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 6, 'messaging__outbound_messages', count(*) FROM messaging__outbound_messages WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 7, 'messaging__inbound_messages', count(*) FROM messaging__inbound_messages WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 8, 'messaging__outbox_events', count(*) FROM messaging__outbox_events WHERE workspace_id = :'workspace_id'
  UNION ALL SELECT 9, 'messaging__suppressions', count(*) FROM messaging__suppressions WHERE workspace_id = :'workspace_id'
) AS counts ORDER BY ord;

\if :confirm
BEGIN;
DELETE FROM campaign__processed_events WHERE workspace_id = :'workspace_id';
DELETE FROM campaign__send_jobs WHERE workspace_id = :'workspace_id';
DELETE FROM campaign__leads WHERE workspace_id = :'workspace_id';
DELETE FROM campaign__steps WHERE workspace_id = :'workspace_id';
DELETE FROM campaign__campaigns WHERE workspace_id = :'workspace_id';
DELETE FROM messaging__suppressions WHERE workspace_id = :'workspace_id';
DELETE FROM messaging__outbox_events WHERE workspace_id = :'workspace_id';
DELETE FROM messaging__inbound_messages WHERE workspace_id = :'workspace_id';
DELETE FROM messaging__outbound_messages WHERE workspace_id = :'workspace_id';
COMMIT;
\echo 'Deleted. The workspace, its mailbox and the mailbox sync cursor are kept.'
\else
\echo 'Nothing deleted. Run again with CONFIRM=yes to delete these rows.'
\endif
