"""
Starter on-chain exploit monitor.

Watches how much of a token a contract holds (for example, the USDC sitting in
a lending pool or DEX pool) and alerts you when that balance drops sharply in
a short window -- the classic signature of a pool being drained.

Run:
    python monitor.py          # start watching
    python monitor.py --test   # send one test alert and exit
"""

import json
import os
import sys
import time
from collections import deque

import requests
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# ---- Settings (from .env) --------------------------------------------------
RPC_URL = os.getenv("RPC_URL")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
DROP_PCT = float(os.getenv("DROP_PCT", "20"))              # alert if balance falls this % ...
WINDOW_BLOCKS = int(os.getenv("WINDOW_BLOCKS", "30"))      # ... within this many blocks (~1 min on Base)
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "2"))       # how often to check for a new block
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "600"))  # don't repeat the same alert for 10 min
EXPLORER = os.getenv("EXPLORER_URL", "https://basescan.org")

# Minimal ERC-20 interface: just the read functions we need.
ERC20_ABI = [
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "owner", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "decimals", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint8"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
]


# ---- Alerts ------------------------------------------------------------------
def send_alert(text):
    """Send to Telegram if configured; always print to the console too."""
    print(f"\n🚨 {text}\n", flush=True)
    if not (TG_TOKEN and TG_CHAT):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"[warn] Telegram send failed: {e}")


# ---- Setup -------------------------------------------------------------------
def load_watchlist(w3):
    with open("watchlist.json") as f:
        entries = json.load(f)

    watches = []
    for e in entries:
        if "PUT_" in e["holder"] or "PUT_" in e["token"]:
            sys.exit(f"Fill in a real address for '{e['name']}' in watchlist.json first.")
        token = w3.eth.contract(address=Web3.to_checksum_address(e["token"]), abi=ERC20_ABI)
        watches.append({
            "name": e["name"],
            "token": token,
            "holder": Web3.to_checksum_address(e["holder"]),
            "decimals": token.functions.decimals().call(),
            "symbol": token.functions.symbol().call(),
            "history": deque(maxlen=WINDOW_BLOCKS),  # (block, balance) pairs
            "last_alert": 0.0,
        })
    return watches


def fmt(amount, decimals):
    return f"{amount / 10**decimals:,.2f}"


# ---- Core check ----------------------------------------------------------------
def check(w, block):
    balance = w["token"].functions.balanceOf(w["holder"]).call(block_identifier=block)
    w["history"].append((block, balance))

    peak_block, peak = max(w["history"], key=lambda x: x[1])
    if peak == 0:
        return

    drop = (peak - balance) / peak * 100
    if drop >= DROP_PCT and time.time() - w["last_alert"] > COOLDOWN_SECONDS:
        w["last_alert"] = time.time()
        send_alert(
            f"⚠️ {w['name']}: {w['symbol']} balance fell {drop:.1f}% "
            f"in {block - peak_block} blocks\n"
            f"{fmt(peak, w['decimals'])} → {fmt(balance, w['decimals'])} {w['symbol']}\n"
            f"Block {block}\n"
            f"{EXPLORER}/address/{w['holder']}"
        )


def run():
    if not RPC_URL:
        sys.exit("Set RPC_URL in your .env file (see .env.example).")

    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 15}))
    if not w3.is_connected():
        sys.exit("Couldn't connect to the RPC. Check RPC_URL.")

    watches = load_watchlist(w3)
    print(f"Connected (chain id {w3.eth.chain_id}). Watching {len(watches)} target(s). "
          f"Alert threshold: -{DROP_PCT}% within {WINDOW_BLOCKS} blocks.")

    last_block = None
    backoff = POLL_SECONDS
    while True:
        try:
            block = w3.eth.block_number
            if block != last_block:
                for w in watches:
                    check(w, block)
                last_block = block
                print(f"block {block} ok", end="\r", flush=True)
            backoff = POLL_SECONDS
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("\nStopped.")
            return
        except Exception as e:
            # Network blips, rate limits, laptop waking from sleep, etc.
            print(f"\n[warn] {type(e).__name__}: {e} -- retrying in {backoff:.0f}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        send_alert("✅ Test alert from your exploit monitor. If you see this, alerts work.")
    else:
        run()
