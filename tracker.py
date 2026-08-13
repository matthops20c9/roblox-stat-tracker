import argparse
import sys
import time
from pathlib import Path

from roblox_tracker.db import init_db, track_place, get_tracked_places, save_snapshot, get_stats_history, remove_tracked_place
from roblox_tracker.roblox import fetch_place_details, fetch_universe_stats

DB_PATH = Path.home() / ".roblox_tracker.db"

def get_sparkline(data):
    """Generates a small Unicode bar chart representing numerical trends."""
    if not data:
        return ""
    if len(data) == 1:
        return "▅"
    low = min(data)
    high = max(data)
    span = high - low
    if span == 0:
        return "▄" * len(data)
    ticks = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    out = []
    for v in data:
        idx = int(((v - low) / span) * (len(ticks) - 1))
        out.append(ticks[idx])
    return "".join(out)

def render_dashboard():
    places = get_tracked_places(DB_PATH)
    if not places:
        print("No places are currently tracked. Add one with 'add <place_id>'")
        return
    
    print(f"\n{'Game Name':<30} | {'Active':<8} | {'History Sparkline':<15} | {'Visits':<12}")
    print("-" * 75)
    
    for p in places:
        # Limit to the last 15 recording snapshots to keep sparkline readable
        # TODO: support custom timeline granularities instead of strict FIFO snapshots
        history = get_stats_history(DB_PATH, p["universe_id"], limit=15)
        
        active_history = [row["active_players"] for row in history]
        latest_active = active_history[-1] if active_history else 0
        latest_visits = history[-1]["visits"] if history else 0
        
        spark = get_sparkline(active_history)
        spark_padded = f"{spark:<15}"[-15:]
        
        # Keep terminal columns clean and aligned
        name_trimmed = p["name"][:28] + ".." if len(p["name"]) > 30 else p["name"]
        print(f"{name_trimmed:<30} | {latest_active:<8} | {spark_padded} | {latest_visits:<12,}")

def main():
    init_db(DB_PATH)
    
    parser = argparse.ArgumentParser(
        description="Track Roblox universe stats over time."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    add_parser = subparsers.add_parser("add", help="Track a new place ID")
    add_parser.add_argument("place_id", type=int, help="Roblox Place ID")
    
    remove_parser = subparsers.add_parser("remove", help="Stop tracking a place ID")
    remove_parser.add_argument("place_id", type=int, help="Roblox Place ID")
    
    subparsers.add_parser("list", help="List all tracked places")
    subparsers.add_parser("update", help="Fetch and save latest stats for all tracked places")
    subparsers.add_parser("dash", help="Show terminal dashboard with visual sparklines")
    
    monitor_parser = subparsers.add_parser("monitor", help="Continually update and display stats")
    monitor_parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between updates")
    
    args = parser.parse_args()
    
    if args.command == "add":
        try:
            details = fetch_place_details(args.place_id)
            # print(f"DEBUG: resolved details -> {details}")
            universe_id = details["universeId"]
            name = details["name"]
            
            track_place(DB_PATH, args.place_id, universe_id, name)
            print(f"Successfully started tracking '{name}' (Universe: {universe_id})")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ConnectionError as e:
            print(f"Network error trying to resolve place ID: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif args.command == "remove":
        remove_tracked_place(DB_PATH, args.place_id)
        print(f"Stopped tracking place ID {args.place_id}")
            
    elif args.command == "list":
        places = get_tracked_places(DB_PATH)
        if not places:
            print("No places are currently tracked. Add one with 'add <place_id>'")
            return
        for p in places:
            print(f"[{p['place_id']}] {p['name']} (Universe: {p['universe_id']})")
            
    elif args.command == "update":
        places = get_tracked_places(DB_PATH)
        if not places:
            print("No places to update.")
            return
        for p in places:
            try:
                stats = fetch_universe_stats(p["universe_id"])
                save_snapshot(
                    DB_PATH, 
                    p["universe_id"],
                    stats["activePlayers"], 
                    stats["visits"], 
                    stats["upvotes"], 
                    stats["downvotes"]
                )
                print(f"Updated {p['name']}: {stats['activePlayers']} active players")
            except (ConnectionError, ValueError) as e:
                print(f"Failed to update {p['name']}: {e}", file=sys.stderr)
                
    elif args.command == "dash":
        render_dashboard()
        
    elif args.command == "monitor":
        print(f"Starting stats monitor loop. Refreshing every {args.interval} seconds. Press Ctrl+C to stop.")
        try:
            while True:
                places = get_tracked_places(DB_PATH)
                if not places:
                    print("No tracked places. Add some using 'add' command first.")
                    break
                
                for p in places:
                    try:
                        stats = fetch_universe_stats(p["universe_id"])
                        save_snapshot(
                            DB_PATH, 
                            p["universe_id"],
                            stats["activePlayers"], 
                            stats["visits"], 
                            stats["upvotes"], 
                            stats["downvotes"]
                        )
                    except (ConnectionError, ValueError):
                        # Skip individual update failures during loop to keep loop alive overnight
                        pass
                
                render_dashboard()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped monitor loop.")

if __name__ == "__main__":
    main()
