import json, socket, base64, re, time, concurrent.futures

with open('temp/all_nodes.json', 'r') as f:
    nodes = json.load(f)

print(f'Starting health check for {len(nodes)} nodes...')

def parse_node(node_url):
    try:
        if node_url.startswith('vmess://'):
            b64 = node_url[8:]
            padding = 4 - len(b64) % 4
            if padding != 4: b64 += '=' * padding
            json_str = base64.b64decode(b64).decode('utf-8', errors='ignore')
            data = json.loads(json_str)
            return data.get('add', ''), int(data.get('port', 0))
        elif node_url.startswith('vless://') or node_url.startswith('trojan://'):
            match = re.search(r'://[^@]+@([^:]+):(\d+)', node_url)
            if match: return match.group(1), int(match.group(2))
        elif node_url.startswith('ss://'):
            if '@' in node_url:
                match = re.search(r'@([^:]+):(\d+)', node_url)
                if match: return match.group(1), int(match.group(2))
            else:
                b64_part = node_url[5:].split('#')[0].split('?')[0]
                padding = 4 - len(b64_part) % 4
                if padding != 4: b64_part += '=' * padding
                decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore')
                match = re.search(r'@([^:]+):(\d+)', decoded)
                if match: return match.group(1), int(match.group(2))
        elif node_url.startswith('ssr://'):
            b64 = node_url[6:]
            padding = 4 - len(b64) % 4
            if padding != 4: b64 += '=' * padding
            decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
            parts = decoded.split(':')
            if len(parts) >= 2: return parts[0], int(parts[1])
        elif any(node_url.startswith(p) for p in ['hysteria://', 'hysteria2://', 'tuic://']):
            match = re.search(r'://[^@]*@?([^:]+):(\d+)', node_url)
            if match: return match.group(1), int(match.group(2))
    except: pass
    return None, None

def test_tcp_connect(host, port, timeout=5):
    if not host or not port or port <= 0 or port > 65535:
        return False, 'Invalid host/port'
    try:
        if host in ('127.0.0.1', 'localhost', '0.0.0.0', '::1'):
            return False, 'Local address'
        if host.startswith('192.168.') or host.startswith('10.') or host.startswith('172.'):
            return False, 'Private address'
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0: return True, 'TCP OK'
        return False, f'TCP failed (code {result})'
    except socket.gaierror: return False, 'DNS resolve failed'
    except Exception as e: return False, str(e)

def test_node(node_url):
    host, port = parse_node(node_url)
    if not host: return node_url, False, 'Parse failed', 9999
    start = time.time()
    ok, msg = test_tcp_connect(host, port, timeout=5)
    latency = round((time.time() - start) * 1000, 1)
    return node_url, ok, msg, latency

alive_nodes = []
dead_nodes = []
max_workers = min(50, len(nodes))

with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(test_node, node): node for node in nodes}
    completed = 0
    for future in concurrent.futures.as_completed(futures):
        completed += 1
        if completed % 50 == 0:
            print(f'  Progress: {completed}/{len(nodes)}...')
        try:
            node_url, ok, msg, latency = future.result(timeout=10)
            if ok: alive_nodes.append((node_url, latency))
            else: dead_nodes.append((node_url, msg))
        except Exception as e:
            dead_nodes.append((futures[future], str(e)))

alive_nodes.sort(key=lambda x: x[1])

print()
print('=' * 50)
print('Health Check Results:')
print(f'  Total nodes: {len(nodes)}')
print(f'  Alive: {len(alive_nodes)}')
print(f'  Dead: {len(dead_nodes)}')
print(f'  Alive rate: {len(alive_nodes)/len(nodes)*100:.1f}%')
print('=' * 50)

alive_urls = [n[0] for n in alive_nodes]
if alive_urls:
    merged = '\n'.join(alive_urls)
    encoded = base64.b64encode(merged.encode('utf-8')).decode('utf-8')
else:
    encoded = ''

with open('docs/node.txt', 'w') as f: f.write(encoded)
with open('docs/node_plain.txt', 'w') as f:
    for url, lat in alive_nodes:
        f.write(f'[{lat}ms] {url}\n')

stats = {
    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'total': len(nodes),
    'alive': len(alive_nodes),
    'dead': len(dead_nodes),
    'alive_rate': round(len(alive_nodes)/len(nodes)*100, 1) if nodes else 0,
    'alive_nodes': [{'url': n[0][:50] + '...', 'latency': n[1]} for n in alive_nodes[:20]],
    'dead_reasons': {}
}
for _, reason in dead_nodes:
    stats['dead_reasons'][reason] = stats['dead_reasons'].get(reason, 0) + 1

with open('docs/stats.json', 'w') as f:
    json.dump(stats, f, indent=2)

print(f'Output: docs/node.txt ({len(encoded)} bytes base64)')
print(f'        docs/node_plain.txt ({len(alive_urls)} alive nodes)')
print(f'        docs/stats.json')
