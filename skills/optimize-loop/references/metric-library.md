# Metric Library

Copy-paste `Verify` commands by domain. Each prints **one number** to stdout. Adjust flags per your toolchain version.
Direction: **lower** = fewer errors/ms/bytes is better · **higher** = more coverage/accuracy is better.

## Code quality

### Test coverage

```bash
# Jest                                    [higher · low · guard: npm test]
npx jest --coverage --coverageReporters=json-summary 2>/dev/null \
  | node -e "console.log(require('./coverage/coverage-summary.json').total.lines.pct)"

# Vitest                                  [higher · low · guard: npm test]
npx vitest run --coverage 2>/dev/null | grep 'All files' | awk '{print $NF}' | tr -d '%'

# pytest-cov                              [higher · low · guard: pytest]
pytest --cov=src --cov-report=term-missing -q 2>/dev/null | grep TOTAL | awk '{print $NF}' | tr -d '%'

# Go                                      [higher · low · guard: go test ./...]
go test ./... -coverprofile=cover.out -covermode=atomic 2>/dev/null \
  && go tool cover -func=cover.out | grep total | awk '{print $3}' | tr -d '%'
```

### Lint errors

```bash
# ESLint                                  [lower · low · guard: npm test]
npx eslint src -f json 2>/dev/null | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(r.reduce((a,f)=>a+f.errorCount,0))"

# Pylint                                  [lower · low · guard: pytest]
pylint src/ --output-format=json 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(1 for m in d if m['type'] in('error','fatal')))"

# Clippy                                  [lower · low · guard: cargo test]
cargo clippy --message-format=json 2>/dev/null | jq -r 'select(.reason=="compiler-message")|.message.level' | grep -c error
```

### Type errors

```bash
# tsc                                     [lower · low · guard: npm test]
npx tsc --noEmit 2>&1 | grep -c 'error TS' || true

# mypy                                    [lower · low · guard: pytest]
mypy src/ --ignore-missing-imports 2>&1 | tail -1 | awk '{print $1}'
```

## Performance

```bash
# API latency, wrk mean ms                [lower · high · guard: npm test]
wrk -t2 -c10 -d10s http://localhost:3000/api/health 2>/dev/null | grep Latency | awk '{print $2}' | sed 's/ms//'

# Single request ms, curl                 [lower · high · guard: npm test]
curl -o /dev/null -s -w "%{time_total}" http://localhost:3000/api/health | awk '{printf "%.0f\n",$1*1000}'

# Bundle size bytes (Vite/Webpack)        [lower · low · guard: tsc --noEmit]
npm run build 2>/dev/null && find dist -name '*.js' ! -name '*.map' | xargs wc -c | tail -1 | awk '{print $1}'

# Go binary bytes                         [lower · low · guard: go test ./...]
go build -o /tmp/app_m . 2>/dev/null && wc -c < /tmp/app_m

# Build time ms (Node)                    [lower · medium · guard: tsc --noEmit]
start=$(date +%s%N); npm run build 2>/dev/null; echo $(( ($(date +%s%N)-start)/1000000 ))
```

## Security

```bash
# npm audit vuln count                    [lower · low · guard: npm test]
npm audit --json 2>/dev/null | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(r.metadata?.vulnerabilities?.total??0)"

# pip-audit vuln count                    [lower · low · guard: pytest]
pip-audit --format=json 2>/dev/null | python3 -c "import json,sys;print(sum(len(d.get('vulns',[])) for d in json.load(sys.stdin).get('dependencies',[])))"
```

## Lines of code (toolchain-free)

```bash
# find + wc                               [lower · low · guard: npm test]
find src -name '*.ts' -o -name '*.js' | xargs wc -l | tail -1 | awk '{print $1}'

# cloc                                    [lower · low · guard: relevant tests]
cloc src --json 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin)['SUM']['code'])"
```

## ML / data science

```bash
# Eval accuracy                           [higher · high · guard: pytest tests/]
python3 scripts/evaluate.py --split val 2>/dev/null | grep accuracy | awk '{print $NF}'

# sklearn weighted F1                     [higher · high · guard: pytest tests/]
python3 -c "from sklearn.metrics import f1_score;import numpy as np;print(f'{f1_score(np.load(\"data/y_true.npy\"),np.load(\"data/y_pred.npy\"),average=\"weighted\"):.4f}')"
```

## Creating a custom metric

```bash
# 1. Measure exactly one numeric value
# 2. Print it to stdout as the last line
# 3. Exit 0 on success, non-zero on failure (treated as crash)
# 4. Complete in < 30s (sample expensive workloads)
# 5. Be deterministic, or declare Noise: high
YOUR_MEASURE_COMMAND | YOUR_EXTRACT_COMMAND
```

| Rule | Detail |
|---|---|
| One number | stdout last line = a bare number |
| Exit codes | 0 = valid measurement, non-zero = crash (logged, skipped) |
| Runtime | < 30s; sample if expensive |
| Determinism | varies run-to-run → `Noise: high`, 3–5 runs |
| Units | consistent across all iterations; never change mid-loop |
| Direction | declare `lower` or `higher` explicitly |
