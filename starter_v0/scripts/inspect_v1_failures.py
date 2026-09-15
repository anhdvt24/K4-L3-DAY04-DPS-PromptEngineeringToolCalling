import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('runs/v1_B_base_gemini_20260915T195258062393.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== V1 FAILURES ===')
for r in data['results']:
    if not r['result']['passed']:
        cid = r['id']
        expected = r['expect']
        actual = r['result'].get('actual_tool_calls', [])
        failure = r['result'].get('failure_type')
        failures = r['result'].get('failures', [])
        inp = r.get('input') or '<multiturn>'
        print(f'{cid} [{failure}]')
        print(f'  input: {inp}')
        print(f'  expected: {json.dumps(expected, ensure_ascii=False)}')
        print(f'  actual:   {json.dumps(actual, ensure_ascii=False)}')
        if failures:
            print(f'  failures detail: {json.dumps(failures, ensure_ascii=False)[:400]}')
        print()
