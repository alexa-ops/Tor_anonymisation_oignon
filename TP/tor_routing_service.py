#!/usr/bin/env python3
"""
TP 1 - Tor Routing Service.

Au demarrage, le service configure iptables pour rediriger le TCP sortant
vers le TransPort de Tor, puis demande une nouvelle identite toutes les
5 secondes via le ControlPort.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

from stem import Signal
from stem.control import Controller


BASE_DIR = Path(__file__).resolve().parent
IPTABLES_SCRIPT = BASE_DIR / "iptables_nat.sh"
LOG_FILE = BASE_DIR / "tor_exit_ip.log"

CONTROL_HOST = os.getenv("TOR_CONTROL_HOST", "127.0.0.1")
CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
ROTATION_SECONDS = int(os.getenv("TOR_ROTATION_SECONDS", "5"))
IP_CHECK_URL = os.getenv("TOR_IP_CHECK_URL", "https://check.torproject.org/api/ip")

stop_event = threading.Event()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def require_root() -> None:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SystemExit("Ce service doit etre lance avec sudo/root pour modifier iptables.")


def run_iptables(action: str) -> None:
    subprocess.run(["bash", str(IPTABLES_SCRIPT), action], check=True)


def get_exit_ip() -> str:
    request = urllib.request.Request(
        IP_CHECK_URL,
        headers={"User-Agent": "TP1-Tor-Routing-Service/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8", errors="replace").strip()
    except urllib.error.URLError as exc:
        return f"IP inconnue: {exc}"


def rotation_loop(controller: Controller) -> None:
    while not stop_event.is_set():
        controller.signal(Signal.NEWNYM)
        exit_ip = get_exit_ip()
        logging.info("SIGNAL NEWNYM envoye - IP de sortie: %s", exit_ip)
        stop_event.wait(ROTATION_SECONDS)


def handle_stop(signum: int, _frame: object) -> None:
    logging.info("Signal %s recu, arret du service...", signum)
    stop_event.set()


def main() -> int:
    configure_logging()
    require_root()

    if not IPTABLES_SCRIPT.exists():
        logging.error("Script iptables introuvable: %s", IPTABLES_SCRIPT)
        return 1

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    logging.info("Activation des regles iptables NAT...")
    run_iptables("enable")

    try:
        with Controller.from_port(address=CONTROL_HOST, port=CONTROL_PORT) as controller:
            controller.authenticate()
            logging.info("Connecte au ControlPort Tor %s:%s.", CONTROL_HOST, CONTROL_PORT)

            worker = threading.Thread(target=rotation_loop, args=(controller,), daemon=True)
            worker.start()

            while not stop_event.is_set():
                stop_event.wait(1)

            worker.join(timeout=ROTATION_SECONDS + 2)
    finally:
        logging.info("Nettoyage des regles iptables NAT...")
        try:
            run_iptables("disable")
        except subprocess.CalledProcessError as exc:
            logging.error("Impossible de nettoyer iptables: %s", exc)

    logging.info("Service arrete proprement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
