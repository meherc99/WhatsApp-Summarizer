"""WhatsApp chat scraper and summarizer.

On-demand:  python main.py --chat "My Group" --msgs 100
Scheduled:  python main.py --chat "My Group" --msgs 100 --cron "0 9 * * 1-5"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import apify_scraper
import summarizer


def run_pipeline(chat_id: str, max_messages: int, output_dir: str | None) -> str:
    """Scrape and summarize one chat. Prints and optionally saves the result."""
    print(f"\n[pipeline] Starting for chat: {chat_id} (max {max_messages} messages)")

    messages = apify_scraper.scrape(chat_id, max_messages)
    if not messages:
        print(f"[pipeline] No messages returned — nothing to summarize.")
        return ""

    summary = summarizer.summarize(messages, group_name=chat_id)

    print("\n" + "=" * 60)
    print(summary)
    print("=" * 60 + "\n")

    if output_dir:
        _save_summary(summary, chat_id, output_dir)

    return summary


def _save_summary(summary: str, chat_id: str, output_dir: str) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in chat_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) / f"{safe_name}_{ts}.txt"
    out_path.write_text(summary, encoding="utf-8")
    print(f"[pipeline] Summary saved to {out_path}")


def _run_scheduled(chat_id: str, max_messages: int, cron_expr: str, output_dir: str) -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("Error: APScheduler is not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_pipeline,
        CronTrigger.from_crontab(cron_expr, timezone="UTC"),
        args=[chat_id, max_messages, output_dir],
        id="whatsapp_summary",
        name=f"Summarize {chat_id}",
        misfire_grace_time=300,  # allow up to 5-min late start
    )

    next_run = scheduler.get_jobs()[0].next_run_time
    print(f"[scheduler] Scheduled '{chat_id}' | cron: {cron_expr} | next run: {next_run}")
    print("[scheduler] Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)
        print("\n[scheduler] Stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape and summarize a WhatsApp chat via Apify.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--chat", "-c",
        required=True,
        help="Chat name or ID to scrape (passed to Apify actor as chatId)",
    )
    parser.add_argument(
        "--msgs", "-n",
        type=int,
        default=100,
        metavar="N",
        help="Max messages to fetch (default: 100)",
    )
    parser.add_argument(
        "--cron",
        metavar="EXPR",
        help="Cron expression for recurring runs (e.g. '0 9 * * 1-5' = weekdays at 9am UTC). "
             "Omit to run once and exit.",
    )
    parser.add_argument(
        "--output", "-o",
        default="summaries",
        metavar="DIR",
        help="Directory to write summary files (default: summaries/). Pass empty string to disable.",
    )

    args = parser.parse_args()
    output_dir = args.output if args.output else None

    if args.cron:
        _run_scheduled(args.chat, args.msgs, args.cron, output_dir)
    else:
        run_pipeline(args.chat, args.msgs, output_dir)


if __name__ == "__main__":
    main()
