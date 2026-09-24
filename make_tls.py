#!/usr/bin/env python3
"""Create a dedicated local CA and IP-SAN certificate. Never overwrite existing keys."""
import argparse
import ipaddress
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ip", required=True, type=ipaddress.ip_address)
parser.add_argument("--out", type=Path, default=Path("pico_tls"))
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
if any(args.out.iterdir()):
    parser.error("Output directory must be empty")
ca_key, ca, key, request, cert = [args.out / name for name in
                                ("ca.key", "ca.crt", "server.key", "server.csr", "server.crt")]
commands = [
    ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365", "-sha256",
     "-keyout", str(ca_key), "-out", str(ca), "-subj", "/CN=RoboDojo Pico Local CA",
     "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign"],
    ["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(request),
     "-subj", "/CN=RoboDojo Pico Workstation"],
]
for command in commands:
    subprocess.run(command, check=True, capture_output=True)
extensions = args.out / "server.ext"
extensions.write_text(f"subjectAltName=IP:{args.ip},IP:127.0.0.1,DNS:localhost\n"
                      "basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n"
                      "extendedKeyUsage=serverAuth\n")
subprocess.run(["openssl", "x509", "-req", "-in", str(request), "-CA", str(ca), "-CAkey", str(ca_key),
                "-CAcreateserial", "-out", str(cert), "-days", "365", "-sha256", "-extfile", str(extensions)],
               check=True, capture_output=True)
ca_key.chmod(0o600)
key.chmod(0o600)
print(f"Created {cert}. Trust {ca} on the Pico before opening HTTPS. Keep both .key files on this computer.")
