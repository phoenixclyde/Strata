import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
src = root / "shared_page" / "conversation-data.json"
data = json.loads(src.read_text(encoding="utf-8"))
lines = []
urls = set()
for i, message in enumerate(data.get("messages", []), 1):
    role = message.get("messageType", "unknown")
    texts = [part.get("text", "") for part in message.get("content", []) if part.get("type") == "text"]
    text = "\n".join(texts).strip()
    if not text:
        continue
    lines.append(f"\n===== {i:03d} {role} =====\n{text}\n")
    urls.update(re.findall(r"https?://[^\s<>()\]\"']+", text))
(root / "conversation.txt").write_text("".join(lines), encoding="utf-8")
(root / "urls.txt").write_text("\n".join(sorted(urls)) + "\n", encoding="utf-8")
print(f"messages={len(data.get('messages', []))} text_messages={len(lines)} urls={len(urls)} chars={sum(map(len, lines))}")
