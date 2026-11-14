"""Best-effort exception diagnostics, independent of scientific/ownership state."""


def add_failure_note(original: BaseException, context: str, secondary: BaseException) -> None:
    """Preserve the primary failure if its optional diagnostic note cannot be added.

    Python 3.10 has no exception-note API. A subclass may also disable or override
    it. Note lookup, formatting and ordinary reporting errors must not mask the
    primary exception. A new BaseException interruption still propagates.
    This helper writes no artifact and grants no success or recovery authority.
    """
    try:
        add_note = getattr(original, "add_note", None)
        if callable(add_note):
            add_note(f"{context}: {secondary}")
    except Exception:
        pass
