#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-enable}"
TOR_TRANS_PORT="${TOR_TRANS_PORT:-9040}"
TOR_USER="${TOR_USER:-debian-tor}"

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Erreur: ce script doit etre lance avec sudo/root." >&2
    exit 1
  fi
}

tor_uid() {
  id -u "$TOR_USER" 2>/dev/null || true
}

delete_rule_if_exists() {
  local chain="$1"
  shift
  while iptables -t nat -C "$chain" "$@" 2>/dev/null; do
    iptables -t nat -D "$chain" "$@"
  done
}

disable_rules() {
  local uid
  uid="$(tor_uid)"

  delete_rule_if_exists OUTPUT -p tcp -m owner --uid-owner "${uid:-0}" -j RETURN
  delete_rule_if_exists OUTPUT -o lo -j RETURN
  delete_rule_if_exists OUTPUT -d 127.0.0.0/8 -j RETURN
  delete_rule_if_exists OUTPUT -d 10.0.0.0/8 -j RETURN
  delete_rule_if_exists OUTPUT -d 172.16.0.0/12 -j RETURN
  delete_rule_if_exists OUTPUT -d 192.168.0.0/16 -j RETURN
  delete_rule_if_exists OUTPUT -d 169.254.0.0/16 -j RETURN
  delete_rule_if_exists OUTPUT -d 224.0.0.0/4 -j RETURN
  delete_rule_if_exists OUTPUT -d 240.0.0.0/4 -j RETURN
  delete_rule_if_exists OUTPUT -p tcp -j REDIRECT --to-ports "$TOR_TRANS_PORT"
}

enable_rules() {
  local uid
  uid="$(tor_uid)"

  if [ -z "$uid" ]; then
    echo "Erreur: utilisateur Tor introuvable: $TOR_USER" >&2
    echo "Astuce: export TOR_USER=tor si votre distribution utilise ce nom." >&2
    exit 1
  fi

  disable_rules

  iptables -t nat -A OUTPUT -p tcp -m owner --uid-owner "$uid" -j RETURN
  iptables -t nat -A OUTPUT -o lo -j RETURN
  iptables -t nat -A OUTPUT -d 127.0.0.0/8 -j RETURN
  iptables -t nat -A OUTPUT -d 10.0.0.0/8 -j RETURN
  iptables -t nat -A OUTPUT -d 172.16.0.0/12 -j RETURN
  iptables -t nat -A OUTPUT -d 192.168.0.0/16 -j RETURN
  iptables -t nat -A OUTPUT -d 169.254.0.0/16 -j RETURN
  iptables -t nat -A OUTPUT -d 224.0.0.0/4 -j RETURN
  iptables -t nat -A OUTPUT -d 240.0.0.0/4 -j RETURN
  iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-ports "$TOR_TRANS_PORT"
}

require_root

case "$ACTION" in
  enable)
    enable_rules
    echo "Regles iptables NAT activees vers le port Tor $TOR_TRANS_PORT."
    ;;
  disable)
    disable_rules
    echo "Regles iptables NAT desactivees."
    ;;
  *)
    echo "Usage: sudo $0 {enable|disable}" >&2
    exit 1
    ;;
esac
