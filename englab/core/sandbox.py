"""Esecuzione dei calcoli in un processo separato con limite di tempo.

SymPy può impiegare minuti (o non terminare) su alcuni input: su un sito
pubblico ogni calcolo gira in un processo figlio che viene ucciso allo scadere.
"""

from __future__ import annotations

import contextlib
import multiprocessing as mp
import os
import signal
import threading
from typing import Any, Callable

from .parsing import ParseError

DEFAULT_TIMEOUT = float(os.environ.get("ENGLAB_TIMEOUT", "10"))

_ctx = mp.get_context("forkserver")
# Precarica SymPy nel forkserver: ogni figlio parte già con i moduli in memoria.
_ctx.set_forkserver_preload([
    "sympy", "numpy",
    "englab.modules.analisi", "englab.modules.algebra",
    "englab.modules.numerico", "englab.modules.chimica", "englab.tools",
])


class ComputationTimeout(RuntimeError):
    pass


def _child(conn, fn, args, kwargs):
    try:
        conn.send(("ok", fn(*args, **kwargs)))
    except ParseError as exc:
        conn.send(("input", str(exc)))
    except Exception as exc:  # qualsiasi errore di calcolo
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()


def run(fn: Callable[..., Any], *args: Any, timeout: float = DEFAULT_TIMEOUT, **kwargs: Any) -> Any:
    """Esegue fn(*args) in un processo isolato; solleva ComputationTimeout se sfora."""
    parent, child = _ctx.Pipe(duplex=False)
    proc = _ctx.Process(target=_child, args=(child, fn, args, kwargs), daemon=True)
    proc.start()
    child.close()
    try:
        if not parent.poll(timeout):
            raise ComputationTimeout(
                "Il calcolo ha richiesto troppo tempo. Prova a semplificare l'espressione."
            )
        status, payload = parent.recv()
    except EOFError:
        raise RuntimeError("Il calcolo si è interrotto inaspettatamente.") from None
    finally:
        parent.close()
        if proc.is_alive():
            proc.kill()
        proc.join(1)
    if status == "ok":
        return payload
    if status == "input":
        raise ParseError(payload)
    raise RuntimeError(payload)


class _SoftTimeout(Exception):
    pass


@contextlib.contextmanager
def soft_limit(seconds: float):
    """Interrompe un blocco facoltativo (es. soluzione esatta) dopo `seconds`.

    Funziona solo nel thread principale (dove gira il processo sandbox); altrove
    non fa nulla. L'eccezione viene assorbita: il chiamante controlla il risultato.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _handler(signum, frame):
        raise _SoftTimeout()

    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except _SoftTimeout:
        pass
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
