import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Latest V3 runs
runs = [
    ('BASE v3',        'runs/v3_B_base_gemini_20260915T205320244502.json'),
    ('ADVERSARIAL v3', 'runs/v3_B_adversarial_gemini_20260915T205411170586.json'),
    ('GROUP v3',       'runs/v3_B_group_gemini_20260915T205451723067.json'),
]
for suite, fname in runs:
    with open(fname, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"=== {suite}: {data['summary']['passed_cases']}/{data['summary']['total_cases']} ({data['summary']['case_accuracy']*100:.1f}%) ===")
    for r in data['results']:
        if not r['result']['passed']:
            cid = r['id']
            expected = r['expect']
            actual = r['result'].get('actual_tool_calls', [])
            failure = r['result'].get('failure_type')
            failures = r['result'].get('failures', [])
            inp = r.get('input') or r.get('turns') or '<multiturn>'
            print(f'\n{cid} [{failure}]')
            print(f'  input:  {str(inp)[:200]}')
            print(f'  expected: {json.dumps(expected, ensure_ascii=False)}')
            print(f'  actual:   {json.dumps(actual, ensure_ascii=False)}')
            if failures:
                print(f'  detail: {json.dumps(failures, ensure_ascii=False)[:300]}')
    print()
