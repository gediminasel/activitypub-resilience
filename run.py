import asyncio
import logging
import os
import sys
from argparse import ArgumentParser
from typing import Union

sys.path.append("src")
from runners import LookupRunner, VerifierRunner  # noqa: E402
from workarounds import run_in_event_loop_windows_workaround  # noqa: E402


def simple_run(run, cleanup):
    async def run_with_cleanup():
        try:
            await run()
        finally:
            await cleanup()

    asyncio.run(run_with_cleanup())


if os.name == "nt":
    simple_run = run_in_event_loop_windows_workaround  # noqa: F811

if __name__ == "__main__":
    parser = ArgumentParser(description="Run lookup server or verifier")
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument("-v", action="store_true", help="display info logs")
    log_group.add_argument("-vv", action="store_true", help="display debug logs")
    subparsers = parser.add_subparsers(
        title="service", help="which service to run", dest="service", required=True
    )

    lookup_parser = subparsers.add_parser("lookup", help="Run lookup server")
    lookup_start_group = lookup_parser.add_mutually_exclusive_group()
    lookup_parser.add_argument(
        "--from",
        dest="crawl_from",
        metavar="URI",
        default=[],
        action="append",
        help="Resource from which to start crawling",
    )
    lookup_parser.add_argument(
        "--add-ver",
        dest="verifiers",
        metavar="URI",
        default=[],
        action="append",
        help="Add verifier to trusted list",
    )
    lookup_start_group.add_argument(
        "--no-crawl", dest="crawl", action="store_false", help="Don't start the crawler"
    )
    lookup_start_group.add_argument(
        "--no-server",
        dest="server",
        action="store_false",
        help="Don't start web server",
    )

    verifier_parser = subparsers.add_parser("verifier", help="Run verifier")
    verifier_parser.add_argument(
        "--watch",
        dest="lookups",
        metavar="URI",
        default=[],
        action="append",
        help="URI of a lookup server",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.vv else logging.INFO if args.v else None

    runner: Union[VerifierRunner, LookupRunner]
    if args.service == "lookup":
        if not args.crawl and not args.server and not args.verifiers:
            print("Nothing to do: start crawler and/or server or add verifier")
            exit(1)
        runner: LookupRunner = LookupRunner(log_level)

        async def run_with_args():
            if args.verifiers:
                for v in args.verifiers:
                    vid, uri = await runner.add_verifier(v)
                    print(f"added verifier {uri} with id {vid}")
                return
            await runner.start(args.crawl_from if args.crawl else None, args.server)
            await runner.spin_and_log()

    elif args.service == "verifier":
        if not args.lookups:
            print("Nothing to do: give a lookup server to watch")
            exit(1)

        runner = VerifierRunner(log_level)

        async def run_with_args():
            await runner.start(args.lookups)
            await runner.spin_and_log()

    else:
        raise NotImplementedError()

    simple_run(run_with_args, runner.cleanup)
