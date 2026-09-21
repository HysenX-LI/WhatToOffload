"""Publish synthetic measurements and frozen candidates; retain raw logs locally."""
import hashlib
import json
import shutil
from pathlib import Path


def export_run(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('metadata.json', 'plan.json', 'attempts.jsonl', 'report.json', 'report.md', 'comparison.svg'):
        if (source / name).is_file(): shutil.copyfile(source / name, destination / name)
    if (source / 'builds').exists(): shutil.copytree(source / 'builds', destination / 'builds')
    events = []
    target = destination / 'calls'
    target.mkdir()
    for path in sorted((source / 'calls').glob('call-*.events.jsonl')):
        raw = path.read_bytes()
        entry = {'file': path.name, 'raw_sha256': hashlib.sha256(raw).hexdigest(), 'events': []}
        for line in raw.splitlines():
            try: event = json.loads(line)
            except ValueError: continue
            # Public audit includes reported usage and tool identity/outcome but not host paths/transcript.
            item = event.get('item', {})
            kept = {'type': event.get('type')}
            if 'usage' in event: kept['usage'] = event['usage']
            if item:
                kept['item'] = {k: item[k] for k in ('id', 'type', 'status', 'exit_code') if k in item}
            entry['events'].append(kept)
        events.append(entry)
    for path in (source / 'calls').glob('*.metrics.json'): shutil.copyfile(path, target / path.name)
    (target / 'event-audit.json').write_text(json.dumps(events, indent=2) + '\n')
    (destination / 'EXPORT.md').write_text(
        'Synthetic inputs/results and candidate sources are public. Full request/response/tool transcripts remain in the local run directory.\n'
        'calls/event-audit.json preserves event types, item IDs, outcomes, reported usage and SHA-256 of each original raw JSONL.\n'
        'No experimental outcomes are removed from attempts or reports. No credentials or private long-task material is included.\n')
