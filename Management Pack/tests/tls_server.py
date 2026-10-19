#  Copyright 2026 VCF Operations vCommunity Management Pack
"""A local HTTPS server with a self-signed certificate, for the TLS tests.

It stands in for a vCenter or an ESXi host. It records every request that reaches it, so a test can show that a
refused certificate stopped the connection before anything, such as a login, was sent.

Needs the 'cryptography' package. The tests that use it skip when it is not installed.
"""
import datetime
import hashlib
import ipaddress
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSIONS_XML = b"""<?xml version="1.0" encoding="UTF-8" ?>
<namespaces version="1.0">
  <namespace>
    <name>urn:vim25</name>
    <version>8.0.3.0</version>
    <priorVersions>
      <version>8.0.2.0</version>
      <version>8.0.1.0</version>
      <version>8.0.0.1</version>
      <version>8.0.0.0</version>
      <version>7.0.3.0</version>
    </priorVersions>
  </namespace>
</namespaces>
"""


def make_certificate(directory):
    """A new self-signed certificate for localhost. Returns (cert file, key file, DER bytes)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_file = directory / "server.pem"
    key_file = directory / "server.key"
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return cert_file, key_file, cert.public_bytes(serialization.Encoding.DER)


def thumbprint(der: bytes, algorithm: str = "sha256", colons: bool = False, upper: bool = False) -> str:
    digest = hashlib.new(algorithm, der).hexdigest()
    if upper:
        digest = digest.upper()
    return ":".join(digest[i:i + 2] for i in range(0, len(digest), 2)) if colons else digest


class TlsServer:
    """Use as a context manager. .port, .der, .requests: [(method, path, body)] of what reached the server."""

    def __init__(self, directory):
        self.cert_file, self.key_file, self.der = make_certificate(directory)
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _body(self):
                length = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(length) if length else b""

            def _reply(self, status, body=b"", content_type="text/plain"):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                outer.requests.append(("GET", self.path, b""))
                if self.path.endswith("/vimServiceVersions.xml"):
                    self._reply(200, VERSIONS_XML, "text/xml")
                else:
                    self._reply(200, b"script output")

            def do_PUT(self):
                outer.requests.append(("PUT", self.path, self._body()))
                self._reply(200)

            def do_POST(self):
                outer.requests.append(("POST", self.path, self._body()))
                self._reply(500)

            def log_message(self, *args):
                pass

        class QuietServer(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass  # a client that refuses the certificate aborts the handshake: that is the test, not a fault

        self._server = QuietServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert_file, self.key_file)
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
