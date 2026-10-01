from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import DEFAULT_AS_OF, run_query, verify_trace
from .evaluation import save_report


def main() -> None:
    parser = argparse.ArgumentParser(description='Evidence Desk • offline synthetic due-diligence prototype')
    sub = parser.add_subparsers(dest='command', required=True)
    ask = sub.add_parser('ask', help='Run the deterministic local evidence pipeline')
    ask.add_argument('--entity', default='Atlas Reserve')
    ask.add_argument('--question', default='What is the reserve coverage ratio?')
    ask.add_argument('--as-of', default=DEFAULT_AS_OF)
    ask.add_argument('--output', type=Path)
    evaluation = sub.add_parser('evaluate', help='Replay the synthetic ablation benchmark')
    evaluation.add_argument('--output', type=Path, default=Path('artifacts'))
    serve = sub.add_parser('serve', help='Start a loopback-only demo, not a production server')
    serve.add_argument('--port', type=int, default=8765)
    verify = sub.add_parser('verify-trace', help='Check an exported trace for accidental modification')
    verify.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'ask':
            result = run_query(args.entity, args.question, as_of=args.as_of)
            text = json.dumps(result, indent=2)+'\n'
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text)
            print(text, end='')
        elif args.command == 'evaluate':
            result = save_report(args.output)
            print(json.dumps({k: result[k] for k in ['dataset', 'baseline', 'checked', 'limitations']}, indent=2))
        elif args.command == 'verify-trace':
            data = json.loads(args.file.read_text())
            valid = verify_trace(data['trace'] if isinstance(data, dict) else data)
            print('Trace chain valid' if valid else 'Trace chain INVALID')
            raise SystemExit(0 if valid else 1)
        elif args.command == 'serve':
            from .server import serve_local
            serve_local(args.port)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
