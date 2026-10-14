# Exploit Monitor (starter)

Watches token balances held by DeFi contracts and alerts you when one drops sharply, which is what a drained pool looks like.

## Setup

1. **Install Python 3.10+**, then in this folder run:
   ```
   pip install -r requirements.txt
   ```

2. **Get a free RPC URL.** Sign up at Alchemy (or Infura or QuickNode), create an app on **Base Mainnet**, and copy the HTTPS URL.

3. **Create your `.env`.** Copy `.env.example` to `.env` and paste in your `RPC_URL`.

4. **Pick something to watch.** Open `watchlist.json`:
   - `token` is the token to track. USDC on Base is pre-filled; double-check it on basescan.org.
   - `holder` is the contract holding that token, such as a lending pool or DEX pool. One easy way to find candidates is to open the token on basescan.org, go to the **Holders** tab, and look for the big *contract* holders labeled with protocol names.
   - Add more entries to the list to watch more things.

5. **(Optional) Telegram alerts.**
   - In Telegram, message **@BotFather**, send `/newbot`, and copy the token into `TELEGRAM_BOT_TOKEN`.
   - Send your new bot any message, then open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and copy the `"chat":{"id": ...}` number into `TELEGRAM_CHAT_ID`.
   - Run `python monitor.py --test` to confirm an alert reaches your phone.

## Run

```
python monitor.py
```

Stop it with Ctrl+C. It reconnects on its own if the network drops.

## Tuning

- `DROP_PCT` is how big a drop triggers an alert. Normal pools move a few % with large withdrawals, so 20% is a sane start.
- `WINDOW_BLOCKS` is how fast the drop has to happen. Base makes a block about every 2 seconds, so 30 blocks is about 1 minute.

## Next ideas

- Flash loan detection (watch Aave/Balancer flash loan events)
- Oracle price jump alerts
- Watching multiple chains
