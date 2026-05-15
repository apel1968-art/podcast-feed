#!/usr/bin/env python3
"""
Générateur RSS automatique pour podcast GitHub Pages
Usage : python generate_feed.py
"""

import os
import re
from datetime import datetime, timezone

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
BASE_URL        = "https://apel1968-art.github.io/podcast-feed"
PODCAST_TITLE   = "Nom du Podcast"
PODCAST_DESC    = "Description de votre podcast — remplacez ce texte."
AUTHOR          = "apel1968-art"
EMAIL           = "votre@email.com"
LANGUAGE        = "fr-fr"
CATEGORY        = "Music"
EXPLICIT        = "false"
EPISODES_DIR    = "./episodes"
OUTPUT_FILE     = "./feed.xml"
# ──────────────────────────────────────────────────────────────────────────────

def format_duration(seconds):
    h, r = divmod(int(seconds), 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"

def slug_to_title(filename):
    name = filename.replace(".mp3", "")
    name = re.sub(r"^ep\d+[-_]?", "", name, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ").title()
    return name.strip() or filename.replace(".mp3", "")

def get_episode_number(filename):
    match = re.search(r"ep(\d+)", filename, re.IGNORECASE)
    return int(match.group(1)) if match else 999

def build_item(filename, index_from_end):
    path = os.path.join(EPISODES_DIR, filename)
    size = os.path.getsize(path)
    title = slug_to_title(filename)
    ep_num = get_episode_number(filename)
    url = f"{BASE_URL}/episodes/{filename}"

    # Essayer d'extraire la durée via mutagen (optionnel)
    duration = "00:00:00"
    try:
        from mutagen.mp3 import MP3
        audio = MP3(path)
        duration = format_duration(audio.info.length)
    except ImportError:
        pass  # mutagen pas installé — durée laissée à 00:00:00
    except Exception:
        pass

    # Date de publication : basée sur la date de modification du fichier
    mtime = os.path.getmtime(path)
    pub_date = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    return f"""
    <item>
      <title>Épisode {ep_num:02d} — {title}</title>
      <description>Épisode {ep_num:02d} du podcast {PODCAST_TITLE}.</description>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{url}" length="{size}" type="audio/mpeg"/>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:episode>{ep_num}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <guid isPermaLink="true">{url}</guid>
    </item>"""

def main():
    # Lister et trier les MP3
    if not os.path.isdir(EPISODES_DIR):
        print(f"⚠️  Dossier '{EPISODES_DIR}' introuvable — aucun épisode.")
        mp3_files = []
    else:
        mp3_files = sorted(
            [f for f in os.listdir(EPISODES_DIR) if f.lower().endswith(".mp3")],
            key=get_episode_number
        )

    if not mp3_files:
        print("ℹ️  Aucun fichier MP3 trouvé dans ./episodes/")

    items_xml = "".join(
        build_item(f, i) for i, f in enumerate(reversed(mp3_files))
    )

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:atom="http://www.w3.org/2005/Atom">

  <channel>
    <title>{PODCAST_TITLE}</title>
    <link>{BASE_URL}/</link>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>{LANGUAGE}</language>
    <description>{PODCAST_DESC}</description>
    <itunes:author>{AUTHOR}</itunes:author>
    <itunes:owner>
      <itunes:name>{AUTHOR}</itunes:name>
      <itunes:email>{EMAIL}</itunes:email>
    </itunes:owner>
    <itunes:category text="{CATEGORY}"/>
    <itunes:image href="{BASE_URL}/cover.jpg"/>
    <itunes:explicit>{EXPLICIT}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <image>
      <url>{BASE_URL}/cover.jpg</url>
      <title>{PODCAST_TITLE}</title>
      <link>{BASE_URL}/</link>
    </image>
{items_xml}
  </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(feed)

    print(f"✅ feed.xml généré — {len(mp3_files)} épisode(s)")
    for mp3 in mp3_files:
        print(f"   🎙️  {mp3}")

if __name__ == "__main__":
    main()
