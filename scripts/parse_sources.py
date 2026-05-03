import json, base64

try:
    with open('temp/source3_raw.json', 'r') as f:
        data = json.load(f)
    for key in ['data', 'nodes', 'list', 'result', 'subscription', 'content']:
        if key in data:
            val = data[key]
            if isinstance(val, str):
                try:
                    decoded = base64.b64decode(val).decode('utf-8', errors='ignore')
                    with open('temp/source3.txt', 'w') as f: f.write(decoded)
                    print('Source3: Extracted from field:', key)
                    exit(0)
                except:
                    with open('temp/source3.txt', 'w') as f: f.write(val)
                    print('Source3: Extracted string from:', key)
                    exit(0)
            elif isinstance(val, list):
                nodes = '\n'.join(str(x) for x in val if x)
                encoded = base64.b64encode(nodes.encode()).decode()
                with open('temp/source3.txt', 'w') as f: f.write(encoded)
                print('Source3: Extracted list from:', key)
                exit(0)
    if isinstance(data, list):
        nodes = '\n'.join(str(x) for x in data if x)
        encoded = base64.b64encode(nodes.encode()).decode()
        with open('temp/source3.txt', 'w') as f: f.write(encoded)
        print('Source3: JSON is array')
        exit(0)
    with open('temp/source3.txt', 'w') as f: f.write(json.dumps(data))
    print('Source3: Fallback raw JSON')
except json.JSONDecodeError:
    with open('temp/source3_raw.json', 'r') as f: content = f.read().strip()
    with open('temp/source3.txt', 'w') as f: f.write(content)
    print('Source3: Not JSON, saved as-is')
