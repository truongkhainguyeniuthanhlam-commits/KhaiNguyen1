"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     Discord Multi-System Bot                                ║
║                     Components V2  |  Single File Edition                   ║
║                     discord.py 2.4+  |  aiohttp  |  aiosqlite              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Install  :  pip install discord.py aiohttp aiosqlite                       ║
║  Run      :  python bot.py                                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
╠══════════════════════════════════════════════════════════════════════════════╣
║  /invites setup   — Configure invite tracking channel                       ║
║  /invites check   — Check how many members a user has invited               ║
║  /invites top     — Show invite leaderboard                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  /welcome setup   — Configure welcome message system                        ║
║  /leave   setup   — Configure leave message system                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  /payment setup        — Configure VietQR + Casso                           ║
║  /payment create       — Generate a QR payment request                      ║
║  /payment check        — Check payment status by ref                        ║
║  /payment confirm      — Manually confirm a payment                         ║
║  /payment cancel       — Cancel a pending payment                           ║
║  /payment list         — List all payments with filter                      ║
║  /payment announce_all — Send daily summary to channel                      ║
║  /payment info         — Show current payment config                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  /ping             — Check bot latency                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import pathlib
import random
import string
import time
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              CREDENTIALS                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

TOKEN    = os.getenv("TOKEN", "")
OWNER_ID = 1498384419805986886
PREFIX   = "!"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              STRING TABLE                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

S = {
    # ── Panel ──────────────────────────────────────────────────────────────────
    "panel_title":            "Support Center",
    "panel_categories_title": "### Available Categories",

    # ── Modal ──────────────────────────────────────────────────────────────────
    "modal_subject_label":    "Subject",
    "modal_detail_label":     "Detailed Description",
    "modal_detail_ph":        "Provide As Much Detail As Possible...",

    # ── Buttons ────────────────────────────────────────────────────────────────

    # ── Close Flow ─────────────────────────────────────────────────────────────
    "close_cancelled":        "Close Request Cancelled.",

    # ── Claim Flow ─────────────────────────────────────────────────────────────

    # ── Misc ───────────────────────────────────────────────────────────────────
    "transcript_ok":          "Transcript Generated Successfully.",
    "err_open_close_first":   "Please Close It Before Opening A New One.",
    "err_panel_sent":         "Panel Sent Successfully.",

    # ── Setup ──────────────────────────────────────────────────────────────────
    "setup_ok":               "Setup Complete",
    "setup_category":         "Category",
    "setup_role":             "Support Role",
    "setup_log":              "Log Channel",
    "setup_not_set":          "Not Set",

    # ── List ───────────────────────────────────────────────────────────────────
    "list_unclaimed":         "Unclaimed",

    # ── Category Labels ────────────────────────────────────────────────────────
    "cat_general_label":          "General Support",
    "cat_general_desc":           "Questions And General Help",
    "cat_slot_transfer_label":    "Slot Transfers",
    "cat_slot_transfer_desc":     "Moving Or Transferring Slots",
    "cat_deposit_label":          "Deposit Support",
    "cat_deposit_desc":           "Issues With Deposits Or Balances",
}

def t(key: str) -> str:
    return S.get(key, key)

def _cat_label(key: str) -> str:
    return S.get(f"cat_{key}_label", key)

def _cat_desc(key: str) -> str:
    return S.get(f"cat_{key}_desc", key)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                               LOGGING                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("Bot")

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                             OWNER CHECK                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "Access Denied. This Command Is Restricted To The Bot Owner.",
                ephemeral=True,
            )
            return False
        return True
    return app_commands.check(predicate)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        COMPONENTS V2 HELPERS                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

V2_FLAG = 1 << 15

def _text(content: str) -> dict:
    return {"type": 10, "content": content}

def _separator(divider: bool = True, spacing: int = 1) -> dict:
    return {"type": 14, "divider": divider, "spacing": spacing}

def _select(custom_id: str, placeholder: str, options: list[dict]) -> dict:
    return {
        "type": 1,
        "components": [{
            "type":        3,
            "custom_id":   custom_id,
            "placeholder": placeholder,
            "min_values":  1,
            "max_values":  1,
            "options":     options,
        }],
    }

def _button(label: str, custom_id: str, style: int = 2) -> dict:
    return {"type": 2, "style": style, "label": label, "custom_id": custom_id}

def _action_row(*buttons) -> dict:
    return {"type": 1, "components": list(buttons)}

def _container(*components, accent_color: int = 0xFFFFFF) -> dict:
    return {"type": 17, "accent_color": accent_color, "components": list(components)}

def _section(text_content: str, thumbnail_url: str) -> dict:
    return {
        "type": 9,
        "components": [{"type": 10, "content": text_content}],
        "accessory":  {"type": 11, "media": {"url": thumbnail_url}},
    }

async def _v2_send(channel: discord.TextChannel, components: list[dict]) -> dict:
    url     = f"https://discord.com/api/v10/channels/{channel.id}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = {"flags": V2_FLAG, "components": components}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload, headers=headers) as r:
            data = await r.json()
            if r.status not in (200, 201):
                log.error("V2 Send Error %s: %s", r.status, data)
            return data

async def _v2_respond(
    interaction: discord.Interaction,
    components: list[dict],
    *,
    ephemeral: bool = True,
) -> None:
    flags   = V2_FLAG | (64 if ephemeral else 0)
    url     = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = {"type": 4, "data": {"flags": flags, "components": components}}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload, headers=headers) as r:
            if r.status not in (200, 204):
                log.error("V2 Respond Error %s: %s", r.status, await r.json())

async def _v2_followup(
    interaction: discord.Interaction,
    components: list[dict],
    *,
    ephemeral: bool = True,
) -> None:
    flags   = V2_FLAG | (64 if ephemeral else 0)
    url     = f"https://discord.com/api/v10/webhooks/{interaction.application_id}/{interaction.token}"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = {"flags": flags, "components": components}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload, headers=headers) as r:
            if r.status not in (200, 201):
                log.error("V2 Followup Error %s: %s", r.status, await r.json())

async def _v2_edit_msg(channel_id: int, message_id: int, components: list[dict]) -> None:
    url     = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = {"flags": V2_FLAG, "components": components}
    async with aiohttp.ClientSession() as s:
        async with s.patch(url, json=payload, headers=headers) as r:
            if r.status not in (200, 201):
                log.error("V2 Edit Error %s: %s", r.status, await r.json())

async def _v2_send_with_file(
    channel_id: int,
    components: list[dict],
    file_bytes: bytes,
    filename: str,
) -> None:
    """Send a Components V2 message with a file attachment via multipart."""
    url     = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}
    payload = {"flags": V2_FLAG, "components": components}
    form    = aiohttp.FormData()
    form.add_field("payload_json", json.dumps(payload), content_type="application/json")
    form.add_field("files[0]", file_bytes, filename=filename, content_type="text/plain")
    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=form, headers=headers) as r:
            data = await r.json()
            if r.status not in (200, 201):
                log.error("V2 Send File Error %s: %s", r.status, data)

async def _v2_send_with_channel_id(channel_id: int, components: list[dict]) -> None:
    """Send a Components V2 message to a channel by ID (e.g. DM channel)."""
    url     = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = {"flags": V2_FLAG, "components": components}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload, headers=headers) as r:
            data = await r.json()
            if r.status not in (200, 201):
                log.error("V2 Send Channel Error %s: %s", r.status, data)

async def _get_or_create_dm(user: discord.User | discord.Member) -> int | None:
    """Return the DM channel ID for a user, creating it if needed."""
    url     = "https://discord.com/api/v10/users/@me/channels"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"recipient_id": user.id}, headers=headers) as r:
            if r.status in (200, 201):
                data = await r.json()
                return int(data["id"])
    return None

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      PERSISTENT STORE  (SQLite via aiosqlite)               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

DB_PATH = pathlib.Path("bot.db")

# In-memory config + runtime data — kept per-guild
_STORE: dict[int, dict] = {}

_DEFAULTS: dict = {
    "log_channel":      None,
    "counter":          0,
    "welcome_channel":  None,
    "welcome_purchase": None,
    "welcome_rules":    None,
    "welcome_news":     None,
    "leave_channel":    None,
    "invites_channel":  None,
    "pay_bank_id":      "ICB",
    "pay_account_no":   "0907617630",
    "pay_account_name": "Nguyen Van A",
    "pay_casso_key":    None,
    "pay_log_channel":  None,
    "pay_confirm_role": None,
    "pay_timeout":      600,
    "payments":         {},
    "pay_announce_channel": None,
}

_CONFIG_KEYS = {
    "counter", "welcome_channel", "welcome_purchase", "welcome_rules",
    "welcome_news", "pay_bank_id", "pay_account_no", "pay_account_name",
    "pay_casso_key", "pay_log_channel", "pay_confirm_role", "pay_timeout",
    "pay_announce_channel", "leave_channel", "invites_channel",
}

# ── Database init ──────────────────────────────────────────────────────────────

async def _db_init() -> None:
    """Create all tables if they don't exist yet."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            -- Guild config (one row per guild)
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id    INTEGER PRIMARY KEY,
                data_json   TEXT    NOT NULL DEFAULT '{}'
            );

            -- Payment records
            CREATE TABLE IF NOT EXISTS payments (
                ref             TEXT    NOT NULL,
                guild_id        INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                amount          INTEGER NOT NULL,
                description     TEXT,
                channel_id      INTEGER,
                message_id      INTEGER,
                status          TEXT    NOT NULL DEFAULT 'pending',
                created_at      REAL    NOT NULL,
                confirmed_at    REAL,
                confirmed_by_tx TEXT,
                PRIMARY KEY (ref, guild_id)
            );

            -- Invite tracking (cumulative per inviter per guild)
            CREATE TABLE IF NOT EXISTS invite_stats (
                guild_id    INTEGER NOT NULL,
                inviter_id  INTEGER NOT NULL,
                total_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, inviter_id)
            );
        """)
        await db.commit()
    log.info("Database Initialised At %s", DB_PATH)

# ── Load / Save guild config ───────────────────────────────────────────────────

async def _db_load_all() -> None:
    """Load all guild configs from SQLite into _STORE."""
    global _STORE
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT guild_id, data_json FROM guild_config") as cur:
            rows = await cur.fetchall()
    for guild_id, data_json in rows:
        try:
            saved = json.loads(data_json)
        except Exception:
            saved = {}
        d = dict(_DEFAULTS)
        for k in _CONFIG_KEYS:
            if k in saved:
                d[k] = saved[k]
        # Restore runtime dicts
        d["payments"] = {}  # payments loaded lazily from DB
        _STORE[int(guild_id)] = d
    log.info("Loaded SQLite — %d Guild(s) Restored.", len(_STORE))

async def _db_save_guild(guild_id: int) -> None:
    """Persist one guild's config to SQLite (async-safe)."""
    d = _STORE.get(guild_id)
    if d is None:
        return
    blob = {k: d[k] for k in _CONFIG_KEYS if k in d}
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO guild_config(guild_id, data_json) VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET data_json=excluded.data_json",
            (guild_id, json.dumps(blob, ensure_ascii=False)),
        )
        await db.commit()

def _save_data() -> None:
    """No-op shim — all saves are done via await _db_save_guild() directly."""
    pass

def _gdata(guild_id: int) -> dict:
    if guild_id not in _STORE:
        _STORE[guild_id] = dict(_DEFAULTS)
        _STORE[guild_id]["payments"] = {}
    return _STORE[guild_id]

async def _invite_add(guild_id: int, inviter_id: int) -> int:
    """Increment invite count for inviter and return new total."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invite_stats(guild_id, inviter_id, total_count) VALUES(?,?,1) "
            "ON CONFLICT(guild_id, inviter_id) DO UPDATE SET total_count = total_count + 1",
            (guild_id, inviter_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT total_count FROM invite_stats WHERE guild_id=? AND inviter_id=?",
            (guild_id, inviter_id),
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 1

async def _invite_get(guild_id: int, inviter_id: int) -> int:
    """Return cumulative invite count for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT total_count FROM invite_stats WHERE guild_id=? AND inviter_id=?",
            (guild_id, inviter_id),
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0

async def _invite_leaderboard(guild_id: int, limit: int = 10) -> list[tuple[int, int]]:
    """Return top inviters as list of (inviter_id, total_count)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT inviter_id, total_count FROM invite_stats "
            "WHERE guild_id=? ORDER BY total_count DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [(r[0], r[1]) for r in rows]

# ── Payment DB helpers ─────────────────────────────────────────────────────────

async def _db_save_payment(guild_id: int, ref: str, p: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO payments(ref,guild_id,user_id,amount,description,channel_id,"
            "message_id,status,created_at,confirmed_at,confirmed_by_tx) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(ref,guild_id) DO UPDATE SET "
            "status=excluded.status, confirmed_at=excluded.confirmed_at, "
            "confirmed_by_tx=excluded.confirmed_by_tx",
            (
                ref, guild_id, p["user_id"], p["amount"], p.get("description",""),
                p["channel_id"], p["message_id"], p["status"],
                p["created_at"], p.get("confirmed_at"), p.get("confirmed_by_tx"),
            ),
        )
        await db.commit()

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           VIETQR HELPER                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

VIETQR_BANKS = {
    "ACB":         "ACB",
    "BIDV":        "BIDV",
    "MB":          "MB",
    "MSB":         "MSB",
    "OCB":         "OCB",
    "SCB":         "SCB",
    "SHB":         "SHB",
    "TCB":         "TCB",
    "TPB":         "TPB",
    "VCB":         "VCB",
    "VIB":         "VIB",
    "VPB":         "VPB",
    "VIETINBANK":  "ICB",
    "AGRIBANK":    "VBA",
    "TPBANK":      "TPB",
    "SACOMBANK":   "STB",
    "HDBANK":      "HDB",
    "SEABANK":     "SEAB",
    "ABBANK":      "ABB",
    "BAOVIETBANK": "BVB",
}

def _vietqr_url(
    bank_id: str,
    account_no: str,
    account_name: str,
    amount: int,
    ref: str,
) -> str:
    from urllib.parse import quote
    base  = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png"
    query = (
        f"?amount={amount}"
        f"&addInfo={quote(ref)}"
        f"&accountName={quote(account_name)}"
    )
    return base + query

def _gen_ref(guild_id: int, user_id: int) -> str:
    chars  = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"PAY{suffix}"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                         CASSO AUTO-CONFIRM                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _casso_get_transactions(api_key: str, from_id: int = 0) -> list[dict]:
    url     = "https://oauth.casso.vn/v2/transactions"
    headers = {"Authorization": f"Apikey {api_key}"}
    params  = {"page": 1, "pageSize": 20}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                url, headers=headers, params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status != 200:
                    log.warning("Casso API Error: %s", r.status)
                    return []
                data = await r.json()
                return data.get("data", {}).get("records", [])
    except Exception as e:
        log.warning("Casso Poll Error: %s", e)
        return []

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                         PAYMENT STORE HELPERS                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _payment_create(
    guild_id: int,
    user_id: int,
    amount: int,
    description: str,
    channel_id: int,
    message_id: int,
    ref: str = "",
) -> dict:
    d = _gdata(guild_id)
    if not ref:
        ref = _gen_ref(guild_id, user_id)
        while ref in d["payments"]:
            ref = _gen_ref(guild_id, user_id)
    payment = {
        "ref":             ref,
        "guild_id":        guild_id,
        "user_id":         user_id,
        "amount":          amount,
        "description":     description,
        "channel_id":      channel_id,
        "message_id":      message_id,
        "status":          "pending",
        "created_at":      time.time(),
        "confirmed_at":    None,
        "confirmed_by_tx": None,
    }
    d["payments"][ref] = payment
    await _db_save_payment(guild_id, ref, payment)
    return payment

def _payment_get(guild_id: int, ref: str) -> dict | None:
    return _gdata(guild_id)["payments"].get(ref)

async def _payment_confirm(guild_id: int, ref: str, tx_id: str) -> bool:
    p = _payment_get(guild_id, ref)
    if not p or p["status"] != "pending":
        return False
    p["status"]          = "confirmed"
    p["confirmed_at"]    = time.time()
    p["confirmed_by_tx"] = tx_id
    await _db_save_payment(guild_id, ref, p)
    return True

async def _payment_expire(guild_id: int, ref: str) -> bool:
    p = _payment_get(guild_id, ref)
    if not p or p["status"] != "pending":
        return False
    p["status"] = "expired"
    await _db_save_payment(guild_id, ref, p)
    return True

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                          /welcome COMMANDS                                  ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  /welcome setup   — Configure welcome message system                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

welcome_grp = app_commands.Group(
    name="welcome",
    description="Welcome Message System",
    default_permissions=discord.Permissions(0),
)

@welcome_grp.command(name="setup", description="Configure The Welcome Message System")
@app_commands.describe(
    channel="Channel To Send Welcome Messages In",
    purchase="Purchase / Shop Channel To Link",
    rules="Rules Channel To Link",
    news="Announcements / News Channel To Link",
)
@is_owner()
async def welcome_setup(
    interaction: discord.Interaction,
    channel:     discord.TextChannel,
    purchase:    Optional[discord.TextChannel] = None,
    rules:       Optional[discord.TextChannel] = None,
    news:        Optional[discord.TextChannel] = None,
):
    await interaction.response.defer(ephemeral=True)
    d = _gdata(interaction.guild_id)
    d["welcome_channel"]  = channel.id
    d["welcome_purchase"] = purchase.id if purchase else None
    d["welcome_rules"]    = rules.id    if rules    else None
    d["welcome_news"]     = news.id     if news     else None
    await _db_save_guild(interaction.guild_id)

    def _ref(ch: Optional[discord.TextChannel]) -> str:
        return ch.mention if ch else "`Not Set`"

    await _v2_followup(interaction, [
        _container(
            _text("## Welcome System Configured"),
            _separator(),
            _text(
                f"**Welcome Channel:** {channel.mention}\n"
                f"**Purchase Channel:** {_ref(purchase)}\n"
                f"**Rules Channel:** {_ref(rules)}\n"
                f"**News Channel:** {_ref(news)}"
            ),
            _separator(),
            _text("Members Will Now Receive A Welcome Message When They Join."),
        )
    ])
    log.info("Welcome Setup By %s In '%s'", interaction.user, interaction.guild.name)

bot.tree.add_command(welcome_grp)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                          /payment COMMANDS                                  ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  /payment setup        — Configure VietQR + Casso                           ║
# ║  /payment create       — Generate a QR payment request                      ║
# ║  /payment check        — Check payment status by ref                        ║
# ║  /payment confirm      — Manually confirm a payment (owner)                 ║
# ║  /payment cancel       — Cancel a pending payment (owner)                   ║
# ║  /payment list         — List all payments with filter                      ║
# ║  /payment announce_all — Send daily summary to channel                      ║
# ║  /payment info         — Show current payment config                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

payment_grp = app_commands.Group(
    name="payment",
    description="VietQR Payment System",
    default_permissions=discord.Permissions(0),
)

@payment_grp.command(name="setup", description="Configure The VietQR AutoBank Payment System")
@app_commands.describe(
    bank_id="VietQR Bank Code (E.g. MB, VCB, TCB, VPB, TPB, ACB)",
    account_no="Bank Account Number",
    account_name="Account Holder Name (Shown On QR)",
    casso_key="Casso API Key For Auto-Confirm (Get From casso.vn)",
    log_channel="Channel To Log Confirmed Payments",
    confirm_role="Role To Ping On Payment Confirmed (Optional)",
    timeout="Payment Expiry In Minutes (Default: 10)",
)
@is_owner()
async def payment_setup(
    interaction:   discord.Interaction,
    bank_id:       str,
    account_no:    str,
    account_name:  str,
    casso_key:     str,
    log_channel:   discord.TextChannel,
    confirm_role:  Optional[discord.Role] = None,
    timeout:       int = 10,
):
    await interaction.response.defer(ephemeral=True)
    d             = _gdata(interaction.guild_id)
    bank_id_upper = bank_id.strip().upper()

    d["pay_bank_id"]      = bank_id_upper
    d["pay_account_no"]   = account_no.strip()
    d["pay_account_name"] = account_name.strip()
    d["pay_casso_key"]    = casso_key.strip()
    d["pay_log_channel"]  = log_channel.id
    d["pay_confirm_role"] = confirm_role.id if confirm_role else None
    d["pay_timeout"]      = max(1, timeout) * 60
    await _db_save_guild(interaction.guild_id)

    await _v2_followup(interaction, [
        _container(
            _text("## ✅ Payment System Configured"),
            _separator(),
            _text(
                f"**Bank:** `{bank_id_upper}`\n"
                f"**Account No:** `{account_no}`\n"
                f"**Account Name:** `{account_name}`\n"
                f"**Log Channel:** {log_channel.mention}\n"
                f"**Ping Role:** {confirm_role.mention if confirm_role else '`None`'}\n"
                f"**Casso API Key:** `{'*' * min(len(casso_key), 8)}...` *(Hidden)*\n"
                f"**Payment Timeout:** `{timeout} Minutes`\n\n"
                "Auto-Confirm: Bot Will Poll Casso Every 15s And Confirm Matching Payments.\n"
                "Run `/payment create` To Generate A QR Code."
            ),
        )
    ])
    log.info(
        "Payment Setup By %s In '%s' — Bank: %s  Account: %s",
        interaction.user, interaction.guild.name, bank_id_upper, account_no,
    )

@payment_grp.command(name="create", description="Generate A VietQR Payment QR Code")
@app_commands.describe(
    amount="Amount In VND (E.g. 50000)",
    user="Who Is Paying (Optional, Defaults To You)",
)
async def payment_create(
    interaction: discord.Interaction,
    amount:      int,
    user:        Optional[discord.Member] = None,
):
    await interaction.response.defer(ephemeral=False, thinking=True)
    d = _gdata(interaction.guild_id)

    if not d.get("pay_bank_id") or not d.get("pay_account_no"):
        return await interaction.followup.send(
            "Payment System Not Configured. Ask An Admin To Run `/payment setup` First.",
            ephemeral=True,
        )

    if amount < 1000:
        return await interaction.followup.send(
            "Minimum Amount Is `1,000 VND`.", ephemeral=True
        )

    payer      = user or interaction.user
    bank_id    = d["pay_bank_id"]
    account_no = d["pay_account_no"]
    acc_name   = d["pay_account_name"]
    ref        = _gen_ref(interaction.guild_id, payer.id)
    while ref in d["payments"]:
        ref = _gen_ref(interaction.guild_id, payer.id)

    qr_url = _vietqr_url(bank_id, account_no, acc_name, amount, ref)
    ts     = int(time.time())
    expire = ts + d.get("pay_timeout", 600)

    channel: discord.TextChannel = interaction.channel  # type: ignore
    msg_data = await _v2_send(channel, [
        _container(
            _text("## 🏦 Payment Request"),
            _separator(),
            _section(
                f"**Payer:** {payer.mention}\n"
                f"**Amount:** `{amount:,} VND`\n"
                f"**Bank:** `{bank_id}` — `{account_no}`\n"
                f"**Account Name:** `{acc_name}`\n"
                f"**Transfer Description:** `{ref}`\n"
                f"⏰ Expires <t:{expire}:R>",
                qr_url,
            ),
            _separator(),
            _text(
                "**Instructions:**\n"
                "> 1️⃣  Open Your Banking App\n"
                "> 2️⃣  Scan The QR Code On The Right\n"
                f"> 3️⃣  Enter Exactly This Transfer Description: **`{ref}`** — Required!\n"
                "> 4️⃣  Bot Will Auto-Confirm Within A Few Seconds\n\n"
                "-# Do Not Change The Transfer Description Or Payment Will Not Be Detected."
            ),
            _separator(),
            _action_row(_button("❌ Cancel Payment", f"payment:cancel:{ref}", style=4)),
        )
    ])

    msg_id = int(msg_data.get("id", 0))
    await _payment_create(interaction.guild_id, payer.id, amount, "", channel.id, msg_id, ref=ref)

    try:
        await interaction.delete_original_response()
    except Exception:
        pass

    log.info(
        "Payment %s Created — %s VND — Payer: %s — Bank: %s %s",
        ref, amount, payer, bank_id, account_no,
    )

@payment_grp.command(name="check", description="Manually Check A Payment Status By Reference Code")
@app_commands.describe(ref="Payment Reference Code (E.g. PAYAB1234)")
async def payment_check(interaction: discord.Interaction, ref: str):
    await interaction.response.defer(ephemeral=True)
    d = _gdata(interaction.guild_id)
    p = d["payments"].get(ref.upper())
    if not p:
        return await interaction.response.send_message(
            f"Payment `{ref}` Not Found.", ephemeral=True
        )

    status_icon = {
        "pending":   "⏳",
        "confirmed": "✅",
        "expired":   "⏰",
        "cancelled": "❌",
    }.get(p["status"], "❓")
    payer = interaction.guild.get_member(p["user_id"])
    ts    = int(p["created_at"])

    await _v2_followup(interaction, [
        _container(
            _text(f"## {status_icon} Payment Status"),
            _separator(),
            _text(
                f"**Reference:** `{ref}`\n"
                f"**Status:** {status_icon} {p['status'].upper()}\n"
                f"**Amount:** `{p['amount']:,} VND`\n"
                f"**Payer:** {payer.mention if payer else 'ID: ' + str(p['user_id'])}\n"
                f"**Created:** <t:{ts}:F>\n"
                + (f"**TX ID:** `{p['confirmed_by_tx']}`" if p.get("confirmed_by_tx") else "")
            ),
        )
    ])

@payment_grp.command(name="confirm", description="Manually Confirm A Payment (Owner Only)")
@app_commands.describe(ref="Payment Reference Code To Confirm")
@is_owner()
async def payment_confirm(interaction: discord.Interaction, ref: str):
    d          = _gdata(interaction.guild_id)
    ref_up     = ref.strip().upper()
    payments   = d["payments"]

    matched_key = next((k for k in payments if k.upper() == ref_up), None)
    if not matched_key:
        pending_refs = [k for k, v in payments.items() if v["status"] == "pending"]
        hint = (
            "\n\n**Active Payments:** " + ", ".join(f"`{r}`" for r in pending_refs[:10])
            if pending_refs else ""
        )
        return await interaction.response.send_message(
            f"Payment `{ref_up}` Not Found.{hint}", ephemeral=True
        )

    p = payments[matched_key]
    if p["status"] != "pending":
        return await interaction.response.send_message(
            f"Payment `{matched_key}` Is Already **{p['status'].upper()}**.", ephemeral=True
        )

    await _payment_confirm(interaction.guild_id, matched_key, "MANUAL")
    await _notify_payment_confirmed(interaction.guild_id, matched_key)
    await interaction.response.send_message(
        f"Payment `{matched_key}` Confirmed Manually. ✅", ephemeral=True
    )

@payment_grp.command(name="cancel", description="Cancel A Pending Payment (Owner Only)")
@app_commands.describe(ref="Payment Reference Code To Cancel")
@is_owner()
async def payment_cancel(interaction: discord.Interaction, ref: str):
    d = _gdata(interaction.guild_id)
    p = d["payments"].get(ref.upper())
    if not p:
        return await interaction.response.send_message(
            f"Payment `{ref}` Not Found.", ephemeral=True
        )
    if p["status"] != "pending":
        return await interaction.response.send_message(
            f"Payment Is Already **{p['status'].upper()}**.", ephemeral=True
        )
    await _payment_expire(interaction.guild_id, ref.upper())
    await _notify_payment_expired(interaction.guild_id, ref.upper())
    await interaction.response.send_message(f"Payment `{ref}` Cancelled.", ephemeral=True)

@payment_grp.command(name="list", description="List All Payments (Owner Only)")
@app_commands.describe(status="Filter By Status")
@app_commands.choices(status=[
    app_commands.Choice(name="All",       value="all"),
    app_commands.Choice(name="Pending",   value="pending"),
    app_commands.Choice(name="Confirmed", value="confirmed"),
    app_commands.Choice(name="Expired",   value="expired"),
    app_commands.Choice(name="Cancelled", value="cancelled"),
])
@is_owner()
async def payment_list(interaction: discord.Interaction, status: str = "all"):
    await interaction.response.defer(ephemeral=True)
    d        = _gdata(interaction.guild_id)
    payments = d["payments"]

    filtered = {
        ref: p for ref, p in payments.items()
        if status == "all" or p["status"] == status
    }

    if not filtered:
        return await interaction.response.send_message(
            f"No Payments Found With Status: `{status}`.", ephemeral=True
        )

    icon_map = {"pending": "⏳", "confirmed": "✅", "expired": "⏰", "cancelled": "❌"}
    rows     = []
    for ref, p in list(filtered.items())[-20:]:
        icon   = icon_map.get(p["status"], "❓")
        payer  = interaction.guild.get_member(p["user_id"])
        p_name = payer.display_name if payer else f"ID:{p['user_id']}"
        rows.append(f"{icon} `{ref}` — `{p['amount']:,}₫` — {p_name} — **{p['status']}**")

    total     = len(filtered)
    confirmed = sum(1 for p in filtered.values() if p["status"] == "confirmed")
    total_vnd = sum(p["amount"] for p in filtered.values() if p["status"] == "confirmed")

    await _v2_followup(interaction, [
        _container(
            _text(f"## 💳 Payment List — `{status.upper()}`"),
            _separator(),
            _text(
                f"**Total:** {total}  •  **Confirmed:** {confirmed}  •  **Revenue:** `{total_vnd:,} VND`\n\n"
                + "\n".join(rows)
            ),
        )
    ])

@payment_grp.command(
    name="announce_all",
    description="Manually Send Daily Payment Summary To A Channel",
)
@app_commands.describe(
    channel="Channel To Send The Summary (Also Saves As Auto-Announce Channel)",
    note="Extra Note To Include (Optional)",
)
@is_owner()
async def payment_announce_all(
    interaction: discord.Interaction,
    channel:     discord.TextChannel,
    note:        Optional[str] = None,
):
    await interaction.response.defer(ephemeral=True, thinking=True)
    d = _gdata(interaction.guild_id)
    d["pay_announce_channel"] = channel.id
    await _db_save_guild(interaction.guild_id)

    await _send_daily_summary(
        interaction.guild_id, channel.id, note=note, actor=str(interaction.user)
    )
    await interaction.followup.send(
        f"Summary Sent To {channel.mention}.\n"
        "-# This Channel Is Now Set As The Daily 00:00 Auto-Announce Channel.",
        ephemeral=True,
    )

@payment_grp.command(name="info", description="Show Current Payment System Configuration")
@is_owner()
async def payment_info(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    d = _gdata(interaction.guild_id)
    if not d.get("pay_bank_id"):
        return await interaction.response.send_message(
            "Payment System Not Configured. Run `/payment setup` First.", ephemeral=True
        )

    log_ch    = interaction.guild.get_channel(d.get("pay_log_channel") or 0)
    conf_role = interaction.guild.get_role(d.get("pay_confirm_role") or 0)
    timeout_m = d.get("pay_timeout", 600) // 60
    pending   = sum(1 for p in d["payments"].values() if p["status"] == "pending")
    confirmed = sum(1 for p in d["payments"].values() if p["status"] == "confirmed")
    revenue   = sum(p["amount"] for p in d["payments"].values() if p["status"] == "confirmed")

    await _v2_followup(interaction, [
        _container(
            _text("## 🏦 Payment System Info"),
            _separator(),
            _text(
                f"**Bank:** `{d['pay_bank_id']}`\n"
                f"**Account No:** `{d['pay_account_no']}`\n"
                f"**Account Name:** `{d['pay_account_name']}`\n"
                f"**Log Channel:** {log_ch.mention if log_ch else '`Not Set`'}\n"
                f"**Ping Role:** {conf_role.mention if conf_role else '`None`'}\n"
                f"**Timeout:** `{timeout_m} Minutes`\n"
                f"**Casso Key:** `{'Configured ✅' if d.get('pay_casso_key') else 'Not Set ❌'}`"
            ),
            _separator(),
            _text(
                f"**Stats:**\n"
                f"> Pending: `{pending}`\n"
                f"> Confirmed: `{confirmed}`\n"
                f"> Total Revenue: `{revenue:,} VND`"
            ),
        )
    ])

bot.tree.add_command(payment_grp)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║               COMPONENT INTERACTION — PAYMENT CANCEL BUTTON                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = (interaction.data or {}).get("custom_id", "")
    if not custom_id.startswith("payment:cancel:"):
        return

    ref      = custom_id[len("payment:cancel:"):].upper()
    guild_id = interaction.guild_id
    if not guild_id:
        return await interaction.response.send_message("Guild Not Found.", ephemeral=True)

    p = _payment_get(guild_id, ref)
    if not p:
        return await interaction.response.send_message(
            f"Payment `{ref}` Not Found.", ephemeral=True
        )
    if p["status"] != "pending":
        return await interaction.response.send_message(
            f"Payment Is Already **{p['status'].upper()}**.", ephemeral=True
        )
    if p["user_id"] != interaction.user.id and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "Only The Payment Owner Can Cancel This.", ephemeral=True
        )

    await _payment_expire(guild_id, ref)
    await interaction.response.defer()

    await _v2_edit_msg(p["channel_id"], p["message_id"], [
        _container(
            _text("## ❌ Payment Cancelled"),
            _separator(),
            _text(
                f"**Reference:** `{ref}`\n"
                f"**Amount:** `{p['amount']:,} VND`\n"
                f"**Status:** ❌ Cancelled\n"
                f"-# Cancelled By {interaction.user.mention}  —  This Message Will Be Deleted In 5 Seconds."
            ),
        )
    ])
    await asyncio.sleep(5)
    try:
        url     = f"https://discord.com/api/v10/channels/{p['channel_id']}/messages/{p['message_id']}"
        headers = {"Authorization": f"Bot {TOKEN}"}
        async with aiohttp.ClientSession() as s:
            async with s.delete(url, headers=headers) as r:
                if r.status not in (200, 204):
                    log.warning("Could Not Delete Cancelled Payment Message: %s", r.status)
    except Exception as e:
        log.warning("Could Not Delete Cancelled Payment Message: %s", e)

    log.info("Payment %s Cancelled By %s", ref, interaction.user)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            ERROR HANDLER                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "You Do Not Have Permission To Use This Command."
    elif isinstance(error, app_commands.CheckFailure):
        msg = "Access Denied. You Are Not Authorized To Use This Command."
    else:
        msg = "An Error Occurred. Please Try Again."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                          PREFIX COMMANDS                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@bot.command(name="sync")
async def cmd_sync(ctx: commands.Context):
    if ctx.author.id != OWNER_ID:
        return await ctx.reply("Access Denied. Only The Bot Owner Can Use This Command.")
    msg    = await ctx.reply("Syncing Commands...")
    synced = await bot.tree.sync()
    await msg.edit(content=f"Synced **{len(synced)}** Slash Commands Successfully.")
    log.info("!sync Called By %s — %d Commands Synced", ctx.author, len(synced))

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            SLASH COMMANDS                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@bot.tree.command(name="ping", description="Check Bot Latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    latency_ms = round(bot.latency * 1000)
    ts = int(datetime.now(timezone.utc).timestamp())
    await _v2_followup(interaction, [
        _container(
            _text("## 🏓 Pong!"),
            _separator(),
            _text(f"**Latency:** `{latency_ms}ms`"),
            _separator(),
            _text(f"-# <t:{ts}:F>"),
        )
    ], ephemeral=False)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        EVENT — MEMBER LEAVE (on_member_remove)              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    d     = _gdata(guild.id)

    lch = guild.get_channel(d.get("leave_channel") or 0)
    if not lch:
        return

    ts         = int(datetime.now(timezone.utc).timestamp())
    avatar_url = member.display_avatar.with_size(256).url
    joined_ts  = int(member.joined_at.timestamp()) if member.joined_at else ts

    await _v2_send(lch, [  # type: ignore
        _container(
            _text(f"## 🚪 Goodbye From **{guild.name}**!"),
            _separator(),
            _section(
                f"**{member.mention} Has Left The Server.**\n"
                f"> Joined: <t:{joined_ts}:R>\n"
                f"> We Now Have `{guild.member_count}` Members.",
                avatar_url,
            ),
            _separator(),
            _text(f"-# <t:{ts}:F>"),
        )
    ])
    log.info("Leave Message Sent For %s In '%s'", member, guild.name)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                       /leave setup COMMAND                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

leave_grp = app_commands.Group(
    name="leave",
    description="Leave Message System",
    default_permissions=discord.Permissions(0),
)

@leave_grp.command(name="setup", description="Configure The Leave Message System")
@app_commands.describe(channel="Channel To Send Leave Messages In")
@is_owner()
async def leave_setup(
    interaction: discord.Interaction,
    channel:     discord.TextChannel,
):
    await interaction.response.defer(ephemeral=True)
    d = _gdata(interaction.guild_id)
    d["leave_channel"] = channel.id
    await _db_save_guild(interaction.guild_id)

    await _v2_followup(interaction, [
        _container(
            _text("## Leave System Configured"),
            _separator(),
            _text(
                f"**Leave Channel:** {channel.mention}\n\n"
                "Members Will Now Receive A Goodbye Message When They Leave."
            ),
        )
    ])
    log.info("Leave Setup By %s In '%s'", interaction.user, interaction.guild.name)

bot.tree.add_command(leave_grp)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                       /invites COMMANDS                                     ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  /invites setup   — Configure invite tracking channel                       ║
# ║  /invites check   — Check how many people a user has invited                ║
# ║  /invites top     — Show invite leaderboard                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

invites_grp = app_commands.Group(
    name="invites",
    description="Invite Tracking System",
    default_permissions=discord.Permissions(0),
)

@invites_grp.command(name="setup", description="Configure The Invite Tracking Channel")
@app_commands.describe(channel="Channel To Send Invite Notifications In")
@is_owner()
async def invites_setup(
    interaction: discord.Interaction,
    channel:     discord.TextChannel,
):
    await interaction.response.defer(ephemeral=True)
    d = _gdata(interaction.guild_id)
    d["invites_channel"] = channel.id
    await _db_save_guild(interaction.guild_id)

    # Pre-cache current invites
    await _refresh_invite_cache(interaction.guild)

    await _v2_followup(interaction, [
        _container(
            _text("## 🔗 Invite Tracking Configured"),
            _separator(),
            _text(
                f"**Invites Channel:** {channel.mention}\n\n"
                "When A Member Joins, The Bot Will Detect Who Invited Them\n"
                "And Track Their Cumulative Invite Count In The Database."
            ),
        )
    ])
    log.info("Invites Setup By %s In '%s'", interaction.user, interaction.guild.name)

@invites_grp.command(name="check", description="Check How Many People A User Has Invited")
@app_commands.describe(user="Member To Check (Defaults To Yourself)")
async def invites_check(
    interaction: discord.Interaction,
    user:        Optional[discord.Member] = None,
):
    await interaction.response.defer(ephemeral=False)
    target = user or interaction.user
    count  = await _invite_get(interaction.guild_id, target.id)
    ts     = int(datetime.now(timezone.utc).timestamp())

    await _v2_followup(interaction, [
        _container(
            _text("## 🔗 Invite Stats"),
            _separator(),
            _section(
                f"**{target.mention}** Has Invited **{count}** Member(s)\n"
                f"-# Tracked Since Bot Joined / Invite Tracking Was Enabled",
                target.display_avatar.with_size(256).url,
            ),
            _separator(),
            _text(f"-# <t:{ts}:F>"),
        )
    ], ephemeral=False)

@invites_grp.command(name="top", description="Show The Invite Leaderboard")
async def invites_top(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    board = await _invite_leaderboard(interaction.guild_id, limit=10)
    ts    = int(datetime.now(timezone.utc).timestamp())

    if not board:
        return await _v2_followup(interaction, [
            _container(
                _text("## 🔗 Invite Leaderboard"),
                _separator(),
                _text("No Invite Data Found Yet. Data Is Collected When Members Join."),
            )
        ])

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    rows   = []
    for i, (uid, cnt) in enumerate(board):
        m      = interaction.guild.get_member(uid)
        name   = m.display_name if m else f"<@{uid}>"
        mention= m.mention       if m else f"<@{uid}>"
        rows.append(f"{medals[i]} **#{i+1}** {mention} — **{cnt}** Invite(s)")

    await _v2_followup(interaction, [
        _container(
            _text("## 🔗 Invite Leaderboard"),
            _separator(),
            _text("\n".join(rows)),
            _separator(),
            _text(f"-# <t:{ts}:F>"),
        )
    ], ephemeral=False)

bot.tree.add_command(invites_grp)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                             ENTRY POINT                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    log.info("Starting Bot  |  Owner ID: %d", OWNER_ID)
    bot.run(TOKEN, log_handler=None)
