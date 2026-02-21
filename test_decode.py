import sqlite3
import lz4.block

conn = sqlite3.connect("data/extracted/nwtsty_KO-1c8a6f537094/jwpub_unzip/inner_contents/nwtsty_KO.db")
c = conn.cursor()
c.execute("SELECT Content FROM Document WHERE Content IS NOT NULL LIMIT 1")
row = c.fetchone()
data = row[0]

# JW Library SQLite compressed blobs usually start with a byte indicating compression type
# Or they might have a 4 to 12 byte header. Let's try brute-forcing the offset.
for offset in range(1, 16):
    try:
        decomp = lz4.block.decompress(data[offset:])
        print(f"Success at offset {offset}! text preview:", decomp[:200].decode("utf-8", "ignore"))
        break
    except Exception:
        pass
        
for offset in range(1, 16):
    try:
        decomp = lz4.block.decompress(data[offset:], uncompressed_size=len(data)*20)
        print(f"Success at offset {offset} (with size hint)! text preview:", decomp[:200].decode("utf-8", "ignore"))
        break
    except Exception:
        pass
        
print("Tried all reasonable offsets.")
