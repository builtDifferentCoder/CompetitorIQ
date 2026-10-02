"""Sanity check: inspect checkpoints.db tables, counts, and rows."""

import sqlite3

conn = sqlite3.connect("checkpoints.db")
cur = conn.cursor()

print("=" * 70)
print(" SQLITE CHECKPOINTS.DB SANITY CHECK")
print("=" * 70)

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cur.fetchall()]
print(f"\nTables found: {tables}")

for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t};")
    count = cur.fetchone()[0]
    print(f"Total row count in table '{t}': {count}")

print("\n--- SAMPLE CHECKPOINT RECORDS (First 5) ---")
cur.execute("SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, length(checkpoint), length(metadata) FROM checkpoints LIMIT 5;")
for row in cur.fetchall():
    print(f"Thread: {row[0]:<22} | Ckpt ID: {row[1][:18]}... | Type: {row[3]} | Ckpt: {row[4]} bytes | Meta: {row[5]} bytes")

print("\n--- DISTINCT THREADS IN DATABASE ---")
cur.execute("SELECT DISTINCT thread_id FROM checkpoints;")
for row in cur.fetchall():
    print(f"  * {row[0]}")

print("\n--- SAMPLE WRITE RECORDS (First 3) ---")
cur.execute("SELECT thread_id, task_id, idx, channel, type, length(value) FROM writes LIMIT 3;")
for row in cur.fetchall():
    print(f"Thread: {row[0]:<22} | Task: {row[1][:12]}... | Channel: {row[3]:<15} | Type: {row[4]} | Val Bytes: {row[5]}")

print("=" * 70)
conn.close()
