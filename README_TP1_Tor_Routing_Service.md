# TP 1 - Tor Routing Service

Objectif : creer un service Python qui configure automatiquement `iptables` pour faire passer tout le trafic TCP sortant par Tor, puis demande a Tor une nouvelle identite toutes les 5 secondes avec `SIGNAL NEWNYM`.

Ce TP reprend les 4 blocs de l'architecture de la diapo :

- `torrc` : configuration de Tor avec `TransPort 9040` et `ControlPort 9051`.
- `iptables NAT` : redirection du TCP sortant vers le proxy transparent de Tor.
- `stem Controller` : controle de Tor depuis Python.
- `Thread Rotation` : demande d'une nouvelle IP de sortie toutes les 5 secondes et journalisation.

## Fichiers fournis

- `torrc` : configuration Tor a utiliser pour le TP.
- `iptables_nat.sh` : script d'activation/desactivation des regles NAT.
- `tor_routing_service.py` : service Python principal.
- `requirements.txt` : dependances Python.
- `tor-routing.service` : exemple d'unite systemd.
- `.gitignore` : ignore les fichiers de logs et environnements Python.

## Prerequis

Sur Debian/Ubuntu :

```bash
sudo apt update
sudo apt install -y tor python3 python3-venv iptables curl
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x iptables_nat.sh
```

## Configuration de Tor

Sauvegarder la configuration existante puis copier le fichier du TP :

```bash
sudo cp /etc/tor/torrc /etc/tor/torrc.backup
sudo cp torrc /etc/tor/torrc
sudo systemctl restart tor
sudo systemctl status tor
```

Verifier que Tor ecoute bien sur les ports attendus :

```bash
ss -lntp | grep -E '9040|9051'
```

## Lancer le service a la main

Le service doit etre lance avec les privileges root, car il modifie `iptables`.

```bash
sudo .venv/bin/python tor_routing_service.py
```

Le programme :

1. active les regles `iptables`;
2. contacte Tor sur le port de controle `9051`;
3. envoie `SIGNAL NEWNYM` toutes les 5 secondes;
4. ecrit l'IP de sortie dans `tor_exit_ip.log`;
5. nettoie les regles `iptables` quand on l'arrete avec `Ctrl+C`.

## Utiliser systemd

Adapter les chemins dans `tor-routing.service`, puis installer l'unite :

```bash
sudo cp tor-routing.service /etc/systemd/system/tor-routing.service
sudo systemctl daemon-reload
sudo systemctl enable --now tor-routing.service
sudo journalctl -u tor-routing.service -f
```

## Desactiver les regles NAT

En cas de besoin :

```bash
sudo bash iptables_nat.sh disable
```

## Tests rapides

Verifier l'IP publique :

```bash
curl https://check.torproject.org/api/ip
tail -f tor_exit_ip.log
```

Chaque rotation envoie une demande de nouvelle identite a Tor. Tor peut refuser de changer immediatement d'IP si le reseau impose un delai interne ou si aucun nouveau circuit n'est encore disponible.

## Attention

Ce TP manipule le routage local. Il est conseille de l'executer dans une VM Linux de laboratoire. Les connexions UDP ne sont pas redirigees par ce TP, car la diapo demande explicitement la redirection de tout le trafic TCP.
