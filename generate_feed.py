# -*- coding: utf-8 -*-
"""
generate_feed.py — Génère feed_fr.xml / feed_en.xml / feed_es.xml
depuis les fichiers JSON dans episodes/{lang}/*.json
et les métadonnées de podcast_meta.json.

Usage: python generate_feed.py
"""

import json
import os
import glob
from datetime import datetime, timezone

BASE_URL     = "https://apel1968-art.github.io/podcast-feed"
META_FILE    = "podcast_meta.json"
EPISODES_DIR = "episodes"
LANGS        = ["fr", "en", "es"]


def fmt_rfc2822(iso_str: str) -> str:
    """Convertit une date ISO 8601 en RFC 2822 pour RSS."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")


def fmt_duration(seconds: int) -> str:
    h, r = divmod(int(seconds), 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"


def esc(text: str) -> str:
    """Échapper les caractères XML."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def load_episodes(lang: str) -> list:
    pattern = os.path.join(EPISODES_DIR, lang, "*.json")
    episodes = []
    for path in glob.glob(pattern):
        try:
            with open(path, encoding="utf-8") as f:
                ep = json.load(f)
            ep["_path"] = path
            episodes.append(ep)
        except Exception as e:
            print(f"  ⚠️  Erreur lecture {path}: {e}")
    episodes.sort(key=lambda e: e.get("episode_number", 999))
    return episodes


def build_item(ep: dict) -> str:
    num      = ep.get("episode_number", 0)
    title    = esc(ep.get("title", f"Épisode {num}"))
    desc     = esc(ep.get("description", ""))
    pub      = fmt_rfc2822(ep.get("published_at", ""))
    audio    = ep.get("audio_url", "")
    size     = ep.get("audio_size_bytes", 0)
    dur      = fmt_duration(ep.get("duration_seconds", 0))
    guid     = esc(ep.get("guid", audio))
    img      = ep.get("image_url", "")
    keywords = ", ".join(ep.get("keywords", []))
    season   = ep.get("season", 1)

    img_tag = f'\n      <itunes:image href="{esc(img)}"/>' if img else ""

    return f"""
    <item>
      <title>{title}</title>
      <description>{desc}</description>
      <pubDate>{pub}</pubDate>
      <enclosure url="{esc(audio)}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="false">{guid}</guid>
      <itunes:duration>{dur}</itunes:duration>
      <itunes:episode>{num}</itunes:episode>
      <itunes:season>{season}</itunes:season>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:keywords>{esc(keywords)}</itunes:keywords>{img_tag}
    </item>"""


def build_feed(lang: str, meta: dict, episodes: list) -> str:
    m = meta[lang]
    title    = esc(m["title"])
    desc     = esc(m["description"])
    author   = esc(m["author"])
    email    = esc(m["email"])
    language = m["language"]
    category = esc(m["category"])
    sub      = esc(m.get("subcategory", ""))
    explicit = m.get("explicit", "false")
    image    = esc(m["image_url"])
    link     = esc(m["link"])
    feed_url = esc(m["feed_url"])
    copyright_ = esc(m.get("copyright", ""))

    items = "".join(build_item(ep) for ep in reversed(episodes))

    sub_tag = f'\n    <itunes:category text="{sub}"/>' if sub else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:atom="http://www.w3.org/2005/Atom">

  <channel>
    <title>{title}</title>
    <link>{link}</link>
    <atom:link href="{feed_url}" rel="self" type="application/rss+xml"/>
    <language>{language}</language>
    <description>{desc}</description>
    <copyright>{copyright_}</copyright>
    <itunes:author>{author}</itunes:author>
    <itunes:owner>
      <itunes:name>{author}</itunes:name>
      <itunes:email>{email}</itunes:email>
    </itunes:owner>
    <itunes:category text="{category}">{sub_tag}
    </itunes:category>
    <itunes:image href="{image}"/>
    <image>
      <url>{image}</url>
      <title>{title}</title>
      <link>{link}</link>
    </image>
    <itunes:explicit>{explicit}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{items}
  </channel>
</rss>
"""


def main():
    import sys, shutil
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with open(META_FILE, encoding="utf-8") as f:
        meta = json.load(f)

    total = 0
    for lang in LANGS:
        episodes = load_episodes(lang)
        feed_xml = build_feed(lang, meta, episodes)
        out_file = f"feed_{lang}.xml"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(feed_xml)
        print(f"[OK] {out_file} -- {len(episodes)} episode(s)")
        for ep in episodes:
            n = ep.get("episode_number", "?")
            t = ep.get("title", "")
            print(f"     E{n:02} {t}")
        total += len(episodes)

    shutil.copy("feed_fr.xml", "feed.xml")
    print(f"\n[OK] feed.xml -> copie de feed_fr.xml")
    print(f"Total : {total} episode(s) sur {len(LANGS)} langues")


if __name__ == "__main__":
    main()
