#!/usr/bin/env python3
import json, os, re, sys, hashlib
from pathlib import Path
from collections import defaultdict

ROOT = Path.home() / 'projects' / 'grocy-reports'
VAULT_ROOT = Path('/home/yura/obsidian/grocy-code-memory/graphify')
TARGETS = {
    'frontend': ROOT / 'frontend' / 'graphify-out' / 'graph.json',
    'backend': ROOT / 'backend' / 'graphify-out' / 'graph.json',
}


def slugify(name: str) -> str:
    s = re.sub(r'[^\w\-. ]+', '_', name.strip(), flags=re.UNICODE)
    s = s.replace('/', '∕').replace('\\', '⧵').replace(':', '꞉')
    s = re.sub(r'\s+', ' ', s).strip().strip('.')
    if not s:
        s = 'node'
    if len(s) > 120:
        h = hashlib.sha1(name.encode('utf-8')).hexdigest()[:8]
        s = s[:100].rstrip() + ' ' + h
    return s


def wikilink(name: str) -> str:
    return f'[[{slugify(name)}]]'


def community_file_slug(community: str) -> str:
    label = community if community != '' else 'no-community'
    return slugify(f'community-{label}')


def node_ref(name: str, community_by_name: dict) -> str:
    comm = community_by_name.get(name, '')
    return f'[[{community_file_slug(str(comm))}#^{slugify(name)}|{name}]]'


def load_graph(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Unsupported graph format in {path}')
    return data.get('nodes', []), data.get('edges', data.get('links', []))


def node_name(node):
    for key in ('label', 'id', 'name', 'title'):
        if key in node and node[key]:
            return str(node[key])
    return 'unknown-node'


def edge_endpoints(edge):
    src = edge.get('source', edge.get('from', edge.get('src')))
    dst = edge.get('target', edge.get('to', edge.get('dst')))
    rel = edge.get('type', edge.get('label', edge.get('relation', 'related_to')))
    meta = []
    if edge.get('provenance'):
        meta.append(str(edge['provenance']))
    if edge.get('context'):
        meta.append(f"context={edge['context']}")
    return src, dst, rel, ', '.join(meta)


def esc(v):
    return str(v).replace('"', '\\"')


def render_node_section(info, outgoing, incoming, community_by_name):
    slug = slugify(info['name'])
    lines = [
        f'## {info["name"]} ^{slug}',
        '',
        f'- Kind: {info["kind"]}',
        f'- Source: `{info["src"]}`' if info['src'] else '- Source:',
        f'- Location: `{info["loc"]}`' if info['loc'] else '- Location:',
        '',
    ]
    if outgoing:
        lines += ['**Outgoing:**', '']
        for rel, target, meta in outgoing:
            suffix = f' ({meta})' if meta else ''
            lines.append(f'- `{rel}` -> {node_ref(target, community_by_name)}{suffix}')
        lines.append('')
    if incoming:
        lines += ['**Incoming:**', '']
        for rel, source, meta in incoming:
            suffix = f' ({meta})' if meta else ''
            lines.append(f'- {node_ref(source, community_by_name)} -> `{rel}`{suffix}')
        lines.append('')
    return '\n'.join(lines)


def write_vault(name: str, graph_path: Path):
    nodes, edges = load_graph(graph_path)
    by_name = {}
    for n in nodes:
        nm = node_name(n)
        by_name[nm] = {
            'name': nm,
            'src': n.get('src', ''),
            'loc': n.get('loc', ''),
            'community': n.get('community', ''),
            'kind': n.get('kind', n.get('type', 'node')),
        }

    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for e in edges:
        src, dst, rel, meta = edge_endpoints(e)
        if src in by_name and dst in by_name:
            outgoing[src].append((rel, dst, meta))
            incoming[dst].append((rel, src, meta))

    vault_dir = VAULT_ROOT / name
    communities_dir = vault_dir / 'communities'
    os.makedirs(communities_dir, exist_ok=True)

    community_by_name = {nname: str(info['community']) for nname, info in by_name.items()}

    communities = defaultdict(list)
    sources = defaultdict(list)
    for nname, info in by_name.items():
        communities[str(info['community'])].append(nname)
        sources[str(info['src'])].append(nname)

    for comm, items in sorted(communities.items(), key=lambda x: x[0]):
        label = comm if comm != '' else 'no-community'
        file_slug = community_file_slug(comm)
        header = [
            '---',
            f'community: "{esc(comm)}"',
            f'node_count: {len(items)}',
            '---',
            '',
            f'# Community {label}',
            '',
            f'- Nodes: {len(items)}',
            '',
        ]
        sections = []
        for nname in sorted(items):
            info = by_name[nname]
            sections.append(
                render_node_section(
                    info,
                    outgoing.get(nname, []),
                    incoming.get(nname, []),
                    community_by_name,
                )
            )
        body = '\n'.join(header) + '\n'.join(sections)
        (communities_dir / f'{file_slug}.md').write_text(body.rstrip() + '\n', encoding='utf-8')

    index = {
        'meta': {
            'name': name,
            'source_graph': str(graph_path),
            'node_count': len(by_name),
            'edge_count': len(edges),
            'community_count': len(communities),
        },
        'nodes': {
            nname: {
                'kind': info['kind'],
                'src': info['src'],
                'loc': info['loc'],
                'community': str(info['community']),
                'community_file': f'communities/{community_file_slug(str(info["community"]))}.md',
                'block_id': slugify(nname),
                'out': [
                    {'rel': rel, 'target': target, 'meta': meta}
                    for rel, target, meta in outgoing.get(nname, [])
                ],
                'in': [
                    {'rel': rel, 'source': source, 'meta': meta}
                    for rel, source, meta in incoming.get(nname, [])
                ],
            }
            for nname, info in by_name.items()
        },
    }
    (vault_dir / 'index.json').write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding='utf-8',
    )

    readme = [
        f'# Graphify {name}',
        '',
        f'- Nodes: {len(by_name)}',
        f'- Edges: {len(edges)}',
        f'- Communities: {len(communities)}',
        f'- Source graph: `{graph_path}`',
        '',
        '## Quick links',
        '',
        '- [[communities]]',
        '- [[sources]]',
        '- `index.json` — machine-readable index for tooling',
        '',
    ]
    (vault_dir / 'README.md').write_text('\n'.join(readme) + '\n', encoding='utf-8')

    comm_lines = [f'# Communities ({name})', '']
    for comm, items in sorted(communities.items(), key=lambda x: x[0]):
        label = comm if comm != '' else 'no-community'
        file_slug = community_file_slug(comm)
        comm_lines += [
            f'## [[communities/{file_slug}|Community {label}]] ({len(items)} nodes)',
            '',
        ]
        for item in sorted(items)[:200]:
            comm_lines.append(f'- {node_ref(item, community_by_name)}')
        if len(items) > 200:
            comm_lines.append(f'- _…and {len(items) - 200} more_')
        comm_lines.append('')
    (vault_dir / 'communities.md').write_text('\n'.join(comm_lines), encoding='utf-8')

    src_lines = [f'# Sources ({name})', '']
    for src, items in sorted(sources.items(), key=lambda x: x[0]):
        title = src if src else '(no source)'
        src_lines += [f'## `{title}`', '']
        for item in sorted(items)[:200]:
            src_lines.append(f'- {node_ref(item, community_by_name)}')
        if len(items) > 200:
            src_lines.append(f'- _…and {len(items) - 200} more_')
        src_lines.append('')
    (vault_dir / 'sources.md').write_text('\n'.join(src_lines), encoding='utf-8')


def main():
    missing = [str(p) for p in TARGETS.values() if not p.exists()]
    if missing:
        print('Missing graph files:')
        for m in missing:
            print(' -', m)
        sys.exit(1)
    for name, path in TARGETS.items():
        write_vault(name, path)
    print(f'Vaults written to: {VAULT_ROOT}')


if __name__ == '__main__':
    main()
