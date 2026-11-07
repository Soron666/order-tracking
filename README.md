# Order Tracking

A food-delivery app tracks one order. Its status moves along:

```
Placed  ->  Cooking  ->  Out for delivery  ->  Delivered
```

Whenever the status changes, the order notifies the things that are watching
it — the customer's phone (an SMS) and the kitchen screen. Each one reports
the change in its own way.

This is the **Observer pattern**: the order is the *subject*, and everything
that wants to know about a status change is an *observer* (watcher).

---

## Required output

Running the demo prints exactly this:

```
Order is now: Cooking
SMS to Rahim: your order is now Cooking
Kitchen screen: Cooking
Order is now: Out for delivery
SMS to Rahim: your order is now Out for delivery
Kitchen screen: Out for delivery
Order is now: Delivered
SMS to Rahim: your order is now Delivered
```

Note the last block: **the kitchen is not notified when the order is
delivered.** That is handled in the code — see
[Why the kitchen is silent at the end](#why-the-kitchen-is-silent-at-the-end).

---

## Quick start

```bash
git clone https://github.com/Soron666/order-tracking.git
cd order-tracking

# Run the demo
python main.py

# Run the tests
python -m pip install -r requirements.txt
python -m pytest -v
```

No third-party runtime dependencies — the package is pure standard library.

Requirements: Python 3.9 or newer.

---

## The design

### The subject — `Order`

`order_tracking/order.py`

```python
order = Order(order_id="ORD-1001", status=OrderStatus.PLACED)
order.add_watcher(some_watcher)      # start watching
order.remove_watcher(some_watcher)   # stop watching
order.change_status(OrderStatus.COOKING)
```

`Order` holds the status and a list of watchers. That is all it does.

### The observer interface — `Watcher`

`order_tracking/watcher.py`

```python
class Watcher(abc.ABC):
    @abc.abstractmethod
    def update(self, order: "Order") -> None:
        """Called once per status change, for every watcher on the list."""
```

One method. Any object with a matching `update(order)` works — the order
never checks what type a watcher is.

### The observers

`order_tracking/watchers/sms.py` and `order_tracking/watchers/kitchen.py`

```python
class SmsNotifier(Watcher):
    def update(self, order):
        print(f"SMS to {self._recipient}: your order is now {order.status.value}")


class KitchenScreen(Watcher):
    def update(self, order):
        print(f"Kitchen screen: {order.status.value}")
        if order.status is OrderStatus.OUT_FOR_DELIVERY:
            order.remove_watcher(self)
```

---

## How each rule is satisfied

| # | Rule | Where it lives |
|---|------|----------------|
| 1 | An order class that holds the status | `Order._status` in `order_tracking/order.py` |
| 2 | The order must not mention phone or kitchen by name | `order.py` contains no reference to SMS, kitchen, phone or screen — only to the `Watcher` interface. A test enforces this. |
| 3 | A watcher can be added or removed at any time | `Order.add_watcher()` / `Order.remove_watcher()` |
| 4 | One status change tells every watcher on the list at that moment | `Order.change_status()` snapshots the list, then calls `update()` on each |
| 5 | The kitchen is not notified when the order is delivered | `KitchenScreen` removes itself once the food leaves the kitchen |

### Rule 2 in detail

The order file never names a reporting channel. It imports only `Watcher`:

```python
from .watcher import Watcher
```

A test reads the source of `order.py` and fails if the words *sms*,
*kitchen*, *phone*, *notifier* or *screen* appear in it
(`tests/test_order.py::test_order_does_not_mention_phone_or_kitchen`).

Because the order only knows the `Watcher` interface, any object with an
`update(order)` method can watch it — no inheritance required.

### Rule 4 in detail

`change_status()` takes a **snapshot** of the watcher list before it starts
telling anybody:

```python
with self._lock:
    self._status = new_status
    self._printer(f"Order is now: {new_status.value}")
    current_watchers = list(self._watchers)

for watcher in current_watchers:
    watcher.update(self)
```

This gives two useful guarantees:

* **The set notified is the set that was watching at the moment of the
  change.** A watcher that joins mid-notification is not told about the
  change already in progress (it hears the next one).
* **The broadcast never breaks.** A watcher is allowed to remove itself, or
  add another watcher, while it is being told — iterating a snapshot means
  the list cannot be mutated out from under the loop.

`threading.RLock` guards the list, so watch/unwatch from another thread
cannot corrupt it.

### Why the kitchen is silent at the end

The order is not allowed to know what a kitchen is, so it cannot special-case
"delivered means don't tell the kitchen". The kitchen handles it itself:

> The kitchen only cares about an order while the food is still in the
> kitchen. Once the order moves to **Out for delivery** the food has left, so
> the screen removes itself from the watch list.

By the time the order becomes **Delivered**, the kitchen screen is no longer
on the watch list, so it is simply not notified — the required output falls
out of the design instead of being hard-coded.

The customer SMS keeps watching until the end, so the customer still gets the
final "your order is now Delivered" message.

---

## Project layout

```
order-tracking/
├── main.py                        # entry point - prints the required output
├── expected_output.txt            # the exact output the assignment asks for
├── verify_against_pdf.py          # diffs the demo output against the assignment PDF
├── pyproject.toml
├── requirements.txt
├── order_tracking/
│   ├── __init__.py
│   ├── __main__.py                # python -m order_tracking
│   ├── demo.py                    # the demonstration scenario
│   ├── order.py                   # the subject
│   ├── status.py                  # OrderStatus enum
│   ├── watcher.py                 # the observer interface
│   └── watchers/
│       ├── __init__.py
│       ├── kitchen.py             # kitchen screen observer
│       └── sms.py                 # SMS observer
├── tests/
│   └── test_order.py
└── .github/workflows/tests.yml    # CI: runs pytest on Python 3.9 - 3.13
```

---

## Tests

```bash
python -m pytest -v
```

The suite covers:

* the order starts `Placed` and holds its status
* every watcher is told exactly once per change
* a watcher added later only hears later changes
* a removed watcher stops receiving updates
* adding the same watcher twice notifies it once
* removing an unknown watcher is harmless
* a watcher may remove **itself** while being notified
* a watcher may **add** another watcher while being notified
* the order source contains no reference to phone/kitchen (rule 2)
* the order accepts any duck-typed object with `update()`
* the demo output matches the required output **character for character**
* the kitchen is not notified when the order is delivered

CI runs the suite on Python 3.9, 3.10, 3.11, 3.12, 3.13 and 3.14, and also diffs
the demo output against `expected_output.txt`.

---

## Checking against the assignment PDF

`verify_against_pdf.py` extracts the **Required Output** block straight out of
the assignment PDF, runs the demo, and compares the two — plus it re-checks
each numbered rule against the code.

```bash
pip install -r requirements.txt
python verify_against_pdf.py                          # auto-detects the PDF
python verify_against_pdf.py path/to/assignment.pdf   # or point at it
```

```
RESULT: EXACT MATCH (line for line, character for character)
[Rule 1] Order class holds the status ............... PASS
[Rule 2] Order names no phone/kitchen ............... PASS
[Rule 3] Watcher added/removed any time ............. PASS
[Rule 4] One change -> every watcher once ........... PASS
[Note]  Kitchen not notified on Delivered .......... PASS
[Note]  Kitchen removed itself from list ........... PASS
[Note]  SMS still notified on Delivered ........... PASS
OVERALL: ALL CHECKS PASSED
```

If the PDF is not on the machine, the script still runs the rule checks and
tells you how to point it at the file.

---

## License

MIT
