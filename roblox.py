import httpx

def resolve_place_to_universe(place_id: int) -> int:
    """Translates a public Roblox Place ID into its internal Universe ID."""
    url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}"
    headers = {"User-Agent": "RobloxStatsTracker/1.0"}
    
    response = httpx.get(url, headers=headers, timeout=12.0)
    response.raise_for_status()
    data = response.json()
    
    if not data or not isinstance(data, list):
        raise ValueError(f"Invalid API response format for place ID {place_id}")
        
    # Roblox API returns empty list if game doesn't exist
    if len(data) == 0:
        raise ValueError(f"No game found with Place ID {place_id}")
        
    universe_id = data[0].get("universeId")
    if not universe_id:
        raise ValueError(f"Could not extract universeId for Place ID {place_id}")
        
    return universe_id


def get_universe_metrics(universe_id: int) -> dict:
    headers = {"User-Agent": "RobloxStatsTracker/1.0"}
    
    # 1. Fetch core stats (active players, visits)
    info_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
    info_resp = httpx.get(info_url, headers=headers, timeout=12.0)
    info_resp.raise_for_status()
    info_data = info_resp.json()
    
    if not info_data or "data" not in info_data or len(info_data["data"]) == 0:
        raise ValueError(f"Universe {universe_id} not found or details are private")
        
    game_info = info_data["data"][0]
    # print(f"Raw game response: {game_info}")
    
    # 2. Fetch voting/rating statistics
    votes_url = f"https://games.roblox.com/v1/games/{universe_id}/votes"
    votes_resp = httpx.get(votes_url, headers=headers, timeout=12.0)
    votes_resp.raise_for_status()
    votes_data = votes_resp.json()
    
    # TODO: Handle unrated or brand new games where votes can be null/zero gracefully
    up_votes = votes_data.get("upVotes", 0) or 0
    down_votes = votes_data.get("downVotes", 0) or 0
    totalVotes = up_votes + down_votes
    
    rating = 0.0
    if totalVotes > 0:
        rating = round((up_votes / totalVotes) * 100, 2)
        
    return {
        "universeId": universe_id,  
        "name": game_info.get("name", "Unknown Game"),
        "visits": game_info.get("visits", 0),
        "playing": game_info.get("playing", 0),
        "up_votes": up_votes,
        "down_votes": down_votes,
        "rating": rating
    }
