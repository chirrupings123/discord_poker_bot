<div align="center">
  <h1>🃏 Discord Poker Bot</h1>
  <p>A production-ready Discord bot for playing No-Limit Texas Hold'em Poker<br>with persistent virtual currency (no real-world value).</p>
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/postgresql-16%2B-blue" alt="PostgreSQL 16+">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
    <img src="https://img.shields.io/badge/tests-30%2F30-passing-brightgreen" alt="Tests Passing">
  </p>
</div>

---

## 📋 Features

- **Full Texas Hold'em** — Pre-flop, flop, turn, river, showdown with correct hand evaluation
- **Persistent Economy** — Chip balances stored in PostgreSQL, survive bot restarts
- **Side Pots & All-Ins** — Correct handling of side pots, split pots, and all-in scenarios
- **Interactive UI** — Discord slash commands and buttons for betting actions
- **Statistics** — Track hands played/won, biggest pots, win rates, and more
- **Leaderboards** — Richest players, most hands won, biggest pot winners
- **Registration System** — One-time registration with starting chips, anti-abuse protections
- **Rebuy System** — Get more chips when you run out (7-day cooldown)
- **Docker Ready** — Easy deployment with Docker Compose

## 📁 Project Structure

```
discord_poker_bot/
├── bot.py                  # Main entry point
├── config.py               # Configuration (reads from .env)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose config
├── README.md               # This file
├── database/
│   ├── connection.py       # Database connection and session
│   ├── models.py           # SQLAlchemy ORM models
│   └── migrations.py       # Migration script
├── commands/
│   ├── registration.py     # /register, /balance, /profile
│   ├── poker.py            # /poker create, list, join, leave, start
│   ├── rebuy.py            # /rebuy
│   ├── stats.py            # /stats
│   └── leaderboard.py      # /leaderboard
├── poker/
│   ├── deck.py             # Card and Deck classes
│   ├── hand_evaluator.py   # Hand ranking and evaluation
│   ├── engine.py           # Core poker game logic
│   └── game_manager.py     # Active table management
├── services/
│   ├── user_service.py     # User registration, balance, stats
│   └── poker_service.py    # Database operations for tables/games
├── views/
│   └── poker_views.py      # Discord UI components (buttons, embeds)
└── tests/
    ├── test_hand_evaluator.py  # Hand ranking tests
    └── test_poker.py           # Poker engine tests
```

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.10+
- PostgreSQL 14+

### 1. Set Up PostgreSQL

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

Create the database:
```bash
sudo -u postgres psql
```

```sql
CREATE USER poker_user WITH PASSWORD 'poker_password';
CREATE DATABASE poker_bot OWNER poker_user;
GRANT ALL PRIVILEGES ON DATABASE poker_bot TO poker_user;
\q
```

### 2. Configure the Bot

```bash
git clone <your-repo-url>
cd discord_poker_bot

cp .env.example .env
# Edit .env with your Discord token, app ID, and guild ID
```

### 3. Install & Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m database.migrations
python bot.py
```

## 🐳 Docker Deployment (Recommended for VPS)

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in
```

### 2. Launch

```bash
cp .env.example .env
# Edit .env with your values (use "db" as database host, not "localhost")
docker compose up -d
docker compose logs -f bot
```

## 📖 Commands

| Command | Description |
|---------|-------------|
| `/register` | Register for poker (get 10,000 chips) |
| `/balance` | Check your chip balance |
| `/profile` | View your poker profile |
| `/stats` | View detailed statistics |
| `/leaderboard category:balance` | Richest players |
| `/leaderboard category:hands_won` | Most hands won |
| `/leaderboard category:biggest_pot` | Biggest pot winners |
| `/poker create buyin:1000` | Create a new poker table |
| `/poker list` | List active tables |
| `/poker join table_id:1` | Join a table |
| `/poker leave` | Leave your current table |
| `/poker start` | Start the game (host only) |
| `/rebuy` | Request a rebuy (when balance is 0) |

## 🧪 Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

All 30 tests should pass.

## 🛡️ Anti-Abuse Features

- Duplicate registration prevention
- Minimum account age check (30 days, configurable)
- Rebuy cooldown (7 days, configurable)
- Chip dumping detection
- Negative balance protection
- Full transaction audit log

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

## 📄 License

This project is for educational and entertainment purposes only. The virtual currency has no real-world value and cannot be exchanged for money.
