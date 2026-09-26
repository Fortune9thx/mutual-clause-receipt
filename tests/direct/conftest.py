import os

# Windows-only: gltest's message-injection helper opens a temp file, dup2()s
# it onto stdin, then tries to unlink the original path while a handle is
# still open. That raises PermissionError on Windows (POSIX allows unlinking
# an open file). This does not affect contract behavior - it only affects
# whether the harness can clean up its own temp file - so we swallow it.
_original_unlink = os.unlink


def _patched_unlink(path, *args, **kwargs):
    try:
        _original_unlink(path, *args, **kwargs)
    except PermissionError:
        pass


os.unlink = _patched_unlink


# gltest's WASI mock eagerly json.loads()s any JSON-shaped mock_llm response
# before handing it back to the contract, regardless of the response_format
# the contract actually requested. gl.nondet.exec_prompt's real SDK
# implementation does its OWN json.loads() (for response_format="json") or
# expects a plain string (for the default "text" format) - either way it
# wants the raw text, not an already-parsed dict, and raises
# NondetException("... is not text"/"... is not a string") when handed one.
# Patch the mock to always return the registered response verbatim.
from gltest.direct import wasi_mock  # noqa: E402


def _patched_handle_llm_request(vm, data):
    prompt = data.get("prompt", "")
    response = vm._match_llm_mock(prompt)
    if response is not None:
        return {"ok": response}

    strict = getattr(vm, "_strict_mock_mode", False)
    if strict:
        registered = [p.pattern for p, _ in vm._llm_mocks]
        raise wasi_mock.MockNotFoundError(
            f"[strict] No LLM mock for prompt: {prompt[:100]}...\n"
            f"  Registered: {registered or '(none)'}"
        )

    live_handler = getattr(vm, "_live_llm_handler", None)
    if live_handler is not None:
        return live_handler(data)

    registered = [p.pattern for p, _ in vm._llm_mocks]
    raise wasi_mock.MockNotFoundError(
        f"No LLM mock for prompt: {prompt[:100]}...\n"
        f"  Registered: {registered or '(none)'}"
    )


wasi_mock._handle_llm_request = _patched_handle_llm_request
