import requests
import json
import time
from datetime import datetime, timezone

# -----------------------------
# Load secrets safely
# -----------------------------
steam_key = None
dctoken = None

start = time.time()

with open(r"C:\Users\novab\Downloads\Py\Discord-Profile\.env", "r") as f:
    for line in f:
        if line.startswith("steam_web_api="):
            steam_key = line.split("=", 1)[1].strip()
        elif line.startswith("dc="):
            dctoken = line.split("=", 1)[1].strip()

if not steam_key or not dctoken:
    raise ValueError("Missing steam_web_api or dc token in .env")

steam_id = "76561199092231296"

# -----------------------------
# Session tracking (for timer)
# -----------------------------
session_start = {}

# -----------------------------
# Helper
# -----------------------------
def get(url, **params):
    r = requests.get(url, params={"key": steam_key, **params})
    r.raise_for_status()
    return r.json()

# -----------------------------
# Discord config
# -----------------------------
client_id = "1520433835857281146"
discord_id = "1079316234232922162"

url = f"https://discord.com/api/v9/applications/{client_id}/users/{discord_id}/identities/0/profile"

headers = {
    "Authorization": f"Bot {dctoken}",
    "Content-Type": "application/json"
}

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:
    try:
        # -----------------------------
        # Steam API calls
        # -----------------------------
        summary = get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            steamids=steam_id
        )

        owned = get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            steamid=steam_id,
            include_appinfo=True,
            include_played_free_games=True
        )

        recent = get(
            "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/",
            steamid=steam_id
        )

        badges = get(
            "https://api.steampowered.com/IPlayerService/GetBadges/v1/",
            steamid=steam_id
        )

        level = get(
            "https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/",
            steamid=steam_id
        )

        friends = get(
            "https://api.steampowered.com/ISteamUser/GetFriendList/v1/",
            steamid=steam_id,
            relationship="friend"
        )

        player = summary.get("response", {}).get("players", [{}])[0]

        name = player.get("personaname", "unknown")
        avatar = player.get("avatarfull", "")
        created = player.get("timecreated", 0)

        # -----------------------------
        # Profile age
        # -----------------------------
        if created:
            age_days = (datetime.now(timezone.utc).timestamp() - created) / 86400
            profile_age = int(age_days // 365)
        else:
            profile_age = "unknown"

        # -----------------------------
        # Games
        # -----------------------------
        games = owned.get("response", {}).get("games", [])
        games_owned = len(games)

        total_minutes = sum(g.get("playtime_forever", 0) for g in games)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        most_played = max(games, key=lambda x: x.get("playtime_forever", 0), default=None)
        most_played_name = most_played.get("name", "unknown") if most_played else "unknown"

        recent_games = recent.get("response", {}).get("games", [])
        last_played = recent_games[0].get("name", "unknown") if recent_games else "unknown"

        recent_hours = sum(g.get("playtime_2weeks", 0) for g in recent_games) / 60

        badge_count = len(badges.get("response", {}).get("badges", []))
        steam_level = level.get("response", {}).get("player_level", 0)

        friend_count = len(friends.get("friendslist", {}).get("friends", []))

        # -----------------------------
        # CURRENTLY PLAYING DETECTION
        # -----------------------------
        game_name = player.get("gameextrainfo")

        if game_name:
            if steam_id not in session_start:
                session_start[steam_id] = time.time()

            elapsed = int(time.time() - session_start[steam_id])
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60

            activity_text = f"Currently Playing: {game_name} for {h:02}:{m:02}:{s:02}"
        else:
            session_start.pop(steam_id, None)
            activity_text = f"Last Played: {last_played}"

        # -----------------------------
        # Payload rebuild each loop
        # -----------------------------
        payload = {
            "username": name,
            "data": {
                "dynamic": [
                    {"type": 1, "name": "user_name", "value": name},
                    {"type": 1, "name": "user_level", "value": f"Steam Level: {steam_level}"},
                    {"type": 1, "name": "user_mostplayed", "value": f"Most Played: {most_played_name}"},
                    {"type": 1, "name": "user_lastplayed", "value": activity_text},
                    {"type": 1, "name": "playtime_hours", "value": f"{hours:,}h {minutes}m"},
                    {"type": 1, "name": "games_owned", "value": str(games_owned)},
                    {"type": 1, "name": "recent_hours", "value": f"{recent_hours:.1f}"},
                    {"type": 1, "name": "friend_count", "value": str(friend_count)},
                    {"type": 1, "name": "badge_count", "value": str(badge_count)},
                    {"type": 1, "name": "profile_age", "value": f"{profile_age} Years"}
                ]
            }
        }

        if avatar:
            payload["data"]["dynamic"].append({
                "type": 3,
                "name": "profile_icon",
                "value": {"url": avatar}
            })

        # -----------------------------
        # Discord update
        # -----------------------------

        print(f"[ Timestamp: {round(time.time()-start)} ]: Syncing Stats!")

        response = requests.patch(url, headers=headers, json=payload)

        if not response.ok:
            print("Discord error:", response.status_code, response.text)
        else:
            print(f"[ Timestamp: {round(time.time()-start)} ]: Sync Successful")

    except Exception as e:
        print("Error:", e)

    time.sleep(20)