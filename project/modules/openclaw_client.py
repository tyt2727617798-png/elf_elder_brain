import subprocess
import json
import sys

question = sys.argv[1]
REPLY_FILE = "/tmp/reply.txt"
cmd = [
    "/home/elf/.npm-global/bin/openclaw",
    "agent",
    "--agent",
    "main",
    "--message",
    question,
    "--json"
]

result = subprocess.run(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

reply=""
try:
    data = json.loads(result.stdout)

    # 优先取官方字段
    reply = data["result"].get("finalAssistantVisibleText", "")

    # 如果没有，再从payload取
    if reply == "":
        payloads = data["result"].get("payloads", [])
        if len(payloads) > 0:
            reply = payloads[0].get("text", "")

except Exception as e:
    print(e)

with open(REPLY_FILE, "w", encoding="utf-8") as f:
    f.write(reply)

print("OpenClaw完成")
