# IMMA Championship Bot

A Telegram bot for managing CS2 (Counter-Strike 2) tournaments with player registration, team management, bracket generation, and match coordination.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your BOT_TOKEN, ADMIN_IDS, OWNER_ID

# Run the bot
python bot.py
```

## Project Structure

```
IMMA-bot/
├── bot.py              # Entry point, bot initialization, startup/shutdown
├── config.py           # Configuration class, tournament formats, maps, constants
├── database.py         # Async SQLite database layer (all DB operations)
├── keyboards.py        # Inline keyboards and Emoji class for UI
├── utils.py            # Validation, formatting, helper functions
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── handlers/           # Message and callback handlers
│   ├── __init__.py     # Router setup (setup_routers function)
│   ├── user.py         # User registration, profile, rating, admin panel
│   ├── teams.py        # Team creation, joining, management
│   ├── tournaments.py  # Tournament CRUD, registration, check-in
│   └── matches.py      # Match results, bracket view, lobby system
└── services/           # Business logic services
    ├── __init__.py     # Service exports
    ├── bracket.py      # Single elimination bracket generation
    ├── channel.py      # Channel posting and updates
    ├── notifications.py# User notifications
    └── scheduler.py    # APScheduler for reminders and auto check-in
```

## Tech Stack

- **Python 3.10+**
- **aiogram 3.x** - Telegram Bot API framework
- **aiosqlite** - Async SQLite database
- **APScheduler** - Background task scheduling
- **python-dotenv** - Environment configuration

## Architecture

### Database Layer (`database.py`)

Single `Database` class with async SQLite connection. All database operations are methods on the global `db` instance.

**Key tables:**
- `players` - Registered users (telegram_id, nickname, steam_link, contact, stats)
- `teams` - Teams with captain, format (2v2/5v5), invite code
- `team_members` - Team membership (team_id, player_id)
- `tournaments` - Tournament configuration (format, maps, prizes, dates, status)
- `tournament_players` / `tournament_teams` - Registration records
- `matches` - Match data (participants, scores, winner, status)
- `tournament_participant_status` - Participant status tracking for manual match system (ready/in_match/eliminated, wins counter)
- `lobby` - Player ready status during active tournaments
- `player_bans` - Ban records with expiration
- `admins` - Additional admin users (beyond config ADMIN_IDS)
- `channel_settings` - Linked Telegram channel for announcements
- `tournament_posts` - Published channel posts
- `bot_settings` - Key-value store for bot settings (e.g., prize_admins)

**Common patterns:**
```python
from database import db

# Get player by telegram ID
player = await db.get_player(telegram_id)

# Update with kwargs
await db.update_tournament(tournament_id, status="active", name="New Name")

# All methods return dict or list[dict]
tournaments = await db.get_tournaments_by_status("open")
```

### Handlers (`handlers/`)

Organized by domain. Each module creates a `Router` and registers handlers.

**Handler patterns:**
- Commands: `@router.message(Command("start"))`
- Callback queries: `@router.callback_query(F.data == "main_menu")`
- Regex callbacks: `@router.callback_query(F.data.regexp(r"^tournament_(\d+)$"))`
- FSM states: `@router.message(RegistrationStates.waiting_nickname)`

**State groups defined in handlers:**
- `RegistrationStates` - nickname, steam, contact
- `EditProfileStates` - profile editing
- `CreateTeamStates` - team creation
- `JoinTeamStates` - joining via invite code
- `MatchResultStates` - entering match scores
- `MatchLinkStates` - entering server links (queue-based system)
- `ManualMatchLinkStates` - entering server links (manual match system)
- `PrizeAdminsStates` - editing prize admin usernames

### Services (`services/`)

**BracketGenerator** - Creates single elimination bracket with bye distribution:
```python
from services.bracket import BracketGenerator

generator = BracketGenerator(tournament_id, participants, "player")
await generator.generate()  # Creates matches in DB
```

**NotificationService** - Sends messages to players:
```python
from services.notifications import NotificationService

service = NotificationService(bot)
await service.notify_tournament_start(tournament_id)
```

**ChannelService** - Publishes/updates tournament posts and results:
```python
from services.channel import get_channel_service

service = get_channel_service()
success, message = await service.publish_post(tournament_id)

# Publish results when tournament finishes (TOP-3, match history, prize admin contacts)
success, message = await service.publish_results(tournament_id)
```

**SchedulerService** - Automated reminders at 60/30/15 minutes before start:
```python
from services.scheduler import get_scheduler

scheduler = get_scheduler()
await scheduler.schedule_tournament_reminders(tournament_id)
```

### Keyboards (`keyboards.py`)

`Keyboards` class with static methods for all inline keyboards. `Emoji` class for consistent emoji usage.

```python
from keyboards import kb, Emoji

# Build keyboard
markup = kb.tournament_view(tournament, is_registered, can_register)

# Use emoji
text = f"{Emoji.TROPHY} Tournament Name"
```

### Configuration (`config.py`)

All configuration in `Config` class, loaded from environment variables:

- `BOT_TOKEN` - Telegram bot token
- `ADMIN_IDS` - Comma-separated admin telegram IDs
- `OWNER_ID` - Main owner ID
- `TIMEZONE` - APScheduler timezone (default: Europe/Moscow)
- `DATABASE_PATH` - SQLite database file

**Tournament formats:**
- `1v1` - Solo (1 player per slot)
- `2v2` - 2 players per team
- `5v5` - 5 players per team

**Maps:** de_mirage, de_inferno, de_nuke, de_overpass, de_vertigo, de_ancient, de_anubis, de_dust2

## Key Workflows

### Tournament Lifecycle

1. **Draft** - Created but not visible to players
2. **Open** - Registration open, players can join
3. **Check-in** (optional) - Players must confirm attendance
4. **Active** - Bracket generated, matches in progress
5. **Finished** - Winner determined

### Manual Match System (Primary)

The bot uses a **manual match system** where admin has full control over match pairings:

1. **Tournament starts** → All participants get status `ready` in `tournament_participant_status` table
2. **Admin creates match** → Selects 2 ready participants → Both become `in_match`
3. **Match completes** → Winner returns to `ready`, loser becomes `eliminated`
4. **Admin repeats** until 1 participant remains
5. **Finish tournament** → Shows final standings sorted by wins

**Participant statuses:**
- `ready` - Available for matches
- `in_match` - Currently playing
- `eliminated` - Lost and out of tournament

**Key callback patterns:**
- `mm_control_{tournament_id}` - Main management screen
- `mm_create_{tournament_id}` - Start creating match
- `mm_p1_{tournament_id}_{participant_id}` - Select first participant
- `mm_p2_{tournament_id}_{participant_id}` - Select second participant
- `mm_go_{tournament_id}_{p1_id}_{p2_id}` - Create match without link
- `mm_link_{tournament_id}_{p1_id}_{p2_id}` - Create match with server link
- `mm_active_{tournament_id}` - View active matches
- `mm_restore_{tournament_id}` - Restore eliminated participant

**Manual match workflow example:**
```python
# Create manual match (sets both participants to in_match)
match_id = await db.create_manual_match(tournament_id, p1_id, p2_id, "player", server_link)

# Complete match (winner → ready, loser → eliminated)
await db.complete_manual_match(match_id, winner_id, score1, score2)

# Cancel match (both return to ready)
await db.cancel_match(match_id)

# Restore eliminated participant
await db.restore_participant(tournament_id, participant_id, "player")
```

### Match Queue System (Legacy)

Alternative queue-based system (not currently used):
- Matches start with status `pending` (queued)
- Admin starts match -> status becomes `active`
- Admin enters result -> status becomes `completed`
- Winner advances to next round automatically
- `MAX_ACTIVE_MATCHES` config limits concurrent matches

### Lobby System

During active tournaments, players can mark themselves as "ready" or "away" in the lobby. Admins see who's ready before starting matches.

## Development Guidelines

### Adding New Handlers

1. Create handler functions in appropriate file under `handlers/`
2. Use `@router.callback_query(F.data.startswith("prefix_"))` for new callback patterns
3. For multi-step flows, define `StatesGroup` and use FSM

### Database Migrations

Migrations are handled in `database.py:_run_migrations()`. Add try/except blocks for new columns:

```python
try:
    await self.conn.execute("SELECT new_column FROM table LIMIT 1")
except Exception:
    await self.conn.execute("ALTER TABLE table ADD COLUMN new_column TYPE")
    await self.conn.commit()
```

### Adding New Services

1. Create service class in `services/`
2. Export in `services/__init__.py`
3. Initialize in `bot.py:on_startup()` if needed globally

### Callback Data Conventions

- Simple actions: `action_name` (e.g., `main_menu`, `register`)
- With ID: `action_id` (e.g., `tournament_123`, `team_45`)
- Admin actions: `admin_action_id` (e.g., `admin_t_open_123`)
- Manual matches: `mm_action_id` or `mm_action_id1_id2` (e.g., `mm_control_1`, `mm_go_1_2_3`)
- Complex: `action_subaction_id1_id2` (e.g., `match_set_1_16_14_1`)
- Prize admins: `admin_prize_admins`, `edit_prize_admins`, `clear_prize_admins`

### Text Formatting

- All bot messages use HTML parse mode
- Use `escape_html()` for user-provided content
- Format functions in `utils.py` for consistent display

## Common Tasks

### Bot Settings

The bot uses a key-value `bot_settings` table for configuration:

```python
# Get/set arbitrary settings
value = await db.get_setting("key_name")
await db.set_setting("key_name", "value")

# Prize admin contacts (shown in tournament results)
admins = await db.get_prize_admins()  # Returns list[str]
await db.set_prize_admins(["admin1", "admin2"])
```

Prize admins are configured via Admin Panel → Other → Prize Admins. They are displayed in channel results post with a warning not to trust other contacts.

### Check if user is admin
```python
if not await db.is_admin(callback.from_user.id):
    await callback.answer("Нет доступа!", show_alert=True)
    return
```

### Get tournament with parsed maps
```python
tournament = await db.get_tournament(tournament_id)
# tournament["maps"] is already a list (JSON parsed)
```

### Send notification to tournament participants
```python
if tournament["format"] == "1v1":
    players = await db.get_tournament_players(tournament_id)
    for p in players:
        await bot.send_message(p["telegram_id"], text, parse_mode="HTML")
else:
    teams = await db.get_tournament_teams(tournament_id)
    for team in teams:
        members = await db.get_team_members(team["id"])
        for m in members:
            await bot.send_message(m["telegram_id"], text, parse_mode="HTML")
```

### Advance winner in bracket
```python
async def advance_winner(match: dict, winner_id: int) -> None:
    next_match = await db.get_next_match_for_winner(
        match["tournament_id"],
        match["round"],
        match["match_number"]
    )
    if next_match:
        position = 1 if match["match_number"] % 2 == 1 else 2
        await db.update_match_participant(next_match["id"], position, winner_id)
```

## Language

The bot UI is in **Russian**. All user-facing strings are hardcoded in handlers and keyboards. Comments in code are also in Russian.

## Testing

No automated tests currently. Test manually:
1. Start bot with test token
2. Register as player
3. Create team (if testing 2v2/5v5)
4. Create tournament via `/admin`
5. Open registration, register participants
6. Start tournament, enter match results

## Environment Variables

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
OWNER_ID=123456789
TIMEZONE=Europe/Moscow
DATABASE_PATH=bot_database.db
```
