# Telegram Mini App — Турнирная платформа CS2

Полная инструкция для создания Telegram Mini App с нуля. Используй этот документ как промпт для AI или техническое задание.

---

## Содержание

1. [Описание проекта](#1-описание-проекта)
2. [Технологический стек](#2-технологический-стек)
3. [Архитектура](#3-архитектура)
4. [База данных](#4-база-данных)
5. [Backend API](#5-backend-api)
6. [Frontend](#6-frontend)
7. [Telegram интеграция](#7-telegram-интеграция)
8. [Функционал по ролям](#8-функционал-по-ролям)
9. [UI/UX требования](#9-uiux-требования)
10. [Деплой](#10-деплой)

---

## 1. Описание проекта

### Что это?

Telegram Mini App для организации турниров по CS2. Платформа позволяет:
- Игрокам регистрироваться и участвовать в турнирах
- Капитанам управлять командами
- Админам создавать турниры и управлять матчами
- Принимать оплату через Telegram Stars

### Форматы турниров

- **1v1** — соло игроки
- **2v2** — команды из 2 человек
- **5v5** — команды из 5 человек

### Система матчей

Ручная система управления:
1. Админ выбирает двух готовых участников
2. Создаёт матч с ссылкой на сервер и паролем
3. После игры вводит результат
4. Победитель возвращается в пул готовых, проигравший выбывает
5. Турнир завершается когда остаётся 1 участник

---

## 2. Технологический стек

### Backend

```
Python 3.11+
├── FastAPI — REST API фреймворк
├── SQLAlchemy — ORM для базы данных
├── Alembic — миграции БД
├── Pydantic — валидация данных
├── python-jose — JWT токены
├── aiogram 3.x — Telegram Bot API
├── Redis — кеширование и сессии
├── Celery — фоновые задачи
└── pytest — тестирование
```

### Frontend

```
React 18+ / Vue 3
├── TypeScript — типизация
├── Tailwind CSS — стилизация
├── @telegram-apps/sdk — Telegram WebApp SDK
├── TanStack Query — работа с API
├── Zustand / Pinia — состояние
├── React Router / Vue Router — маршрутизация
└── Vite — сборка
```

### База данных

```
PostgreSQL 15+ — основная БД
Redis — кеш, сессии, очереди
```

### Инфраструктура

```
Docker + Docker Compose
Nginx — reverse proxy
Certbot — SSL сертификаты
```

---

## 3. Архитектура

### Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram                                  │
│  ┌──────────────┐                    ┌──────────────────────┐   │
│  │  Mini App    │                    │    Bot (уведомления) │   │
│  │  (WebView)   │                    │                      │   │
│  └──────┬───────┘                    └──────────┬───────────┘   │
└─────────┼───────────────────────────────────────┼───────────────┘
          │ HTTPS                                 │ Bot API
          ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  FastAPI    │  │  WebSocket  │  │   Telegram Bot Service  │  │
│  │  REST API   │  │   Server    │  │   (aiogram)             │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                 │
│         └────────────────┼─────────────────────┘                 │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                           │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────┐  │  │
│  │  │ Tournament │ │   Match    │ │   Team     │ │ Player │  │  │
│  │  │  Service   │ │  Service   │ │  Service   │ │Service │  │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │                       ▼                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │ PostgreSQL  │  │    Redis    │  │   Celery    │        │  │
│  │  │   (data)    │  │   (cache)   │  │   (tasks)   │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Структура проекта

```
tournament-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Настройки
│   │   ├── database.py             # Подключение к БД
│   │   │
│   │   ├── models/                 # SQLAlchemy модели
│   │   │   ├── __init__.py
│   │   │   ├── player.py
│   │   │   ├── team.py
│   │   │   ├── tournament.py
│   │   │   ├── match.py
│   │   │   └── payment.py
│   │   │
│   │   ├── schemas/                # Pydantic схемы
│   │   │   ├── __init__.py
│   │   │   ├── player.py
│   │   │   ├── team.py
│   │   │   ├── tournament.py
│   │   │   └── match.py
│   │   │
│   │   ├── api/                    # API роуты
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Зависимости (auth)
│   │   │   ├── auth.py
│   │   │   ├── players.py
│   │   │   ├── teams.py
│   │   │   ├── tournaments.py
│   │   │   ├── matches.py
│   │   │   ├── admin.py
│   │   │   └── payments.py
│   │   │
│   │   ├── services/               # Бизнес-логика
│   │   │   ├── __init__.py
│   │   │   ├── player_service.py
│   │   │   ├── team_service.py
│   │   │   ├── tournament_service.py
│   │   │   ├── match_service.py
│   │   │   ├── notification_service.py
│   │   │   └── payment_service.py
│   │   │
│   │   ├── bot/                    # Telegram Bot
│   │   │   ├── __init__.py
│   │   │   ├── bot.py
│   │   │   └── handlers.py
│   │   │
│   │   └── utils/                  # Утилиты
│   │       ├── __init__.py
│   │       ├── telegram_auth.py
│   │       └── validators.py
│   │
│   ├── alembic/                    # Миграции
│   ├── tests/                      # Тесты
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── api/                    # API клиент
│   │   │   ├── client.ts
│   │   │   ├── auth.ts
│   │   │   ├── tournaments.ts
│   │   │   ├── teams.ts
│   │   │   └── matches.ts
│   │   │
│   │   ├── components/             # Компоненты
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   └── Spinner.tsx
│   │   │   ├── tournament/
│   │   │   │   ├── TournamentCard.tsx
│   │   │   │   ├── TournamentList.tsx
│   │   │   │   ├── TournamentDetails.tsx
│   │   │   │   └── MatchBracket.tsx
│   │   │   ├── team/
│   │   │   │   ├── TeamCard.tsx
│   │   │   │   ├── TeamList.tsx
│   │   │   │   └── TeamMembers.tsx
│   │   │   └── admin/
│   │   │       ├── MatchControl.tsx
│   │   │       ├── ParticipantList.tsx
│   │   │       └── ScoreInput.tsx
│   │   │
│   │   ├── pages/                  # Страницы
│   │   │   ├── Home.tsx
│   │   │   ├── Tournament.tsx
│   │   │   ├── Profile.tsx
│   │   │   ├── Teams.tsx
│   │   │   ├── Team.tsx
│   │   │   ├── Rating.tsx
│   │   │   ├── admin/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── TournamentManage.tsx
│   │   │   │   ├── MatchManage.tsx
│   │   │   │   └── Settings.tsx
│   │   │   └── Register.tsx
│   │   │
│   │   ├── hooks/                  # React хуки
│   │   │   ├── useTelegram.ts
│   │   │   ├── useAuth.ts
│   │   │   └── useWebSocket.ts
│   │   │
│   │   ├── store/                  # Состояние
│   │   │   ├── auth.ts
│   │   │   └── app.ts
│   │   │
│   │   ├── utils/                  # Утилиты
│   │   │   ├── formatters.ts
│   │   │   └── validators.ts
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

## 4. База данных

### ER-диаграмма

```
┌─────────────────┐       ┌─────────────────┐
│     players     │       │      teams      │
├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │
│ telegram_id     │◄──┐   │ name            │
│ username        │   │   │ captain_id      │──┐
│ nickname        │   │   │ format          │  │
│ steam_link      │   │   │ invite_code     │  │
│ contact         │   │   │ created_at      │  │
│ tournaments_won │   │   └─────────────────┘  │
│ tournaments_played    │                      │
│ is_banned       │   │   ┌─────────────────┐  │
│ created_at      │   │   │  team_members   │  │
└─────────────────┘   │   ├─────────────────┤  │
         ▲            │   │ id              │  │
         │            │   │ team_id         │◄─┘
         │            └───│ player_id       │
         │                │ joined_at       │
         │                └─────────────────┘
         │
┌────────┴────────┐       ┌─────────────────┐
│   tournaments   │       │     matches     │
├─────────────────┤       ├─────────────────┤
│ id              │◄──────│ tournament_id   │
│ name            │       │ id              │
│ format          │       │ participant1_id │
│ status          │       │ participant2_id │
│ max_participants│       │ participant_type│
│ start_time      │       │ winner_id       │
│ maps            │       │ score1          │
│ prizes          │       │ score2          │
│ entry_fee       │       │ server_link     │
│ checkin_required│       │ server_password │
│ created_at      │       │ status          │
└─────────────────┘       │ created_at      │
         │                └─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│tournament_players│      │ tournament_teams│
├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │
│ tournament_id   │       │ tournament_id   │
│ player_id       │       │ team_id         │
│ checked_in      │       │ checked_in      │
│ payment_id      │       │ payment_id      │
│ registered_at   │       │ registered_at   │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│participant_status│      │    payments     │
├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │
│ tournament_id   │       │ telegram_payment_id│
│ participant_id  │       │ player_id       │
│ participant_type│       │ tournament_id   │
│ status          │       │ amount          │
│ wins            │       │ status          │
│ losses          │       │ created_at      │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│     admins      │       │   settings      │
├─────────────────┤       ├─────────────────┤
│ id              │       │ key             │
│ telegram_id     │       │ value           │
│ added_by        │       └─────────────────┘
│ created_at      │
└─────────────────┘
```

### SQL схема

```sql
-- Игроки
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(32),
    nickname VARCHAR(20) NOT NULL,
    steam_link VARCHAR(200) NOT NULL,
    contact VARCHAR(100),
    tournaments_won INTEGER DEFAULT 0,
    tournaments_played INTEGER DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,
    ban_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Команды
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(30) NOT NULL,
    captain_id INTEGER REFERENCES players(id),
    format VARCHAR(10) NOT NULL, -- '2v2' или '5v5'
    invite_code VARCHAR(10) UNIQUE,
    invite_expires_at TIMESTAMP,
    tournaments_won INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Участники команд
CREATE TABLE team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    player_id INTEGER REFERENCES players(id),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, player_id)
);

-- Турниры
CREATE TABLE tournaments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    format VARCHAR(10) NOT NULL, -- '1v1', '2v2', '5v5'
    status VARCHAR(20) DEFAULT 'draft', -- draft, open, active, finished
    max_participants INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    maps JSONB DEFAULT '[]',
    prizes JSONB DEFAULT '{}', -- {"1": "Prize1", "2": "Prize2", "3": "Prize3"}
    entry_fee INTEGER DEFAULT 0, -- Telegram Stars
    checkin_required BOOLEAN DEFAULT FALSE,
    checkin_start_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Регистрации игроков на турниры
CREATE TABLE tournament_players (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    player_id INTEGER REFERENCES players(id),
    checked_in BOOLEAN DEFAULT FALSE,
    payment_id VARCHAR(100),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, player_id)
);

-- Регистрации команд на турниры
CREATE TABLE tournament_teams (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES teams(id),
    checked_in BOOLEAN DEFAULT FALSE,
    payment_id VARCHAR(100),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, team_id)
);

-- Статусы участников в турнире
CREATE TABLE participant_status (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    participant_id INTEGER NOT NULL,
    participant_type VARCHAR(10) NOT NULL, -- 'player' или 'team'
    status VARCHAR(20) DEFAULT 'ready', -- ready, in_match, eliminated
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    UNIQUE(tournament_id, participant_id, participant_type)
);

-- Матчи
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    participant1_id INTEGER NOT NULL,
    participant2_id INTEGER NOT NULL,
    participant_type VARCHAR(10) NOT NULL,
    winner_id INTEGER,
    score1 INTEGER,
    score2 INTEGER,
    server_link VARCHAR(500),
    server_password VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active', -- active, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Платежи
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    telegram_payment_id VARCHAR(100) UNIQUE,
    player_id INTEGER REFERENCES players(id),
    tournament_id INTEGER REFERENCES tournaments(id),
    amount INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, refunded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Админы
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    added_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Настройки
CREATE TABLE settings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT
);

-- Индексы
CREATE INDEX idx_players_telegram_id ON players(telegram_id);
CREATE INDEX idx_tournaments_status ON tournaments(status);
CREATE INDEX idx_matches_tournament ON matches(tournament_id);
CREATE INDEX idx_participant_status ON participant_status(tournament_id, status);
```

---

## 5. Backend API

### Аутентификация

Все запросы (кроме `/auth`) требуют JWT токен в заголовке:
```
Authorization: Bearer <token>
```

#### POST /api/auth/telegram

Авторизация через Telegram WebApp InitData.

**Request:**
```json
{
  "init_data": "query_id=AAHd...&user=%7B%22id%22%3A..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "player": {
    "id": 1,
    "telegram_id": 123456789,
    "nickname": "Player1",
    "is_registered": true,
    "is_admin": false
  }
}
```

### Игроки

#### GET /api/players/me

Получить профиль текущего игрока.

**Response:**
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "player1",
  "nickname": "ProPlayer",
  "steam_link": "https://steamcommunity.com/id/player1",
  "contact": "@player1_tg",
  "tournaments_won": 5,
  "tournaments_played": 12,
  "win_rate": 41.6,
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### POST /api/players/register

Регистрация нового игрока.

**Request:**
```json
{
  "nickname": "ProPlayer",
  "steam_link": "https://steamcommunity.com/id/player1",
  "contact": "@player1_tg"
}
```

#### PUT /api/players/me

Обновить профиль.

**Request:**
```json
{
  "nickname": "NewNickname",
  "steam_link": "https://steamcommunity.com/id/new",
  "contact": "@new_contact"
}
```

#### GET /api/players/rating

Рейтинг игроков.

**Query params:**
- `limit` (int, default 50)
- `offset` (int, default 0)

**Response:**
```json
{
  "total": 150,
  "players": [
    {
      "rank": 1,
      "id": 5,
      "nickname": "TopPlayer",
      "tournaments_won": 10,
      "tournaments_played": 15,
      "win_rate": 66.6
    }
  ]
}
```

### Команды

#### GET /api/teams

Список команд текущего игрока.

**Response:**
```json
{
  "teams": [
    {
      "id": 1,
      "name": "Team Alpha",
      "format": "5v5",
      "is_captain": true,
      "members_count": 5,
      "created_at": "2024-01-10T12:00:00Z"
    }
  ]
}
```

#### POST /api/teams

Создать команду.

**Request:**
```json
{
  "name": "Team Alpha",
  "format": "5v5"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Team Alpha",
  "format": "5v5",
  "invite_code": "IMMA-A1B2",
  "invite_expires_at": "2024-01-16T12:00:00Z"
}
```

#### GET /api/teams/{id}

Детали команды.

**Response:**
```json
{
  "id": 1,
  "name": "Team Alpha",
  "format": "5v5",
  "captain": {
    "id": 1,
    "nickname": "Captain",
    "steam_link": "..."
  },
  "members": [
    {
      "id": 2,
      "nickname": "Player2",
      "steam_link": "...",
      "contact": "@player2"
    }
  ],
  "invite_code": "IMMA-A1B2",
  "is_captain": true,
  "tournaments_won": 2
}
```

#### POST /api/teams/join

Присоединиться по инвайт-коду.

**Request:**
```json
{
  "invite_code": "IMMA-A1B2"
}
```

#### POST /api/teams/{id}/regenerate-code

Сгенерировать новый инвайт-код (только капитан).

#### POST /api/teams/{id}/kick/{player_id}

Кикнуть игрока (только капитан).

#### POST /api/teams/{id}/transfer/{player_id}

Передать капитанство (только капитан).

#### POST /api/teams/{id}/leave

Покинуть команду.

#### DELETE /api/teams/{id}

Распустить команду (только капитан).

### Турниры

#### GET /api/tournaments

Список турниров.

**Query params:**
- `status` (string): draft, open, active, finished
- `format` (string): 1v1, 2v2, 5v5
- `limit` (int, default 20)
- `offset` (int, default 0)

**Response:**
```json
{
  "total": 25,
  "tournaments": [
    {
      "id": 1,
      "name": "Weekly Cup #1",
      "format": "1v1",
      "status": "open",
      "start_time": "2024-01-20T18:00:00Z",
      "max_participants": 16,
      "current_participants": 10,
      "entry_fee": 50,
      "prizes": {"1": "1000 Stars", "2": "500 Stars"},
      "is_registered": false
    }
  ]
}
```

#### GET /api/tournaments/{id}

Детали турнира.

**Response:**
```json
{
  "id": 1,
  "name": "Weekly Cup #1",
  "format": "1v1",
  "status": "open",
  "start_time": "2024-01-20T18:00:00Z",
  "max_participants": 16,
  "current_participants": 10,
  "maps": ["de_mirage", "de_inferno", "de_dust2"],
  "prizes": {
    "1": "1000 Stars",
    "2": "500 Stars",
    "3": "250 Stars"
  },
  "entry_fee": 50,
  "checkin_required": true,
  "checkin_start_minutes": 60,
  "is_registered": true,
  "is_checked_in": false,
  "participants": [
    {
      "id": 1,
      "name": "Player1",
      "type": "player",
      "checked_in": true
    }
  ]
}
```

#### POST /api/tournaments/{id}/register

Регистрация на турнир.

**Request (для командных):**
```json
{
  "team_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "payment_required": true,
  "payment_url": "https://t.me/$..."
}
```

#### DELETE /api/tournaments/{id}/register

Отмена регистрации.

#### POST /api/tournaments/{id}/checkin

Подтвердить участие (check-in).

### Матчи

#### GET /api/tournaments/{id}/matches

Список матчей турнира.

**Response:**
```json
{
  "matches": [
    {
      "id": 1,
      "participant1": {"id": 1, "name": "Player1"},
      "participant2": {"id": 2, "name": "Player2"},
      "winner_id": 1,
      "score": "16:14",
      "status": "completed"
    }
  ]
}
```

#### GET /api/tournaments/{id}/standings

Текущие результаты турнира.

**Response:**
```json
{
  "standings": [
    {
      "rank": 1,
      "participant_id": 1,
      "name": "Player1",
      "status": "ready",
      "wins": 3,
      "losses": 0
    }
  ]
}
```

### Админ API

#### POST /api/admin/tournaments

Создать турнир.

**Request:**
```json
{
  "name": "Weekly Cup #1",
  "format": "1v1",
  "start_time": "2024-01-20T18:00:00Z",
  "max_participants": 16,
  "maps": ["de_mirage", "de_inferno"],
  "prizes": {"1": "1000 Stars", "2": "500 Stars"},
  "entry_fee": 50,
  "checkin_required": true
}
```

#### PUT /api/admin/tournaments/{id}

Обновить турнир.

#### POST /api/admin/tournaments/{id}/open

Открыть регистрацию.

#### POST /api/admin/tournaments/{id}/start

Запустить турнир.

#### POST /api/admin/tournaments/{id}/finish

Завершить турнир.

#### POST /api/admin/tournaments/{id}/matches

Создать матч.

**Request:**
```json
{
  "participant1_id": 1,
  "participant2_id": 2,
  "server_link": "connect 192.168.1.1:27015",
  "server_password": "match123"
}
```

#### PUT /api/admin/matches/{id}/result

Ввести результат матча.

**Request:**
```json
{
  "score1": 16,
  "score2": 14
}
```

#### DELETE /api/admin/matches/{id}

Отменить матч.

#### POST /api/admin/tournaments/{id}/restore/{participant_id}

Восстановить выбывшего участника.

#### GET /api/admin/stats

Статистика платформы.

**Response:**
```json
{
  "stars": {
    "total": 15000,
    "today": 500,
    "week": 3000,
    "month": 12000
  },
  "players": {
    "total": 500,
    "today": 10,
    "week": 50
  },
  "tournaments": {
    "total": 25,
    "active": 2,
    "finished": 20
  },
  "paid_tournaments": 15
}
```

---

## 6. Frontend

### Структура страниц

```
/                       # Главная — список турниров
/tournament/:id         # Детали турнира
/tournament/:id/bracket # Сетка турнира (если активен)
/profile                # Профиль игрока
/profile/edit           # Редактирование профиля
/teams                  # Мои команды
/team/:id               # Детали команды
/team/create            # Создание команды
/team/join              # Присоединение по коду
/rating                 # Рейтинг игроков
/register               # Регистрация нового игрока

# Админ
/admin                  # Дашборд
/admin/tournaments      # Управление турнирами
/admin/tournament/:id   # Управление турниром
/admin/tournament/:id/matches  # Управление матчами
/admin/stats            # Статистика
/admin/settings         # Настройки
```

### Ключевые компоненты

#### TournamentCard

```tsx
interface TournamentCardProps {
  tournament: {
    id: number;
    name: string;
    format: '1v1' | '2v2' | '5v5';
    status: 'open' | 'active' | 'finished';
    startTime: Date;
    participants: number;
    maxParticipants: number;
    entryFee: number;
    isRegistered: boolean;
  };
  onClick: () => void;
}
```

Показывает:
- Название и формат
- Дата/время начала
- Прогресс заполнения (X/Y участников)
- Взнос (если есть)
- Статус регистрации
- Бейдж статуса (открыт/идёт/завершён)

#### MatchControl (админ)

```tsx
interface MatchControlProps {
  tournamentId: number;
  participants: Participant[];
  activeMatches: Match[];
  onCreateMatch: (p1: number, p2: number, link: string, password?: string) => void;
  onCompleteMatch: (matchId: number, score1: number, score2: number) => void;
  onCancelMatch: (matchId: number) => void;
}
```

Показывает:
- Список готовых участников (можно выбрать двух)
- Форма создания матча (ссылка + пароль)
- Список активных матчей
- Форма ввода результата (счёт)
- Кнопки отмены матча

#### ParticipantStatus

```tsx
interface ParticipantStatusProps {
  participants: {
    id: number;
    name: string;
    status: 'ready' | 'in_match' | 'eliminated';
    wins: number;
    losses: number;
  }[];
}
```

Показывает участников с цветовой индикацией:
- 🟢 Готов — зелёный
- 🔴 В матче — красный
- ❌ Выбыл — серый

#### ScoreInput

```tsx
interface ScoreInputProps {
  match: Match;
  onSubmit: (score1: number, score2: number) => void;
}
```

Форма ввода счёта:
- Два числовых поля
- Валидация (не равны, положительные)
- Показывает имена участников

### Стили (Tailwind)

```css
/* Основные цвета */
:root {
  --tg-theme-bg-color: #1a1a1a;
  --tg-theme-text-color: #ffffff;
  --tg-theme-hint-color: #999999;
  --tg-theme-link-color: #3390ec;
  --tg-theme-button-color: #3390ec;
  --tg-theme-button-text-color: #ffffff;
}

/* Статусы */
.status-ready { @apply bg-green-500/20 text-green-400; }
.status-in-match { @apply bg-red-500/20 text-red-400; }
.status-eliminated { @apply bg-gray-500/20 text-gray-400; }

/* Карточки */
.card {
  @apply bg-white/5 rounded-xl p-4 border border-white/10;
}

/* Кнопки */
.btn-primary {
  @apply bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg;
}
.btn-secondary {
  @apply bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg;
}
```

---

## 7. Telegram интеграция

### WebApp SDK

```typescript
// hooks/useTelegram.ts
import { useEffect, useState } from 'react';

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    user?: {
      id: number;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
      is_premium?: boolean;
    };
  };
  colorScheme: 'light' | 'dark';
  themeParams: Record<string, string>;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;

  ready(): void;
  expand(): void;
  close(): void;

  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
    showProgress(leaveActive?: boolean): void;
    hideProgress(): void;
  };

  BackButton: {
    isVisible: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };

  HapticFeedback: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void;
    notificationOccurred(type: 'error' | 'success' | 'warning'): void;
    selectionChanged(): void;
  };

  showPopup(params: {
    title?: string;
    message: string;
    buttons?: Array<{
      id?: string;
      type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
      text?: string;
    }>;
  }, callback?: (buttonId: string) => void): void;

  showConfirm(message: string, callback?: (confirmed: boolean) => void): void;
  showAlert(message: string, callback?: () => void): void;

  openInvoice(url: string, callback?: (status: string) => void): void;
}

export function useTelegram() {
  const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);
  const [user, setUser] = useState<TelegramWebApp['initDataUnsafe']['user'] | null>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      setWebApp(tg);
      setUser(tg.initDataUnsafe.user || null);
    }
  }, []);

  return {
    webApp,
    user,
    initData: webApp?.initData || '',
    colorScheme: webApp?.colorScheme || 'dark',

    // Shortcuts
    showMainButton: (text: string, onClick: () => void) => {
      if (webApp) {
        webApp.MainButton.text = text;
        webApp.MainButton.onClick(onClick);
        webApp.MainButton.show();
      }
    },
    hideMainButton: () => webApp?.MainButton.hide(),

    showBackButton: (onClick: () => void) => {
      if (webApp) {
        webApp.BackButton.onClick(onClick);
        webApp.BackButton.show();
      }
    },
    hideBackButton: () => webApp?.BackButton.hide(),

    haptic: webApp?.HapticFeedback,

    showConfirm: (message: string) => new Promise<boolean>((resolve) => {
      webApp?.showConfirm(message, resolve);
    }),

    showAlert: (message: string) => new Promise<void>((resolve) => {
      webApp?.showAlert(message, resolve);
    }),

    openInvoice: (url: string) => new Promise<string>((resolve) => {
      webApp?.openInvoice(url, resolve);
    }),
  };
}
```

### Авторизация

```typescript
// api/auth.ts
import { api } from './client';

export async function authenticateWithTelegram(initData: string) {
  const response = await api.post('/auth/telegram', { init_data: initData });
  return response.data;
}

// App.tsx
function App() {
  const { initData } = useTelegram();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    if (initData) {
      authenticateWithTelegram(initData)
        .then((data) => {
          localStorage.setItem('token', data.access_token);
          setIsAuthenticated(true);
        })
        .catch(console.error);
    }
  }, [initData]);

  if (!isAuthenticated) {
    return <LoadingScreen />;
  }

  return <Router />;
}
```

### Валидация InitData (Backend)

```python
# utils/telegram_auth.py
import hashlib
import hmac
import json
from urllib.parse import parse_qs
from datetime import datetime, timedelta
from app.config import settings

def validate_init_data(init_data: str) -> dict | None:
    """Валидация Telegram WebApp InitData."""
    try:
        parsed = parse_qs(init_data)

        # Извлекаем hash
        received_hash = parsed.get('hash', [None])[0]
        if not received_hash:
            return None

        # Собираем data-check-string
        data_check_arr = []
        for key in sorted(parsed.keys()):
            if key != 'hash':
                data_check_arr.append(f"{key}={parsed[key][0]}")
        data_check_string = '\n'.join(data_check_arr)

        # Вычисляем secret key
        secret_key = hmac.new(
            b'WebAppData',
            settings.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Сравниваем
        if calculated_hash != received_hash:
            return None

        # Проверяем время (не старше 24 часов)
        auth_date = int(parsed.get('auth_date', [0])[0])
        if datetime.utcnow() - datetime.utcfromtimestamp(auth_date) > timedelta(hours=24):
            return None

        # Парсим user
        user_json = parsed.get('user', [None])[0]
        if user_json:
            return json.loads(user_json)

        return None

    except Exception:
        return None
```

### Платежи (Stars)

```python
# services/payment_service.py
from aiogram import Bot
from aiogram.types import LabeledPrice

async def create_stars_invoice(
    bot: Bot,
    tournament_id: int,
    amount: int,
    title: str,
    description: str
) -> str:
    """Создать инвойс для оплаты Stars."""

    prices = [LabeledPrice(label="Взнос", amount=amount)]

    link = await bot.create_invoice_link(
        title=title,
        description=description,
        payload=f"tournament_{tournament_id}",
        currency="XTR",  # Telegram Stars
        prices=prices
    )

    return link

async def refund_stars(bot: Bot, user_id: int, payment_charge_id: str) -> bool:
    """Вернуть Stars."""
    try:
        await bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=payment_charge_id
        )
        return True
    except Exception:
        return False
```

```typescript
// Frontend: обработка оплаты
const { openInvoice, haptic } = useTelegram();

async function handleRegister() {
  const result = await registerForTournament(tournamentId, teamId);

  if (result.payment_required && result.payment_url) {
    const status = await openInvoice(result.payment_url);

    if (status === 'paid') {
      haptic?.notificationOccurred('success');
      // Обновить UI
    } else {
      haptic?.notificationOccurred('error');
    }
  }
}
```

---

## 8. Функционал по ролям

### Игрок (не зарегистрирован)

- Просмотр списка турниров
- Просмотр рейтинга
- Регистрация в системе

### Игрок (зарегистрирован)

**Профиль:**
- Просмотр своих данных и статистики
- Редактирование никнейма, Steam, контакта

**Команды:**
- Просмотр своих команд
- Создание команды (2v2 или 5v5)
- Генерация инвайт-кода (действует 24ч)
- Присоединение к команде по коду
- Выход из команды

**Турниры:**
- Просмотр списка открытых турниров
- Фильтрация по формату
- Регистрация на турнир (соло)
- Оплата взноса (Stars)
- Отмена регистрации (с возвратом Stars)
- Check-in перед началом
- Просмотр сетки и результатов

### Капитан команды

Всё что может игрок, плюс:

- Регистрация команды на турнир
- Оплата взноса за команду
- Генерация нового инвайт-кода
- Кик участников из команды
- Передача капитанства
- Роспуск команды

### Админ

Всё что может игрок, плюс:

**Турниры:**
- Создание турнира со всеми параметрами
- Редактирование турнира
- Открытие/закрытие регистрации
- Запуск турнира
- Завершение турнира

**Матчи:**
- Просмотр участников по статусам
- Создание матча (выбор двух участников)
- Ввод ссылки на сервер и пароля
- Ввод результата
- Отмена матча
- Восстановление выбывшего участника

**Участники:**
- Просмотр списка с контактами
- Кик из турнира
- Бан игрока

**Рассылки:**
- Всем участникам турнира
- Не прошедшим check-in
- Кастомное сообщение

**Статистика:**
- Stars: всего, сегодня, неделя, месяц
- Игроки: всего, новые
- Турниры: активные, завершённые

### Владелец

Всё что может админ, плюс:

- Добавление/удаление админов
- Настройка канала для анонсов
- Редактирование контактов для призов

---

## 9. UI/UX требования

### Общие принципы

1. **Тёмная тема** — соответствие Telegram
2. **Mobile-first** — основной таргет
3. **Быстрая навигация** — минимум кликов до цели
4. **Нативность** — использовать Telegram UI где возможно

### Цветовая схема

```css
/* Используем переменные Telegram */
background: var(--tg-theme-bg-color);
color: var(--tg-theme-text-color);
hint: var(--tg-theme-hint-color);
link: var(--tg-theme-link-color);
button: var(--tg-theme-button-color);

/* Акцентные цвета */
--success: #34C759;
--warning: #FF9500;
--error: #FF3B30;
--info: #007AFF;
```

### Компоненты

**Кнопки:**
- Primary — заполненные, для главных действий
- Secondary — с обводкой, для вторичных
- Destructive — красные, для удаления/отмены

**Карточки:**
- Скруглённые углы (12px)
- Лёгкая тень или border
- Отступы 16px

**Формы:**
- Поля с подсказками
- Inline валидация
- Понятные ошибки

**Списки:**
- Pull-to-refresh
- Skeleton loading
- Empty state

### Анимации

- Переходы между страницами (slide)
- Появление элементов (fade-in)
- Haptic feedback на действиях
- Skeleton loading для контента

### Адаптивность

```css
/* Breakpoints */
sm: 320px   /* Маленькие телефоны */
md: 375px   /* iPhone */
lg: 414px   /* Большие телефоны */
xl: 768px   /* Планшеты */
```

### Навигация

**Bottom Navigation (для игроков):**
- 🏠 Главная (турниры)
- 👥 Команды
- 👤 Профиль
- 🏆 Рейтинг

**Sidebar (для админов):**
- Dashboard
- Турниры
- Статистика
- Настройки

---

## 10. Деплой

### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tournament
      - REDIS_URL=redis://redis:6379
      - BOT_TOKEN=${BOT_TOKEN}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - db
      - redis
    restart: always

  frontend:
    build: ./frontend
    environment:
      - VITE_API_URL=https://api.yourdomain.com
    restart: always

  bot:
    build: ./backend
    command: python -m app.bot
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tournament
      - BOT_TOKEN=${BOT_TOKEN}
    depends_on:
      - db
    restart: always

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=tournament
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - backend
      - frontend
    restart: always

volumes:
  postgres_data:
  redis_data:
```

### Nginx конфиг

```nginx
server {
    listen 80;
    server_name yourdomain.com api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Переменные окружения

```env
# Backend
DATABASE_URL=postgresql://user:password@localhost:5432/tournament
REDIS_URL=redis://localhost:6379
BOT_TOKEN=123456:ABC-DEF...
JWT_SECRET=your-super-secret-key
JWT_EXPIRE_HOURS=24
OWNER_TELEGRAM_ID=123456789

# Frontend
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com/ws
```

### Регистрация Mini App

1. Открыть @BotFather
2. `/mybots` → выбрать бота
3. `Bot Settings` → `Menu Button` → задать URL Mini App
4. Или использовать `Web App` кнопку в боте

---

## Чеклист для запуска

- [ ] Настроен PostgreSQL
- [ ] Настроен Redis
- [ ] Выполнены миграции БД
- [ ] Получен SSL сертификат
- [ ] Настроен Nginx
- [ ] Создан бот в @BotFather
- [ ] Включены Telegram Stars в боте
- [ ] Зарегистрирован Mini App URL
- [ ] Добавлен владелец в админы
- [ ] Протестирована авторизация
- [ ] Протестированы платежи

---

Используй этот документ для создания полнофункционального Telegram Mini App с нуля.
