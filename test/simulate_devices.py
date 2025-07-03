import asyncio
from rich.console import Console
from rich.table import Table
from rich import print
import test_cases

console = Console()
test_results = []

TESTS = [
    ("Server Availability", test_cases.check_server),
    ("Register Devices", test_cases.register_devices),
    ("Post Heart Rate", test_cases.post_heart_rate),
    ("Post Blood Pressure", test_cases.post_blood_pressure),
    ("Post Invalid Patient (403)", test_cases.post_invalid_patient),
    ("Get Heart Rate Readings", test_cases.get_heart_rate),
    ("Get Blood Pressure Readings", test_cases.get_blood_pressure),
    ("Test Concurrent Ingestion", test_cases.concurrent_ingestion),
    ("Test Invalid token (401)", test_cases.invalid_token_test),
    ("Test DB access time", test_cases.db_timing_test),
    ("Insert Known HeartRate", test_cases.insert_known_hr_values),
    ("Insert Known BloodPressure", test_cases.insert_known_bp_values),
    ("Validate HR Aggregates", test_cases.validate_hr_aggregates),
    ("Validate BP Aggregates", test_cases.validate_bp_aggregates),
]

async def run_tests():
    for name, test_fn in TESTS:
        try:
            console.print(f"▶ [cyan]{name}[/cyan]")
            ok = await test_fn()
            if ok is False:
                raise AssertionError("Returned False")
            test_results.append((name, "✅"))
        except Exception as e:
            console.print(f"❌ [red]{name} failed:[/red] {e}")
            test_results.append((name, "❌"))
        await asyncio.sleep(0.3)

    print("[bold underline]Test Summary[/bold underline]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test Case")
    table.add_column("Result")
    for name, status in test_results:
        table.add_row(name, status)
    console.print(table)

    passed = sum(1 for _, status in test_results if status == "✅")
    failed = len(test_results) - passed
    console.print(f"[bold green]PASSED: {passed}[/bold green] / [bold red]FAILED: {failed}[/bold red]")

if __name__ == "__main__":
    asyncio.run(run_tests())