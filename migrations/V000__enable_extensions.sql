-- V000__enable_extensions.sql (SQLite)
-- SQLite does not use extensions.
-- Foreign key enforcement must be enabled per connection in your app:
--
--   Node (better-sqlite3): db.pragma('foreign_keys = ON')
--   Python (sqlite3):      conn.execute('PRAGMA foreign_keys = ON')

PRAGMA foreign_keys = ON;
