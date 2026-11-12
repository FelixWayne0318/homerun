"""Resolve Polymarket hostnames to verified public IPs.

Clash Verge's TUN + fake-ip layer answers DNS with 198.18.x.x addresses
before the kernel config can apply a fake-ip filter.  The fake addresses
are intermittent: some Polymarket endpoints work while others time out
against the same host.  Pinning the verified IPs here keeps every backend
process (API and workers) on the same working route without requiring
system-wide DNS or /etc/hosts changes.

TLS SNI and the HTTP Host header still use the original hostname; only
the socket's destination address is replaced.
"""

from __future__ import annotations

import socket

_POLYMARKET_HOST_IPS: dict[str, str] = {
    "clob.polymarket.com": "172.64.153.51",
    "data-api.polymarket.com": "172.64.153.51",
    "polymarket.com": "172.64.153.51",
    "gamma-api.polymarket.com": "54.239.180.50",
}


def _pinned_host(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="ignore")
    if isinstance(host, str):
        return _POLYMARKET_HOST_IPS.get(host, host)
    return host


def install_polymarket_dns_override() -> None:
    current = socket.getaddrinfo
    if not getattr(current, "_polymarket_override", False):
        original = current

        def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            return original(_pinned_host(host), port, family, type, proto, flags)

        _getaddrinfo._polymarket_override = True
        socket.getaddrinfo = _getaddrinfo

    # httpx resolves through anyio's async backend, which does not call the
    # patched socket.getaddrinfo on every platform.  Patch the anyio entry
    # point as well so worker-side requests use the verified destination IP.
    try:
        from anyio._core import _sockets as anyio_sockets

        current_anyio = anyio_sockets.getaddrinfo
        if not getattr(current_anyio, "_polymarket_override", False):
            original_anyio = current_anyio

            async def _anyio_getaddrinfo(host, port, **kwargs):
                return await original_anyio(_pinned_host(host), port, **kwargs)

            _anyio_getaddrinfo._polymarket_override = True
            anyio_sockets.getaddrinfo = _anyio_getaddrinfo
    except Exception:
        pass
