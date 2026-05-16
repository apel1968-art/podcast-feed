# -*- coding: utf-8 -*-
"""
cross_post.py — Publie un épisode sur Twitter/X et Bluesky.
Usage: python cross_post.py <path/to/episode.json>

Variables d'environnement requises (GitHub Secrets) :
  BLUESKY_HANDLE          ex: cequontecache.bsky.social
  BLUESKY_APP_PASSWORD    mot de passe d'application Bluesky
  TWITTER_API_KEY         OAuth 1.0a consumer key
  TWITTER_API_SECRET      OAuth 1.0a consumer secret
  TWITTER_ACCESS_TOKEN    OAuth 1.0a access token
  TWITTER_ACCESS_SECRET   OAuth 1.0a access token secret
"""

import base64
import hashlib
import hmac
import json
import os
import random
import string
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)


# ─── TEMPLATES DE POST PAR LANGUE ────────────────────────────────────────────

TEMPLATES = {
    "fr": {
        "hashtags": "#CeQuOnTeCache #Podcast #HistoireSecrète #CIA #Documentaire",
        "prefix": "🎙️ Nouvel épisode — Ép. {num} : {title}",
        "suffix": "▶️ YouTube : {youtube}",
    },
    "en": {
        "hashtags": "#TheTruthTheyHide #Podcast #SecretHistory #CIA #Documentary",
        "prefix": "🎙️ New episode — Ep. {num}: {title}",
        "suffix": "▶️ YouTube: {youtube}",
    },
    "es": {
        "hashtags": "#LoQueTeOcultan #Podcast #HistoriaSecreta #CIA #Documental",
        "prefix": "🎙️ Nuevo episodio — Ep. {num}: {title}",
        "suffix": "▶️ YouTube: {youtube}",
    },
}


def build_text(ep: dict, max_len: int = 280) -> str:
    lang = ep.get("lang", "fr")
    tpl  = TEMPLATES.get(lang, TEMPLATES["fr"])
    num  = ep.get("episode_number", "?")
    title   = ep.get("title", "")
    youtube = ep.get("youtube_url", "")

    text = "\n\n".join([
        tpl["prefix"].format(num=num, title=title),
        tpl["hashtags"],
        tpl["suffix"].format(youtube=youtube),
    ])
    return text[:max_len]


# ─── BLUESKY ─────────────────────────────────────────────────────────────────

def post_bluesky(text: str, handle: str, app_password: str) -> bool:
    base = "https://bsky.social/xrpc"

    resp = requests.post(
        f"{base}/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  Bluesky auth FAIL ({resp.status_code}): {resp.text[:200]}")
        return False

    data   = resp.json()
    token  = data["accessJwt"]
    did    = data["did"]
    now    = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

    resp = requests.post(
        f"{base}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text[:300],
                "createdAt": now,
            },
        },
        timeout=30,
    )
    if resp.status_code == 200:
        print(f"  Bluesky OK → {resp.json().get('uri','')}")
        return True
    print(f"  Bluesky post FAIL ({resp.status_code}): {resp.text[:200]}")
    return False


# ─── TWITTER / X ─────────────────────────────────────────────────────────────

def _oauth1_header(method: str, url: str, api_key: str, api_secret: str,
                   token: str, token_secret: str) -> str:
    nonce = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    ts    = str(int(time.time()))

    params = {
        "oauth_consumer_key":     api_key,
        "oauth_nonce":            nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        ts,
        "oauth_token":            token,
        "oauth_version":          "1.0",
    }

    encoded_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(params.items())
    )
    base_str = (
        urllib.parse.quote(method, safe="") + "&"
        + urllib.parse.quote(url, safe="") + "&"
        + urllib.parse.quote(encoded_params, safe="")
    )
    signing_key = (
        urllib.parse.quote(api_secret, safe="") + "&"
        + urllib.parse.quote(token_secret, safe="")
    )
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()

    params["oauth_signature"] = sig
    return "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(str(v), safe="")}"'
        for k, v in sorted(params.items())
    )


def post_twitter(text: str, api_key: str, api_secret: str,
                 access_token: str, access_secret: str) -> bool:
    url  = "https://api.twitter.com/2/tweets"
    auth = _oauth1_header("POST", url, api_key, api_secret, access_token, access_secret)

    resp = requests.post(
        url,
        data=json.dumps({"text": text[:280]}),
        headers={
            "Authorization": auth,
            "Content-Type":  "application/json",
        },
        timeout=30,
    )
    if resp.status_code in (200, 201):
        tweet_id = resp.json().get("data", {}).get("id", "")
        print(f"  Twitter/X OK → https://x.com/i/status/{tweet_id}")
        return True
    print(f"  Twitter/X FAIL ({resp.status_code}): {resp.text[:200]}")
    return False


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python cross_post.py <episode.json>")
        sys.exit(1)

    ep_path = sys.argv[1]
    with open(ep_path, encoding="utf-8") as f:
        ep = json.load(f)

    lang  = ep.get("lang", "fr")
    title = ep.get("title", "?")
    num   = ep.get("episode_number", "?")
    print(f"Cross-posting [{lang.upper()}] E{num:02} — {title}")

    text = build_text(ep)
    print(f"  Texte ({len(text)} chars):\n  {text[:120]}…\n")

    # ── Bluesky ──────────────────────────────────────────────────────────────
    bsky_handle = os.environ.get("BLUESKY_HANDLE", "")
    bsky_pass   = os.environ.get("BLUESKY_APP_PASSWORD", "")
    if bsky_handle and bsky_pass:
        post_bluesky(text, bsky_handle, bsky_pass)
    else:
        print("  Bluesky : ignoré (pas de credentials)")

    # ── Twitter / X ──────────────────────────────────────────────────────────
    tw_key    = os.environ.get("TWITTER_API_KEY", "")
    tw_secret = os.environ.get("TWITTER_API_SECRET", "")
    tw_token  = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    tw_tsec   = os.environ.get("TWITTER_ACCESS_SECRET", "")
    if tw_key and tw_secret and tw_token and tw_tsec:
        post_twitter(text, tw_key, tw_secret, tw_token, tw_tsec)
    else:
        print("  Twitter/X : ignoré (pas de credentials)")


if __name__ == "__main__":
    main()
