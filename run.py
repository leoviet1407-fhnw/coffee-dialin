"""Run the PHIN Dial-in API: python run.py [--host 0.0.0.0] [--port 8000] [--reload]"""
import argparse
import os
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1",
                        help="Use 0.0.0.0 inside Codespaces or a container; the default is local-only.")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    folder = Path(__file__).resolve().parent / "backend"
    os.chdir(folder)
    sys.path.insert(0, str(folder))
    import uvicorn
    print(f"PHIN Dial-in API: http://{args.host}:{args.port}/docs", flush=True)
    uvicorn.run("main:app", host=args.host, port=args.port,
                reload=args.reload, reload_dirs=[str(folder)] if args.reload else None)

if __name__ == "__main__":
    main()
