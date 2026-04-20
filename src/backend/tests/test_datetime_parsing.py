"""
Datetime Parsing Library Comparison Script

Compares 3 datetime parsing libraries on diverse test cases:
- dateparser
- dateutil.parser
- parsedatetime

Run from backend directory:
    cd src/backend
    python tests/test_datetime_parsing.py

Results are saved to: logs/datetime_parsing_comparison.json
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dateparser
from dateutil import parser as dateutil_parser

try:
    import parsedatetime

    PARSEDATETIME_AVAILABLE = True
except ImportError:
    PARSEDATETIME_AVAILABLE = False

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)

test_cases = [
    # ============= RELATIVE DATES =============
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
    "tomorrow",
    "yesterday",
    "in 3 days",
    "in 5 days",
    "in a week",
    "next week",
    "last week",
    "day after tomorrow",
    # ============= RELATIVE WITH TIME =============
    "next monday at 09:00",
    "next friday at 17:00",
    "tomorrow morning",
    "next tuesday at 6am",
    "next saturday at 10:00",
    "monday 6am",
    "friday 5pm",
    "next week monday 10:00",
    "tomorrow afternoon",
    "next week friday evening",
    # ============= ABSOLUTE DATES =============
    "2026-04-20",
    "2026-04-25",
    "2026-05-01",
    "April 20, 2026",
    "April 25 2026",
    "20/04/2026",
    "25/04/2026",
    "04/20/2026",
    "05/01/2026",
    "20 April 2026",
    # ============= WITH TIME =============
    "2026-04-20 09:00",
    "2026-04-25 17:00",
    "April 20 2026 09:00",
    "April 25 2026 at 17:00",
    # ============= INFORMAL =============
    "today",
    "now",
    "end of week",
    "first thing monday",
    "in the morning",
    "later today",
    "first thing in the morning",
    "end of the day",
    "midday",
    "midnight",
    # ============= FORMAL =============
    "this monday",
    "this friday",
    "this week",
    "next month",
    "next quarter",
    "first day of next month",
    "last day of month",
    "first monday of next month",
    # ============= EDGE CASES =============
    "soon",
    "later",
    "asap",
    "whenever",
    "ometime",
    "eventually",
    "quickly",
    "immediately",
    # ============= COMPLEX COMBINATIONS =============
    "next monday morning",
    "next friday afternoon",
    "tomorrow evening",
    "day after tomorrow morning",
    "next week monday at 09:00",
    "first thing next week",
    "beginning of next month",
    "end of next week",
    # ============= SHORT FORMS =============
    "mon",
    "tue",
    "wed",
    "thu",
    "fri",
    "sat",
    "sun",
    "tmr",
    "tmrw",
    "2moro",
    "2mrw",
    # ============= INTERNATIONAL STYLE =============
    "20.04.2026",
    "25.04.2026",
    "20-04-2026",
    "2026/04/20",
    # ============= TIMEZONE INFO =============
    "2026-04-20 UTC",
    "2026-04-20 EST",
    "next monday UTC",
    # ============= HOLIDAYS/EVENTS =============
    "easter 2026",
    "christmas",
    "new year",
    "end of year",
    "start of month",
    # ============= MORE COMPLEX =============
    "monday next week",
    "friday end of week",
    "tomorrow first thing",
    "in two days",
    "in four days",
    "next week monday morning",
    "day after tomorrow afternoon",
    "next month first",
    "last week of month",
    # ============= ERRORS/EDGE =============
    "never",
    "sometimes",
    "maybe",
    "",
    "N/A",
    "TBD",
    "TBC",
    "date not set",
    "no date",
    "unknown",
]


def try_parsedatetime(value):
    """Try parsedatetime library."""
    if not PARSEDATETIME_AVAILABLE:
        return None, "NOT_INSTALLED"
    try:
        cal = parsedatetime.Calendar()
        result = cal.parse(value)
        if result[0]:
            dt = datetime(*result[0][:6])
            return dt, "OK"
        return None, "FAILED"
    except Exception as e:
        return None, f"ERROR: {e}"


def try_dateparser(value):
    """Try dateparser library."""
    try:
        result = dateparser.parse(value)
        if result:
            return result, "OK"
        return None, "FAILED"
    except Exception as e:
        return None, f"ERROR: {e}"


def try_dateutil(value):
    """Try dateutil.parser library."""
    try:
        result = dateutil_parser.parse(value)
        if result:
            return result, "OK"
        return None, "FAILED"
    except Exception as e:
        return None, f"ERROR: {e}"


def main():
    print("=" * 70)
    print("DATETIME PARSING LIBRARY COMPARISON")
    print("=" * 70)
    print(f"\nTotal test cases: {len(test_cases)}")

    results = []

    for i, test_input in enumerate(test_cases, 1):
        result = {
            "test_number": i,
            "input": test_input,
        }

        # Parse with each library
        dateparser_result, dateparser_status = try_dateparser(test_input)
        dateutil_result, dateutil_status = try_dateutil(test_input)
        parsedatetime_result, parsedatetime_status = try_parsedatetime(test_input)

        # Store results
        result["dateparser"] = {
            "status": dateparser_status,
            "datetime": dateparser_result.isoformat() if dateparser_result else None,
        }
        result["dateutil"] = {
            "status": dateutil_status,
            "datetime": dateutil_result.isoformat() if dateutil_result else None,
        }
        result["parsedatetime"] = {
            "status": parsedatetime_status,
            "datetime": parsedatetime_result.isoformat()
            if parsedatetime_result
            else None,
        }

        results.append(result)

        status_indicator = []
        if dateparser_status == "OK":
            status_indicator.append("P")
        if dateutil_status == "OK":
            status_indicator.append("D")
        if parsedatetime_status == "OK":
            status_indicator.append("X")

        indicator_str = "[" + "".join(status_indicator) + "]"

        print(f"{i:3}. {indicator_str:6} {test_input}")

    # Save results to JSON
    os.makedirs(LOG_DIR, exist_ok=True)
    output_file = os.path.join(LOG_DIR, "datetime_parsing_comparison.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_date": datetime.now().isoformat(),
                "test_count": len(test_cases),
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n{'=' * 70}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 70}")

    # Summary
    print("\n--- SUMMARY ---")
    ok_count = {"dateparser": 0, "dateutil": 0, "parsedatetime": 0}
    for r in results:
        for key in ["dateparser", "dateutil", "parsedatetime"]:
            if r[key]["status"] == "OK":
                ok_count[key] += 1

    print(
        f"  dateparser:     {ok_count['dateparser']:3}/{len(test_cases)} OK ({ok_count['dateparser'] / len(test_cases) * 100:.1f}%)"
    )
    print(
        f"  dateutil:       {ok_count['dateutil']:3}/{len(test_cases)} OK ({ok_count['dateutil'] / len(test_cases) * 100:.1f}%)"
    )
    print(
        f"  parsedatetime:  {ok_count['parsedatetime']:3}/{len(test_cases)} OK ({ok_count['parsedatetime'] / len(test_cases) * 100:.1f}%)"
    )


if __name__ == "__main__":
    main()
