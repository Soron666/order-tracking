"""Verify the implementation against the assignment PDF itself.

Extracts the 'Required Output' block straight out of the PDF, runs the demo,
and compares. Also checks each numbered rule in the PDF against the code.

Usage:
    python verify_against_pdf.py [path-to-assignment.pdf]

If no PDF is given, the script looks at the ASSIGNMENT_PDF environment
variable, then at a couple of common local locations. If it cannot find the
PDF it still runs the rule checks and explains what to do.
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parent

sys.path.insert(0, str(REPO))

from order_tracking import Order, OrderStatus, SmsNotifier, Watcher  # noqa: E402
from order_tracking.demo import main  # noqa: E402
from order_tracking.watchers.kitchen import KitchenScreen  # noqa: E402

CANDIDATE_PDFS = [
    Path.home()
    / ".minimax"
    / "v2"
    / "assets"
    / "2026"
    / "11"
    / "07"
    / "13-18-41-357-asset_20261107-131841-357_163e07e039ff_94794a0b-SWE_Assignment-02.pdf",
    REPO / "SWE_Assignment-02.pdf",
]


def find_pdf() -> Path | None:
    """Locate the assignment PDF, if it is available on this machine."""
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        return candidate if candidate.exists() else None

    env = os.environ.get("ASSIGNMENT_PDF")
    if env and Path(env).exists():
        return Path(env)

    for candidate in CANDIDATE_PDFS:
        if candidate.exists():
            return candidate
    return None


def pdf_text(pdf: Path) -> str:
    reader = PdfReader(str(pdf))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def pdf_stream(text: str) -> str:
    """The PDF's text as one whitespace-normalised stream.

    This PDF stores every word on its own line, so the extracted lines are
    joined into a single stream before searching for the output block.
    """
    return " ".join(ln.strip() for ln in text.splitlines() if ln.strip())


def expected_from_pdf(text: str) -> list[str]:
    """Pull the required-output lines out of the PDF.

    The PDF block runs from 'Order is now: Cooking' to the last
    'SMS to Rahim: ... Delivered' line.
    """
    # The PDF breaks the block across separate lines; rebuild the lines by
    # splitting on the known message starts.
    stream = " ".join(ln.strip() for ln in text.splitlines() if ln.strip())

    markers = [
        "Order is now:",
        "SMS to Rahim:",
        "Kitchen screen:",
    ]

    # Find every occurrence of a marker and slice the text that follows it.
    hits = []
    for marker in markers:
        start = 0
        while True:
            idx = stream.find(marker, start)
            if idx == -1:
                break
            hits.append(idx)
            start = idx + len(marker)

    if not hits:
        raise AssertionError("Could not find the required-output block in the PDF")

    hits.sort()

    out: list[str] = []
    for pos in hits:
        end = min(
            (h for h in hits if h > pos),
            default=len(stream),
        )
        chunk = stream[pos:end].strip()
        # Stop the chunk at the end of its own message.
        chunk = chunk.split("Notice that")[0].strip()
        if chunk:
            out.append(chunk)

    if not out:
        raise AssertionError("Could not find the required-output block in the PDF")
    return out


def actual_output() -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    return buf.getvalue()


def main_check() -> int:
    failures = []
    pdf = find_pdf()

    print("=" * 68)
    print("1. REQUIRED OUTPUT: PDF vs ACTUAL PROGRAM OUTPUT")
    print("=" * 68)

    if pdf is None:
        print(
            "\nThe assignment PDF was not found on this machine, so the output\n"
            "could not be diffed against it automatically.\n\n"
            "The expected output is stored in 'expected_output.txt' and is\n"
            "checked by the test suite and by CI on every push.\n\n"
            "To check against the PDF, run:\n"
            "    python verify_against_pdf.py <path-to-SWE_Assignment-02.pdf>"
        )
    else:
        print(f"\nPDF: {pdf}\n")
        text = pdf_text(pdf)
        expected = expected_from_pdf(text)
        actual = [ln for ln in actual_output().splitlines() if ln.strip()]

        print("--- extracted from PDF ---")
        for ln in expected:
            print(repr(ln))
        print("\n--- produced by program ---")
        for ln in actual:
            print(repr(ln))

        if expected == actual:
            print("\nRESULT: EXACT MATCH (line for line, character for character)")
        else:
            print("\nRESULT: MISMATCH")
            import difflib

            for d in difflib.unified_diff(expected, actual, "pdf", "program", lineterm=""):
                print(d)
            failures.append("required-output")

    # ------------------------------------------------------------------
    print("\n" + "=" * 68)
    print("2. RULES CHECKED AGAINST THE PDF TEXT")
    print("=" * 68)

    # Rule 1 - an order class holding the status
    o = Order()
    o.change_status(OrderStatus.COOKING)
    ok1 = o.status is OrderStatus.COOKING
    print(f"\n[Rule 1] Order class holds the status ............... {'PASS' if ok1 else 'FAIL'}")
    if not ok1:
        failures.append("rule 1")

    # Rule 2 - order must not mention phone/kitchen by name
    src = (REPO / "order_tracking" / "order.py").read_text(encoding="utf-8").lower()
    hits = [w for w in ("sms", "kitchen", "phone", "notifier", "screen") if w in src]
    ok2 = not hits
    print(f"[Rule 2] Order names no phone/kitchen ............... {'PASS' if ok2 else 'FAIL ' + str(hits)}")
    if not ok2:
        failures.append("rule 2")

    # Rule 3 - watchers can be added/removed at any time
    o = Order()
    w = SmsNotifier(recipient="X", printer=lambda _m: None)
    o.add_watcher(w)
    added = w in o.watchers
    o.remove_watcher(w)
    removed = w not in o.watchers
    ok3 = added and removed
    print(f"[Rule 3] Watcher added/removed any time ............. {'PASS' if ok3 else 'FAIL'}")
    if not ok3:
        failures.append("rule 3")

    # Rule 4 - one change tells every watcher on the list at that moment
    o = Order()
    seen_a, seen_b = [], []

    class Rec(Watcher):
        def __init__(self, sink):
            self.sink = sink

        def update(self, order):
            self.sink.append(order.status)

    a, b = Rec(seen_a), Rec(seen_b)
    o.add_watcher(a)
    o.add_watcher(b)
    o.change_status(OrderStatus.COOKING)
    ok4 = seen_a == [OrderStatus.COOKING] and seen_b == [OrderStatus.COOKING]
    print(f"[Rule 4] One change -> every watcher once ........... {'PASS' if ok4 else 'FAIL'}")
    if not ok4:
        failures.append("rule 4")

    # Special note - kitchen not notified when delivered.
    # This must use the REAL KitchenScreen: a generic spy watcher does not
    # implement the kitchen's "food has left, stop watching" behaviour, so
    # it would (correctly) keep hearing about every later change.
    o = Order()
    kitchen_calls = []

    class SpyKitchen(KitchenScreen):
        def update(self, order):
            kitchen_calls.append(order.status)
            super().update(order)

    spy = SpyKitchen(printer=lambda _m: None)
    o.add_watcher(spy)
    o.change_status(OrderStatus.COOKING)
    o.change_status(OrderStatus.OUT_FOR_DELIVERY)
    o.change_status(OrderStatus.DELIVERED)
    ok5 = OrderStatus.DELIVERED not in kitchen_calls
    print(f"[Note]  Kitchen not notified on Delivered .......... {'PASS' if ok5 else 'FAIL'}")
    if not ok5:
        failures.append("kitchen-not-notified")

    # ...and the reason it is silent: it left the watch list when the food
    # went out for delivery.
    o = Order()
    k = KitchenScreen(printer=lambda _m: None)
    o.add_watcher(k)
    o.change_status(OrderStatus.OUT_FOR_DELIVERY)
    left = k not in o.watchers
    print(f"[Note]  Kitchen removed itself from list ........... {'PASS' if left else 'FAIL'}")
    if not left:
        failures.append("kitchen-removes-self")

    # The SMS watcher must keep watching to the very end.
    o = Order()
    sms_calls = []

    class SpySms(SmsNotifier):
        def update(self, order):
            sms_calls.append(order.status)
            super().update(order)

    s = SpySms(recipient="Rahim", printer=lambda _m: None)
    o.add_watcher(s)
    o.change_status(OrderStatus.COOKING)
    o.change_status(OrderStatus.OUT_FOR_DELIVERY)
    o.change_status(OrderStatus.DELIVERED)
    ok_sms = OrderStatus.DELIVERED in sms_calls
    print(f"[Note]  SMS still notified on Delivered ........... {'PASS' if ok_sms else 'FAIL'}")
    if not ok_sms:
        failures.append("sms-still-notified")

    # The PDF's status vocabulary
    print("\n" + "=" * 68)
    print("3. STATUS NAMES IN THE PDF vs THE ENUM")
    print("=" * 68)
    if pdf is None:
        for label, enum_value in [
            ("Placed", OrderStatus.PLACED.value),
            ("Cooking", OrderStatus.COOKING.value),
            ("Out for delivery", OrderStatus.OUT_FOR_DELIVERY.value),
            ("Delivered", OrderStatus.DELIVERED.value),
        ]:
            print(f"  {label:<18} enum={enum_value!r:<20} (PDF not available)")
    else:
        pdf_lower = pdf_stream(pdf_text(pdf)).lower()
        for label, enum_value in [
            ("Placed", OrderStatus.PLACED.value),
            ("Cooking", OrderStatus.COOKING.value),
            ("Out for delivery", OrderStatus.OUT_FOR_DELIVERY.value),
            ("Delivered", OrderStatus.DELIVERED.value),
        ]:
            in_pdf = label.lower() in pdf_lower
            matches = label == enum_value
            flag = "OK" if matches and in_pdf else "CHECK"
            print(f"  {label:<18} enum={enum_value!r:<20} in PDF={in_pdf}  {flag}")

    print("\n" + "=" * 68)
    if failures:
        print(f"OVERALL: {len(failures)} FAILURE(S): {failures}")
        return 1
    print("OVERALL: ALL CHECKS PASSED")
    print("=" * 68)
    return 0

    print("\n" + "=" * 68)
    if failures:
        print(f"OVERALL: {len(failures)} FAILURE(S): {failures}")
        return 1
    print("OVERALL: ALL CHECKS PASSED")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_check())
