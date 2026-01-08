#!/usr/bin/env python3
"""
Translation Agent System - Main Entry Point

A translation system using Claude API with:
- English to Chinese translation
- URL content fetching
- Notion integration
- Multiple domain support (tech, business, academic)

Usage:
    python main.py [--host HOST] [--port PORT] [--debug]

Environment Variables:
    ANTHROPIC_API_KEY: Required. Claude API key.
    NOTION_API_KEY: Optional. Notion integration token.
    NOTION_PARENT_PAGE_ID: Optional. Parent page for translations.
    ACCESS_KEYS: Optional. Comma-separated API access keys.
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv


def main():
    """Main entry point."""
    # Load environment variables from .env file
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Translation Agent System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='Host to bind to (default: from config or 0.0.0.0)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Port to bind to (default: from config or 5000)',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check configuration and exit',
    )

    args = parser.parse_args()

    # Load configuration
    from config.settings import load_config, validate_config

    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Check mode - validate and exit
    if args.check:
        errors = validate_config(config)
        if errors:
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        else:
            print("Configuration is valid!")
            print(f"  Model: {config.agent.model}")
            print(f"  Server: {config.server.host}:{config.server.port}")
            print(f"  Domains: {', '.join(config.translation.domains.keys())}")
            print(f"  Notion: {'Configured' if config.notion.api_key else 'Not configured'}")
            sys.exit(0)

    # Validate configuration
    errors = validate_config(config)
    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("\nRun with --check to validate configuration.", file=sys.stderr)
        sys.exit(1)

    # Create and run the application
    from backend.app import create_app

    app = create_app(config)

    # Determine host and port
    host = args.host or config.server.host
    port = args.port or config.server.port
    debug = args.debug or config.server.debug

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║          Translation Agent System v1.0.0                  ║
╠═══════════════════════════════════════════════════════════╣
║  Server:  http://{host}:{port:<5}                            ║
║  Model:   {config.agent.model:<42} ║
║  Debug:   {str(debug):<42} ║
╠═══════════════════════════════════════════════════════════╣
║  Endpoints:                                               ║
║    GET  /api/health          - Health check               ║
║    POST /api/translate       - Sync translation           ║
║    POST /api/translate/stream - Stream translation        ║
║    GET  /api/translate/resume/<id> - Resume/progress      ║
║    POST /api/notion/sync     - Sync to Notion             ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Run the server
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True,
    )


if __name__ == '__main__':
    main()
