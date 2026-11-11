import ipaddress
from flask import current_app


def client_ip(req):
    """The address of the client that made the request.

    Behind a reverse proxy or a load balancer ``remote_addr`` is the address of the proxy, so every client would look
    the same (and share one rate limit). When CLIENT_IP_HEADER names a header that the proxy sets, its address is used
    instead:

    * X-Real-IP: nginx (``proxy_set_header X-Real-IP $remote_addr``, it replaces what the client sent) and
      PythonAnywhere, whose load balancer puts the real address there.
    * X-Forwarded-For: the proxy appends the address it received the request from, so the last entry is the only one
      a client cannot choose.

    Only set it when every request goes through that proxy: a client that can reach the app directly can send the
    header itself. A missing or malformed value falls back to ``remote_addr``.
    """
    header = current_app.config.get('CLIENT_IP_HEADER')
    if header:
        candidate = req.headers.get(header, '').rsplit(',', 1)[-1].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    return req.remote_addr
