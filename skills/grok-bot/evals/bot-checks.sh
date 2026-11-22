# Sourced by the bot-side checks (scenarios 09-18): the bot's reply.md, its card.json and its calls.jsonl.
set -u
calls() {  # the recorded tool calls, one JSON object per line; a line that is not JSON fails the run
  [ -f calls.jsonl ] || return 0
  python3 -c '
import json, sys
for n, line in enumerate(open("calls.jsonl"), 1):
    if line.strip():
        try: print(json.dumps(json.loads(line)))
        except ValueError: sys.exit(f"calls.jsonl line {n} is not JSON")'
}
computer_calls() { calls | python3 -c 'import json,sys; [print(l.strip()) for l in sys.stdin if json.loads(l).get("tool") == "computer"]'; }
reply_ok() { [ -s reply.md ] || { echo "no reply.md"; exit 1; }; }
headline_first() {  # rule 1: the first line is the status dot, a bold headline and the time (unknown is ?)
  first=$(grep -m1 -v '^[[:space:]]*$' reply.md)
  echo "$first" | grep -Eq '^(🟢|🟡|🔴) \*\*[^*]+\*\* · ([0-2][0-9]:[0-5][0-9] ICT|\?( ICT)?)[[:space:]]*$' || { echo "first line is not the headline: $first"; exit 1; }
}
tables_narrow() {  # no markdown table wider than 4 columns
  wide=$(grep -E '^[[:space:]]*\|.*\|[[:space:]]*$' "${1:-reply.md}" | awk -F'|' 'NF-2 > 4 {print NF-2; exit}')
  [ -z "$wide" ] || { echo "a table with $wide columns (at most 4)"; exit 1; }
}
