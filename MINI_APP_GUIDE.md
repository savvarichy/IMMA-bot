# IMMA Championship — Telegram Mini App Guide

Полное руководство по трансформации бота в Telegram Mini App для создания лучшей турнирной платформы.

---

## Содержание

1. [Обзор и преимущества](#1-обзор-и-преимущества)
2. [Архитектура системы](#2-архитектура-системы)
3. [Технологический стек](#3-технологический-стек)
4. [Этапы миграции](#4-этапы-миграции)
5. [Backend API](#5-backend-api)
6. [Frontend разработка](#6-frontend-разработка)
7. [Telegram WebApp интеграция](#7-telegram-webapp-интеграция)
8. [Аутентификация и безопасность](#8-аутентификация-и-безопасность)
9. [Платежи (Telegram Stars)](#9-платежи-telegram-stars)
10. [Real-time функции](#10-real-time-функции)
11. [UI/UX дизайн](#11-uiux-дизайн)
12. [Продвинутые функции](#12-продвинутые-функции)
13. [Инфраструктура и деплой](#13-инфраструктура-и-деплой)
14. [Монетизация](#14-монетизация)
15. [Roadmap](#15-roadmap)

---

## 1. Обзор и преимущества

### Что такое Telegram Mini App?

Mini App — это веб-приложение, которое открывается прямо внутри Telegram и имеет доступ к:
- Данным пользователя (ID, имя, фото, premium статус)
- Нативным UI компонентам Telegram
- Платёжной системе (Stars, карты)
- Биометрической аутентификации
- Буферу обмена, геолокации, QR-сканеру
- Haptic feedback (вибрация)

### Почему Mini App лучше бота?

| Функция | Бот | Mini App |
|---------|-----|----------|
| UI/UX | Кнопки и текст | Полноценный веб-интерфейс |
| Визуализация сетки | Текстовая таблица | Интерактивный bracket |
| Статистика | Текстовые сообщения | Графики и дашборды |
| Формы | Пошаговый ввод | Одна страница формы |
| Фильтры | Ограниченные | Любая сложность |
| Анимации | Нет | Полная поддержка |
| Офлайн | Нет | PWA поддержка |
| Скорость | Ждём ответ бота | Мгновенный отклик |
| Админ-панель | Неудобные меню | Drag-and-drop интерфейс |

### Конкурентные преимущества

1. **Уникальность** — нет турнирных Mini App для СНГ рынка
2. **Telegram-native** — не нужно скачивать приложение
3. **Виральность** — лёгкий шеринг через Telegram
4. **Оплата Stars** — без комиссий App Store/Google Play
5. **800M+ аудитория** — доступ к огромной базе пользователей

---

## 2. Архитектура системы

### Текущая архитектура (Bot)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Telegram  │────▶│   aiogram   │────▶│   SQLite    │
│   Bot API   │◀────│   (Python)  │◀────│   Database  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Целевая архитектура (Mini App + Bot)

```
                                    ┌─────────────────────────────────────┐
                                    │           Frontend (Mini App)        │
                                    │  ┌─────────┐  ┌─────────┐  ┌──────┐ │
                                    │  │  React  │  │ Telegram│  │ PWA  │ │
                                    │  │   SPA   │  │ WebApp  │  │      │ │
                                    │  │         │  │   SDK   │  │      │ │
                                    │  └────┬────┘  └────┬────┘  └──┬───┘ │
                                    └───────┼───────────┼──────────┼─────┘
                                            │           │          │
                                            ▼           ▼          ▼
┌─────────────┐     ┌───────────────────────────────────────────────────┐
│   Telegram  │     │                  Backend                          │
│   Bot API   │◀───▶│  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
└─────────────┘     │  │ FastAPI  │  │WebSocket │  │    Services    │  │
                    │  │ REST API │  │  Server  │  │ (existing code)│  │
                    │  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
                    │       │             │                │           │
                    │       ▼             ▼                ▼           │
                    │  ┌─────────────────────────────────────────────┐ │
                    │  │              PostgreSQL / SQLite            │ │
                    │  └─────────────────────────────────────────────┘ │
                    │                                                   │
                    │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
                    │  │    Redis    │  │   Celery    │  │  aiogram  │ │
                    │  │   (cache)   │  │  (tasks)    │  │   (bot)   │ │
                    │  └─────────────┘  └─────────────┘  └───────────┘ │
                    └───────────────────────────────────────────────────┘
```

### Компоненты системы

#### Frontend
- **React/Next.js** — основной фреймворк
- **Telegram WebApp SDK** — интеграция с Telegram
- **TailwindCSS** — стилизация
- **Framer Motion** — анимации
- **React Query** — кэширование запросов
- **Socket.io-client** — real-time

#### Backend
- **FastAPI** — REST API (Python)
- **aiogram** — Telegram Bot (уведомления)
- **SQLAlchemy** — ORM
- **Alembic** — миграции БД
- **Redis** — кэш и pub/sub
- **Celery** — фоновые задачи

#### Инфраструктура
- **PostgreSQL** — основная БД
- **Nginx** — reverse proxy
- **Docker** — контейнеризация
- **GitHub Actions** — CI/CD

---

## 3. Технологический стек

### Рекомендуемый стек

```yaml
Frontend:
  Framework: Next.js 14 (App Router)
  Language: TypeScript
  UI Library: shadcn/ui + Radix
  Styling: TailwindCSS
  State: Zustand / Jotai
  Data Fetching: TanStack Query
  Animations: Framer Motion
  Charts: Recharts / Tremor
  Forms: React Hook Form + Zod

Backend:
  Framework: FastAPI
  Language: Python 3.11+
  ORM: SQLAlchemy 2.0
  Validation: Pydantic v2
  Auth: python-jose (JWT)
  Tasks: Celery + Redis
  WebSocket: FastAPI WebSockets

Database:
  Primary: PostgreSQL 15
  Cache: Redis 7
  Search: PostgreSQL Full-Text (позже Meilisearch)

Infrastructure:
  Container: Docker + Docker Compose
  Reverse Proxy: Nginx / Caddy
  Hosting: VPS (Hetzner/DigitalOcean) или Vercel + Railway
  CI/CD: GitHub Actions
  Monitoring: Sentry + Prometheus + Grafana
```

### Альтернативный лёгкий стек

Для быстрого старта и меньших затрат:

```yaml
Frontend:
  Framework: Vue 3 + Vite
  UI: Naive UI / Element Plus
  Styling: UnoCSS

Backend:
  Framework: FastAPI (monolith)
  Database: SQLite → PostgreSQL

Hosting:
  Backend: Railway / Render
  Frontend: Vercel / Cloudflare Pages
```

---

## 4. Этапы миграции

### Фаза 0: Подготовка (1-2 недели)

```
□ Ревью существующего кода
□ Документирование всех endpoints бота
□ Проектирование REST API
□ Создание OpenAPI спецификации
□ Настройка репозитория (monorepo)
□ Настройка CI/CD pipeline
```

**Структура монорепозитория:**

```
imma-championship/
├── apps/
│   ├── bot/              # Существующий бот (уведомления)
│   ├── api/              # FastAPI backend
│   └── web/              # Next.js frontend
├── packages/
│   ├── database/         # Shared database models
│   ├── types/            # TypeScript типы (генерируются из OpenAPI)
│   └── config/           # Shared конфигурация
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile.*
├── .github/
│   └── workflows/
└── docs/
```

### Фаза 1: REST API (2-3 недели)

**Цель:** Создать API, переиспользуя существующую бизнес-логику.

```python
# apps/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="IMMA Championship API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://t.me"],  # Telegram WebApp origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(tournaments_router, prefix="/tournaments", tags=["tournaments"])
app.include_router(teams_router, prefix="/teams", tags=["teams"])
app.include_router(matches_router, prefix="/matches", tags=["matches"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
```

**Переиспользование сервисов:**

```python
# apps/api/routers/tournaments.py
from fastapi import APIRouter, Depends, HTTPException
from database import db  # Существующий модуль!
from services.bracket import BracketGenerator  # Существующий!

router = APIRouter()

@router.get("/")
async def list_tournaments(
    status: str = None,
    format: str = None,
    limit: int = 20,
    offset: int = 0
):
    """Список турниров с фильтрацией."""
    if status:
        tournaments = await db.get_tournaments_by_status(status)
    else:
        tournaments = await db.get_all_tournaments()

    # Пагинация
    return {
        "items": tournaments[offset:offset+limit],
        "total": len(tournaments),
        "limit": limit,
        "offset": offset
    }

@router.get("/{tournament_id}")
async def get_tournament(tournament_id: int):
    """Детали турнира."""
    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(404, "Tournament not found")

    # Дополняем данными
    participant_count = await db.get_tournament_participant_count(tournament_id)
    matches = await db.get_tournament_matches(tournament_id)

    return {
        **tournament,
        "participant_count": participant_count,
        "matches": matches
    }

@router.post("/{tournament_id}/register")
async def register_for_tournament(
    tournament_id: int,
    user: User = Depends(get_current_user)
):
    """Регистрация на турнир."""
    # Переиспользуем существующую логику
    tournament = await db.get_tournament(tournament_id)

    if tournament["format"] == "1v1":
        player = await db.get_player(user.telegram_id)
        if not player:
            raise HTTPException(400, "Player not registered")

        # Проверка существующей регистрации
        existing = await db.get_tournament_registration(
            tournament_id, player["id"]
        )
        if existing:
            raise HTTPException(400, "Already registered")

        await db.register_player_for_tournament(tournament_id, player["id"])
        return {"status": "registered"}
    else:
        # Командная регистрация...
        pass
```

### Фаза 2: Базовый Frontend (3-4 недели)

**Цель:** MVP веб-интерфейса с основными функциями.

```
Страницы MVP:
├── / (главная - список турниров)
├── /tournament/[id] (детали турнира)
├── /tournament/[id]/bracket (сетка)
├── /profile (профиль пользователя)
├── /teams (мои команды)
└── /admin/* (админ-панель)
```

**Компонент списка турниров:**

```tsx
// apps/web/app/page.tsx
'use client';

import { useTournaments } from '@/hooks/useTournaments';
import { TournamentCard } from '@/components/TournamentCard';
import { TournamentFilters } from '@/components/TournamentFilters';

export default function HomePage() {
  const [filters, setFilters] = useState({
    status: 'open',
    format: null,
  });

  const { data, isLoading } = useTournaments(filters);

  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-6">
        🏆 IMMA Championship
      </h1>

      <TournamentFilters
        value={filters}
        onChange={setFilters}
      />

      <div className="grid gap-4 mt-6">
        {isLoading ? (
          <TournamentSkeleton count={3} />
        ) : (
          data?.items.map(tournament => (
            <TournamentCard
              key={tournament.id}
              tournament={tournament}
            />
          ))
        )}
      </div>
    </div>
  );
}
```

**Компонент турнирной карточки:**

```tsx
// apps/web/components/TournamentCard.tsx
import { Tournament } from '@/types';
import { formatDate, formatPrize } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface Props {
  tournament: Tournament;
}

export function TournamentCard({ tournament }: Props) {
  const progress = (tournament.participant_count / tournament.max_participants) * 100;

  return (
    <Link href={`/tournament/${tournament.id}`}>
      <div className="bg-card rounded-xl p-4 border hover:border-primary transition-colors">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-semibold text-lg">{tournament.name}</h3>
            <p className="text-muted-foreground text-sm">
              {formatDate(tournament.start_time)}
            </p>
          </div>
          <Badge variant={getStatusVariant(tournament.status)}>
            {getStatusLabel(tournament.status)}
          </Badge>
        </div>

        <div className="flex gap-2 mb-3">
          <Badge variant="outline">{tournament.format}</Badge>
          {tournament.entry_fee > 0 && (
            <Badge variant="secondary">
              ⭐ {tournament.entry_fee}
            </Badge>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Участники</span>
            <span>{tournament.participant_count}/{tournament.max_participants}</span>
          </div>
          <Progress value={progress} />
        </div>

        {tournament.prizes && (
          <div className="mt-3 pt-3 border-t">
            <p className="text-sm text-muted-foreground">Призы:</p>
            <p className="font-medium">{formatPrize(tournament.prizes)}</p>
          </div>
        )}
      </div>
    </Link>
  );
}
```

### Фаза 3: Telegram WebApp интеграция (1-2 недели)

**Цель:** Полная интеграция с Telegram.

```tsx
// apps/web/providers/TelegramProvider.tsx
'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import type { WebApp, WebAppUser } from '@/types/telegram';

interface TelegramContext {
  webApp: WebApp | null;
  user: WebAppUser | null;
  isReady: boolean;
  colorScheme: 'light' | 'dark';
}

const TelegramContext = createContext<TelegramContext | null>(null);

export function TelegramProvider({ children }: { children: React.ReactNode }) {
  const [webApp, setWebApp] = useState<WebApp | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (tg) {
      tg.ready();
      tg.expand();
      tg.enableClosingConfirmation();

      setWebApp(tg);
      setIsReady(true);

      // Применяем тему Telegram
      document.documentElement.setAttribute(
        'data-theme',
        tg.colorScheme
      );
    }
  }, []);

  return (
    <TelegramContext.Provider value={{
      webApp,
      user: webApp?.initDataUnsafe?.user ?? null,
      isReady,
      colorScheme: webApp?.colorScheme ?? 'light',
    }}>
      {children}
    </TelegramContext.Provider>
  );
}

export function useTelegram() {
  const context = useContext(TelegramContext);
  if (!context) {
    throw new Error('useTelegram must be used within TelegramProvider');
  }
  return context;
}
```

### Фаза 4: Продвинутые функции (4-6 недель)

```
□ Интерактивная турнирная сетка
□ Real-time обновления
□ Push уведомления
□ Офлайн режим (PWA)
□ Статистика и графики
□ Drag-and-drop админ-панель
□ Мультиязычность
```

### Фаза 5: Оптимизация и масштабирование (ongoing)

```
□ Нагрузочное тестирование
□ CDN для статики
□ Горизонтальное масштабирование
□ Кэширование (Redis)
□ Мониторинг и алерты
□ A/B тестирование
```

---

## 5. Backend API

### OpenAPI Спецификация

```yaml
# openapi.yaml
openapi: 3.1.0
info:
  title: IMMA Championship API
  version: 1.0.0
  description: Tournament platform API

servers:
  - url: https://api.imma.gg/v1
    description: Production
  - url: http://localhost:8000/v1
    description: Development

security:
  - TelegramAuth: []

paths:
  /tournaments:
    get:
      summary: List tournaments
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [draft, open, checkin, active, finished, cancelled]
        - name: format
          in: query
          schema:
            type: string
            enum: [1v1, 2v2, 5v5]
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TournamentList'

  /tournaments/{id}:
    get:
      summary: Get tournament details
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TournamentDetail'

  /tournaments/{id}/register:
    post:
      summary: Register for tournament
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                team_id:
                  type: integer
                  description: Required for team tournaments
      responses:
        '200':
          description: Registered successfully
        '400':
          description: Registration not allowed
        '402':
          description: Payment required

  /tournaments/{id}/bracket:
    get:
      summary: Get tournament bracket
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Bracket'

components:
  securitySchemes:
    TelegramAuth:
      type: apiKey
      in: header
      name: X-Telegram-Init-Data
      description: Telegram WebApp initData

  schemas:
    Tournament:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        format:
          type: string
          enum: [1v1, 2v2, 5v5]
        status:
          type: string
          enum: [draft, open, checkin, active, finished, cancelled]
        max_participants:
          type: integer
        participant_count:
          type: integer
        entry_fee:
          type: integer
        prizes:
          type: object
        maps:
          type: array
          items:
            type: string
        start_time:
          type: string
          format: date-time
        created_at:
          type: string
          format: date-time

    TournamentList:
      type: object
      properties:
        items:
          type: array
          items:
            $ref: '#/components/schemas/Tournament'
        total:
          type: integer
        limit:
          type: integer
        offset:
          type: integer

    Bracket:
      type: object
      properties:
        tournament_id:
          type: integer
        rounds:
          type: object
          additionalProperties:
            type: array
            items:
              $ref: '#/components/schemas/Match'
        total_rounds:
          type: integer

    Match:
      type: object
      properties:
        id:
          type: integer
        round:
          type: integer
        match_number:
          type: integer
        participant1:
          $ref: '#/components/schemas/Participant'
        participant2:
          $ref: '#/components/schemas/Participant'
        score1:
          type: integer
        score2:
          type: integer
        winner_id:
          type: integer
        status:
          type: string
          enum: [pending, active, completed, cancelled]
```

### Структура API роутеров

```python
# apps/api/routers/__init__.py

# Публичные эндпоинты (любой пользователь)
from .tournaments import router as tournaments_router  # GET /tournaments
from .users import router as users_router              # GET /users/{id}
from .bracket import router as bracket_router          # GET /bracket/{tournament_id}

# Авторизованные эндпоинты (требуют Telegram auth)
from .me import router as me_router                    # /me/*
from .teams import router as teams_router              # /teams/*
from .registration import router as registration_router # /register/*

# Админские эндпоинты (проверка is_admin)
from .admin import router as admin_router              # /admin/*

# WebSocket эндпоинты
from .ws import router as ws_router                    # /ws/*
```

### Модели Pydantic

```python
# apps/api/schemas/tournament.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class TournamentFormat(str, Enum):
    ONE_V_ONE = "1v1"
    TWO_V_TWO = "2v2"
    FIVE_V_FIVE = "5v5"

class TournamentStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    CHECKIN = "checkin"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"

class TournamentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    format: TournamentFormat
    max_participants: int = Field(..., ge=2, le=128)
    entry_fee: int = Field(default=0, ge=0)
    prizes: Optional[dict] = None
    maps: list[str] = Field(default_factory=list)
    start_time: datetime
    checkin_hours: Optional[int] = Field(default=0, ge=0, le=24)

class TournamentCreate(TournamentBase):
    pass

class TournamentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    max_participants: Optional[int] = Field(None, ge=2, le=128)
    entry_fee: Optional[int] = Field(None, ge=0)
    prizes: Optional[dict] = None
    maps: Optional[list[str]] = None
    start_time: Optional[datetime] = None
    checkin_hours: Optional[int] = Field(None, ge=0, le=24)

class Tournament(TournamentBase):
    id: int
    status: TournamentStatus
    participant_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class TournamentDetail(Tournament):
    """Расширенная информация о турнире."""
    participants: list["Participant"] = []
    matches: list["Match"] = []
    channel_post_id: Optional[int] = None
```

---

## 6. Frontend разработка

### Структура проекта

```
apps/web/
├── app/
│   ├── (main)/
│   │   ├── page.tsx              # Главная
│   │   ├── tournament/
│   │   │   ├── [id]/
│   │   │   │   ├── page.tsx      # Детали турнира
│   │   │   │   ├── bracket/
│   │   │   │   │   └── page.tsx  # Сетка
│   │   │   │   └── register/
│   │   │   │       └── page.tsx  # Регистрация
│   │   │   └── page.tsx          # Список
│   │   ├── profile/
│   │   │   └── page.tsx          # Мой профиль
│   │   └── teams/
│   │       ├── page.tsx          # Мои команды
│   │       └── [id]/
│   │           └── page.tsx      # Детали команды
│   ├── admin/
│   │   ├── layout.tsx            # Admin layout
│   │   ├── page.tsx              # Dashboard
│   │   ├── tournaments/
│   │   │   ├── page.tsx          # Список
│   │   │   ├── new/
│   │   │   │   └── page.tsx      # Создание
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # Управление
│   │   │       └── matches/
│   │   │           └── page.tsx  # Матчи
│   │   ├── players/
│   │   │   └── page.tsx          # Игроки
│   │   └── settings/
│   │       └── page.tsx          # Настройки
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                       # shadcn/ui компоненты
│   ├── tournament/
│   │   ├── TournamentCard.tsx
│   │   ├── TournamentList.tsx
│   │   ├── TournamentFilters.tsx
│   │   └── TournamentDetails.tsx
│   ├── bracket/
│   │   ├── Bracket.tsx           # Основной компонент
│   │   ├── BracketMatch.tsx      # Один матч
│   │   ├── BracketRound.tsx      # Раунд
│   │   └── BracketConnector.tsx  # Линии соединения
│   ├── match/
│   │   ├── MatchCard.tsx
│   │   └── MatchResult.tsx
│   ├── team/
│   │   ├── TeamCard.tsx
│   │   └── TeamMembers.tsx
│   ├── player/
│   │   ├── PlayerCard.tsx
│   │   └── PlayerStats.tsx
│   └── layout/
│       ├── Header.tsx
│       ├── Navigation.tsx
│       └── BottomNav.tsx
├── hooks/
│   ├── useTelegram.ts
│   ├── useTournaments.ts
│   ├── useTeams.ts
│   ├── useMatches.ts
│   └── useWebSocket.ts
├── lib/
│   ├── api.ts                    # API клиент
│   ├── utils.ts                  # Утилиты
│   └── telegram.ts               # Telegram helpers
├── providers/
│   ├── TelegramProvider.tsx
│   ├── QueryProvider.tsx
│   └── ThemeProvider.tsx
├── types/
│   ├── index.ts
│   └── telegram.d.ts
└── styles/
    └── telegram-theme.css
```

### Интерактивная турнирная сетка

```tsx
// apps/web/components/bracket/Bracket.tsx
'use client';

import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BracketRound } from './BracketRound';
import { BracketConnectors } from './BracketConnectors';
import type { BracketData } from '@/types';

interface Props {
  data: BracketData;
  onMatchClick?: (matchId: number) => void;
  isAdmin?: boolean;
}

export function Bracket({ data, onMatchClick, isAdmin }: Props) {
  const { rounds, totalRounds } = data;

  // Вычисляем размеры для SVG коннекторов
  const dimensions = useMemo(() => {
    const matchHeight = 80;
    const matchGap = 20;
    const roundWidth = 250;
    const roundGap = 60;

    const firstRoundMatches = rounds[1]?.length || 0;
    const totalHeight = firstRoundMatches * (matchHeight + matchGap);
    const totalWidth = totalRounds * (roundWidth + roundGap);

    return { matchHeight, matchGap, roundWidth, roundGap, totalHeight, totalWidth };
  }, [rounds, totalRounds]);

  return (
    <div className="relative overflow-x-auto pb-4">
      <div
        className="flex gap-4 relative"
        style={{ minWidth: dimensions.totalWidth }}
      >
        {/* Линии соединения */}
        <BracketConnectors
          rounds={rounds}
          dimensions={dimensions}
        />

        {/* Раунды */}
        {Array.from({ length: totalRounds }, (_, i) => i + 1).map(roundNum => (
          <BracketRound
            key={roundNum}
            roundNumber={roundNum}
            totalRounds={totalRounds}
            matches={rounds[roundNum] || []}
            onMatchClick={onMatchClick}
            isAdmin={isAdmin}
            dimensions={dimensions}
          />
        ))}
      </div>
    </div>
  );
}

// apps/web/components/bracket/BracketMatch.tsx
import { cn } from '@/lib/utils';
import type { Match } from '@/types';

interface Props {
  match: Match;
  onClick?: () => void;
  isAdmin?: boolean;
  highlight?: 'winner' | 'loser' | null;
}

export function BracketMatch({ match, onClick, isAdmin, highlight }: Props) {
  const isCompleted = match.status === 'completed';
  const isActive = match.status === 'active';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "bg-card border rounded-lg overflow-hidden cursor-pointer",
        "hover:border-primary transition-all duration-200",
        isActive && "border-yellow-500 ring-2 ring-yellow-500/20",
        isCompleted && "opacity-90"
      )}
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Участник 1 */}
      <div className={cn(
        "flex items-center justify-between px-3 py-2 border-b",
        isCompleted && match.winner_id === match.participant1?.id && "bg-green-500/10"
      )}>
        <div className="flex items-center gap-2">
          {match.participant1 ? (
            <>
              <span className="font-medium truncate max-w-[150px]">
                {match.participant1.name}
              </span>
              {isCompleted && match.winner_id === match.participant1.id && (
                <span className="text-green-500">👑</span>
              )}
            </>
          ) : (
            <span className="text-muted-foreground italic">TBD</span>
          )}
        </div>
        {isCompleted && (
          <span className={cn(
            "font-bold",
            match.winner_id === match.participant1?.id ? "text-green-500" : "text-muted-foreground"
          )}>
            {match.score1}
          </span>
        )}
      </div>

      {/* Участник 2 */}
      <div className={cn(
        "flex items-center justify-between px-3 py-2",
        isCompleted && match.winner_id === match.participant2?.id && "bg-green-500/10"
      )}>
        <div className="flex items-center gap-2">
          {match.participant2 ? (
            <>
              <span className="font-medium truncate max-w-[150px]">
                {match.participant2.name}
              </span>
              {isCompleted && match.winner_id === match.participant2.id && (
                <span className="text-green-500">👑</span>
              )}
            </>
          ) : (
            <span className="text-muted-foreground italic">TBD</span>
          )}
        </div>
        {isCompleted && (
          <span className={cn(
            "font-bold",
            match.winner_id === match.participant2?.id ? "text-green-500" : "text-muted-foreground"
          )}>
            {match.score2}
          </span>
        )}
      </div>

      {/* Статус матча */}
      {isActive && (
        <div className="bg-yellow-500 text-yellow-950 text-xs font-medium text-center py-1">
          🔴 LIVE
        </div>
      )}
    </motion.div>
  );
}
```

### Хуки для работы с данными

```tsx
// apps/web/hooks/useTournaments.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Tournament, TournamentFilters } from '@/types';

export function useTournaments(filters?: TournamentFilters) {
  return useQuery({
    queryKey: ['tournaments', filters],
    queryFn: () => api.tournaments.list(filters),
    staleTime: 30 * 1000, // 30 секунд
  });
}

export function useTournament(id: number) {
  return useQuery({
    queryKey: ['tournament', id],
    queryFn: () => api.tournaments.get(id),
    enabled: !!id,
  });
}

export function useTournamentBracket(id: number) {
  return useQuery({
    queryKey: ['tournament', id, 'bracket'],
    queryFn: () => api.tournaments.getBracket(id),
    enabled: !!id,
    refetchInterval: 10 * 1000, // Обновлять каждые 10 секунд
  });
}

export function useRegisterForTournament() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ tournamentId, teamId }: { tournamentId: number; teamId?: number }) =>
      api.tournaments.register(tournamentId, teamId),
    onSuccess: (_, { tournamentId }) => {
      queryClient.invalidateQueries({ queryKey: ['tournament', tournamentId] });
      queryClient.invalidateQueries({ queryKey: ['tournaments'] });
    },
  });
}

// apps/web/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useTelegram } from './useTelegram';

type EventHandler = (data: any) => void;

export function useWebSocket() {
  const { webApp } = useTelegram();
  const socketRef = useRef<Socket | null>(null);
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());

  useEffect(() => {
    if (!webApp?.initData) return;

    const socket = io(process.env.NEXT_PUBLIC_WS_URL!, {
      auth: {
        initData: webApp.initData,
      },
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    // Пробрасываем все события в зарегистрированные обработчики
    socket.onAny((event, data) => {
      const handlers = handlersRef.current.get(event);
      if (handlers) {
        handlers.forEach(handler => handler(data));
      }
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [webApp?.initData]);

  const subscribe = useCallback((event: string, handler: EventHandler) => {
    if (!handlersRef.current.has(event)) {
      handlersRef.current.set(event, new Set());
    }
    handlersRef.current.get(event)!.add(handler);

    return () => {
      handlersRef.current.get(event)?.delete(handler);
    };
  }, []);

  const emit = useCallback((event: string, data?: any) => {
    socketRef.current?.emit(event, data);
  }, []);

  return { subscribe, emit };
}
```

---

## 7. Telegram WebApp интеграция

### Типы для Telegram WebApp

```typescript
// apps/web/types/telegram.d.ts

declare global {
  interface Window {
    Telegram?: {
      WebApp: WebApp;
    };
  }
}

export interface WebApp {
  initData: string;
  initDataUnsafe: WebAppInitData;
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  isClosingConfirmationEnabled: boolean;

  // Methods
  ready(): void;
  expand(): void;
  close(): void;
  enableClosingConfirmation(): void;
  disableClosingConfirmation(): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  showPopup(params: PopupParams, callback?: (buttonId: string) => void): void;
  showAlert(message: string, callback?: () => void): void;
  showConfirm(message: string, callback?: (confirmed: boolean) => void): void;
  showScanQrPopup(params: ScanQrPopupParams, callback?: (text: string) => boolean): void;
  closeScanQrPopup(): void;
  readTextFromClipboard(callback?: (text: string) => void): void;
  requestWriteAccess(callback?: (granted: boolean) => void): void;
  requestContact(callback?: (granted: boolean) => void): void;
  openLink(url: string, options?: { try_instant_view?: boolean }): void;
  openTelegramLink(url: string): void;
  openInvoice(url: string, callback?: (status: string) => void): void;

  // Haptic Feedback
  HapticFeedback: HapticFeedback;

  // Main Button
  MainButton: MainButton;

  // Back Button
  BackButton: BackButton;

  // Cloud Storage
  CloudStorage: CloudStorage;
}

export interface WebAppInitData {
  query_id?: string;
  user?: WebAppUser;
  receiver?: WebAppUser;
  chat?: WebAppChat;
  chat_type?: string;
  chat_instance?: string;
  start_param?: string;
  can_send_after?: number;
  auth_date: number;
  hash: string;
}

export interface WebAppUser {
  id: number;
  is_bot?: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  added_to_attachment_menu?: boolean;
  allows_write_to_pm?: boolean;
  photo_url?: string;
}

export interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
  header_bg_color?: string;
  accent_text_color?: string;
  section_bg_color?: string;
  section_header_text_color?: string;
  subtitle_text_color?: string;
  destructive_text_color?: string;
}

export interface MainButton {
  text: string;
  color: string;
  textColor: string;
  isVisible: boolean;
  isActive: boolean;
  isProgressVisible: boolean;
  setText(text: string): MainButton;
  onClick(callback: () => void): MainButton;
  offClick(callback: () => void): MainButton;
  show(): MainButton;
  hide(): MainButton;
  enable(): MainButton;
  disable(): MainButton;
  showProgress(leaveActive?: boolean): MainButton;
  hideProgress(): MainButton;
}

export interface BackButton {
  isVisible: boolean;
  onClick(callback: () => void): BackButton;
  offClick(callback: () => void): BackButton;
  show(): BackButton;
  hide(): BackButton;
}

export interface HapticFeedback {
  impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): HapticFeedback;
  notificationOccurred(type: 'error' | 'success' | 'warning'): HapticFeedback;
  selectionChanged(): HapticFeedback;
}

export interface CloudStorage {
  setItem(key: string, value: string, callback?: (error: Error | null, stored: boolean) => void): void;
  getItem(key: string, callback: (error: Error | null, value: string) => void): void;
  getItems(keys: string[], callback: (error: Error | null, values: Record<string, string>) => void): void;
  removeItem(key: string, callback?: (error: Error | null, removed: boolean) => void): void;
  removeItems(keys: string[], callback?: (error: Error | null, removed: boolean) => void): void;
  getKeys(callback: (error: Error | null, keys: string[]) => void): void;
}
```

### Интеграция с UI компонентами

```tsx
// apps/web/components/layout/TelegramMainButton.tsx
'use client';

import { useEffect } from 'react';
import { useTelegram } from '@/hooks/useTelegram';

interface Props {
  text: string;
  onClick: () => void;
  visible?: boolean;
  disabled?: boolean;
  loading?: boolean;
}

export function TelegramMainButton({
  text,
  onClick,
  visible = true,
  disabled = false,
  loading = false,
}: Props) {
  const { webApp } = useTelegram();

  useEffect(() => {
    if (!webApp?.MainButton) return;

    const btn = webApp.MainButton;

    btn.setText(text);

    if (visible) {
      btn.show();
    } else {
      btn.hide();
    }

    if (disabled) {
      btn.disable();
    } else {
      btn.enable();
    }

    if (loading) {
      btn.showProgress();
    } else {
      btn.hideProgress();
    }

    btn.onClick(onClick);

    return () => {
      btn.offClick(onClick);
      btn.hide();
    };
  }, [webApp, text, visible, disabled, loading, onClick]);

  return null;
}

// apps/web/components/layout/TelegramBackButton.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/hooks/useTelegram';

interface Props {
  onBack?: () => void;
}

export function TelegramBackButton({ onBack }: Props) {
  const { webApp } = useTelegram();
  const router = useRouter();

  useEffect(() => {
    if (!webApp?.BackButton) return;

    const handleBack = () => {
      if (onBack) {
        onBack();
      } else {
        router.back();
      }
    };

    webApp.BackButton.onClick(handleBack);
    webApp.BackButton.show();

    return () => {
      webApp.BackButton.offClick(handleBack);
      webApp.BackButton.hide();
    };
  }, [webApp, onBack, router]);

  return null;
}

// apps/web/hooks/useHaptic.ts
import { useCallback } from 'react';
import { useTelegram } from './useTelegram';

export function useHaptic() {
  const { webApp } = useTelegram();

  const impact = useCallback((style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' = 'medium') => {
    webApp?.HapticFeedback?.impactOccurred(style);
  }, [webApp]);

  const notification = useCallback((type: 'error' | 'success' | 'warning') => {
    webApp?.HapticFeedback?.notificationOccurred(type);
  }, [webApp]);

  const selection = useCallback(() => {
    webApp?.HapticFeedback?.selectionChanged();
  }, [webApp]);

  return { impact, notification, selection };
}
```

### Адаптивная тема

```css
/* apps/web/styles/telegram-theme.css */

:root {
  /* Цвета по умолчанию (fallback) */
  --tg-theme-bg-color: #ffffff;
  --tg-theme-text-color: #000000;
  --tg-theme-hint-color: #999999;
  --tg-theme-link-color: #2481cc;
  --tg-theme-button-color: #2481cc;
  --tg-theme-button-text-color: #ffffff;
  --tg-theme-secondary-bg-color: #f0f0f0;
  --tg-theme-header-bg-color: #ffffff;
  --tg-theme-accent-text-color: #2481cc;
  --tg-theme-section-bg-color: #ffffff;
  --tg-theme-section-header-text-color: #999999;
  --tg-theme-subtitle-text-color: #999999;
  --tg-theme-destructive-text-color: #ff3b30;
}

/* Тёмная тема */
[data-theme="dark"] {
  --tg-theme-bg-color: #18222d;
  --tg-theme-text-color: #ffffff;
  --tg-theme-hint-color: #708499;
  --tg-theme-link-color: #6ab2f2;
  --tg-theme-button-color: #2481cc;
  --tg-theme-button-text-color: #ffffff;
  --tg-theme-secondary-bg-color: #232e3c;
  --tg-theme-header-bg-color: #18222d;
}

/* Маппинг на TailwindCSS переменные */
@layer base {
  :root {
    --background: var(--tg-theme-bg-color);
    --foreground: var(--tg-theme-text-color);
    --muted: var(--tg-theme-secondary-bg-color);
    --muted-foreground: var(--tg-theme-hint-color);
    --popover: var(--tg-theme-section-bg-color);
    --popover-foreground: var(--tg-theme-text-color);
    --card: var(--tg-theme-section-bg-color);
    --card-foreground: var(--tg-theme-text-color);
    --border: color-mix(in srgb, var(--tg-theme-hint-color) 20%, transparent);
    --input: var(--tg-theme-secondary-bg-color);
    --primary: var(--tg-theme-button-color);
    --primary-foreground: var(--tg-theme-button-text-color);
    --secondary: var(--tg-theme-secondary-bg-color);
    --secondary-foreground: var(--tg-theme-text-color);
    --accent: var(--tg-theme-accent-text-color);
    --accent-foreground: var(--tg-theme-button-text-color);
    --destructive: var(--tg-theme-destructive-text-color);
    --destructive-foreground: #ffffff;
    --ring: var(--tg-theme-link-color);
  }
}
```

---

## 8. Аутентификация и безопасность

### Валидация initData на сервере

```python
# apps/api/auth/telegram.py
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote
from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException, Header, Depends

from config import settings

class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    photo_url: Optional[str] = None

def validate_init_data(init_data: str) -> Optional[TelegramUser]:
    """
    Валидация initData от Telegram WebApp.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(parse_qs(init_data, keep_blank_values=True))
        parsed = {k: v[0] for k, v in parsed.items()}

        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return None

        # Проверяем время (не старше 24 часов)
        auth_date = int(parsed.get('auth_date', 0))
        if time.time() - auth_date > 86400:
            return None

        # Сортируем и формируем строку для проверки
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(parsed.items())
        )

        # Создаём secret key
        secret_key = hmac.new(
            b'WebAppData',
            settings.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Вычисляем hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Сравниваем
        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        # Парсим данные пользователя
        user_data = json.loads(unquote(parsed.get('user', '{}')))
        return TelegramUser(**user_data)

    except Exception:
        return None


async def get_current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data")
) -> TelegramUser:
    """FastAPI dependency для получения текущего пользователя."""
    user = validate_init_data(x_telegram_init_data)
    if not user:
        raise HTTPException(401, "Invalid or expired Telegram auth")
    return user


async def get_current_user_optional(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data")
) -> Optional[TelegramUser]:
    """FastAPI dependency для опциональной авторизации."""
    if not x_telegram_init_data:
        return None
    return validate_init_data(x_telegram_init_data)


async def require_admin(
    user: TelegramUser = Depends(get_current_user)
) -> TelegramUser:
    """FastAPI dependency для проверки админских прав."""
    from database import db

    if not await db.is_admin(user.id):
        raise HTTPException(403, "Admin access required")
    return user
```

### Middleware для безопасности

```python
# apps/api/middleware/security.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Rate limiting headers
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Простой rate limiter на основе IP."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # ip -> [(timestamp, count)]

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = time.time()

        # Очищаем старые записи
        self.requests[ip] = [
            (ts, count) for ts, count in self.requests.get(ip, [])
            if now - ts < 60
        ]

        # Подсчитываем запросы за последнюю минуту
        total_requests = sum(count for _, count in self.requests.get(ip, []))

        if total_requests >= self.requests_per_minute:
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json"
            )

        # Добавляем текущий запрос
        if ip not in self.requests:
            self.requests[ip] = []
        self.requests[ip].append((now, 1))

        return await call_next(request)
```

---

## 9. Платежи (Telegram Stars)

### Создание инвойса через API

```python
# apps/api/routers/payments.py
from fastapi import APIRouter, Depends, HTTPException
from aiogram.types import LabeledPrice

from auth.telegram import get_current_user, TelegramUser
from database import db
from services.bot import get_bot

router = APIRouter()

@router.post("/tournaments/{tournament_id}/pay")
async def create_tournament_payment(
    tournament_id: int,
    user: TelegramUser = Depends(get_current_user)
):
    """Создать инвойс для оплаты участия в турнире."""
    tournament = await db.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(404, "Tournament not found")

    if tournament["entry_fee"] <= 0:
        raise HTTPException(400, "Tournament is free")

    # Проверяем что пользователь не оплатил ранее
    existing_payment = await db.get_tournament_payment(
        tournament_id, user.id
    )
    if existing_payment and existing_payment["status"] == "completed":
        raise HTTPException(400, "Already paid")

    # Создаём запись о платеже
    payment_id = await db.create_tournament_payment(
        tournament_id=tournament_id,
        telegram_id=user.id,
        amount=tournament["entry_fee"]
    )

    # Генерируем инвойс через бота
    bot = get_bot()

    # Для Mini App используем invoice link
    invoice_link = await bot.create_invoice_link(
        title=f"Участие в турнире",
        description=tournament["name"],
        payload=f"tournament_{tournament_id}_{payment_id}",
        provider_token="",  # Пустой для Stars
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label="Взнос", amount=tournament["entry_fee"])]
    )

    return {
        "payment_id": payment_id,
        "invoice_link": invoice_link,
        "amount": tournament["entry_fee"]
    }


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    user: TelegramUser = Depends(get_current_user)
):
    """Возврат средств за отмену регистрации."""
    payment = await db.get_payment(payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")

    if payment["telegram_id"] != user.id:
        raise HTTPException(403, "Not your payment")

    if payment["status"] != "completed":
        raise HTTPException(400, "Payment not completed")

    if payment.get("refunded"):
        raise HTTPException(400, "Already refunded")

    # Проверяем что турнир ещё не начался
    tournament = await db.get_tournament(payment["tournament_id"])
    if tournament["status"] not in ("draft", "open", "checkin"):
        raise HTTPException(400, "Tournament already started, refund not available")

    # Делаем refund через Telegram
    bot = get_bot()

    try:
        await bot.refund_star_payment(
            user_id=user.id,
            telegram_payment_charge_id=payment["telegram_payment_id"]
        )

        await db.update_payment(payment_id, refunded=True)

        return {"status": "refunded"}
    except Exception as e:
        raise HTTPException(500, f"Refund failed: {str(e)}")
```

### Обработка платежей на фронтенде

```tsx
// apps/web/components/tournament/PaymentButton.tsx
'use client';

import { useState } from 'react';
import { useTelegram } from '@/hooks/useTelegram';
import { useHaptic } from '@/hooks/useHaptic';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';

interface Props {
  tournamentId: number;
  amount: number;
  onSuccess: () => void;
  onError: (error: string) => void;
}

export function PaymentButton({ tournamentId, amount, onSuccess, onError }: Props) {
  const { webApp } = useTelegram();
  const { notification } = useHaptic();
  const [loading, setLoading] = useState(false);

  const handlePayment = async () => {
    if (!webApp) return;

    setLoading(true);

    try {
      // Создаём инвойс на сервере
      const { invoice_link } = await api.payments.createTournamentPayment(tournamentId);

      // Открываем инвойс в Telegram
      webApp.openInvoice(invoice_link, (status) => {
        setLoading(false);

        if (status === 'paid') {
          notification('success');
          onSuccess();
        } else if (status === 'failed') {
          notification('error');
          onError('Payment failed');
        } else if (status === 'cancelled') {
          // Пользователь отменил
        }
      });
    } catch (error) {
      setLoading(false);
      notification('error');
      onError(error instanceof Error ? error.message : 'Payment error');
    }
  };

  return (
    <Button
      onClick={handlePayment}
      disabled={loading}
      className="w-full"
    >
      {loading ? (
        'Обработка...'
      ) : (
        <>⭐ Оплатить {amount} Stars</>
      )}
    </Button>
  );
}
```

---

## 10. Real-time функции

### WebSocket сервер

```python
# apps/api/websocket/manager.py
from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # tournament_id -> set of user_ids subscribed
        self.tournament_subscriptions: Dict[int, Set[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Удаляем из подписок на турниры
        for tournament_id in list(self.tournament_subscriptions.keys()):
            self.tournament_subscriptions[tournament_id].discard(user_id)

    def subscribe_to_tournament(self, user_id: int, tournament_id: int):
        if tournament_id not in self.tournament_subscriptions:
            self.tournament_subscriptions[tournament_id] = set()
        self.tournament_subscriptions[tournament_id].add(user_id)

    def unsubscribe_from_tournament(self, user_id: int, tournament_id: int):
        if tournament_id in self.tournament_subscriptions:
            self.tournament_subscriptions[tournament_id].discard(user_id)

    async def send_to_user(self, user_id: int, message: dict):
        """Отправить сообщение конкретному пользователю."""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except:
                    pass

    async def broadcast_to_tournament(self, tournament_id: int, message: dict):
        """Отправить сообщение всем подписчикам турнира."""
        if tournament_id not in self.tournament_subscriptions:
            return

        tasks = []
        for user_id in self.tournament_subscriptions[tournament_id]:
            tasks.append(self.send_to_user(user_id, message))

        await asyncio.gather(*tasks, return_exceptions=True)


manager = ConnectionManager()


# apps/api/websocket/routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth.telegram import validate_init_data
from .manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    init_data: str = Query(...)
):
    # Валидация пользователя
    user = validate_init_data(init_data)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, user.id)

    try:
        while True:
            data = await websocket.receive_json()

            # Обработка подписки на турнир
            if data.get("type") == "subscribe":
                tournament_id = data.get("tournament_id")
                if tournament_id:
                    manager.subscribe_to_tournament(user.id, tournament_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "tournament_id": tournament_id
                    })

            elif data.get("type") == "unsubscribe":
                tournament_id = data.get("tournament_id")
                if tournament_id:
                    manager.unsubscribe_from_tournament(user.id, tournament_id)

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
```

### Публикация событий

```python
# apps/api/services/events.py
from websocket.manager import manager
from typing import Literal

EventType = Literal[
    "tournament_updated",
    "match_created",
    "match_updated",
    "match_completed",
    "participant_registered",
    "participant_unregistered",
    "tournament_started",
    "tournament_finished"
]

async def publish_tournament_event(
    tournament_id: int,
    event_type: EventType,
    data: dict = None
):
    """Публикует событие всем подписчикам турнира."""
    await manager.broadcast_to_tournament(tournament_id, {
        "type": event_type,
        "tournament_id": tournament_id,
        "data": data or {}
    })


async def publish_user_event(
    user_id: int,
    event_type: str,
    data: dict = None
):
    """Публикует событие конкретному пользователю."""
    await manager.send_to_user(user_id, {
        "type": event_type,
        "data": data or {}
    })


# Использование в роутерах
# apps/api/routers/admin/matches.py
from services.events import publish_tournament_event

@router.post("/tournaments/{tournament_id}/matches")
async def create_match(
    tournament_id: int,
    data: CreateMatchRequest,
    admin: TelegramUser = Depends(require_admin)
):
    match_id = await db.create_manual_match(
        tournament_id,
        data.participant1_id,
        data.participant2_id,
        data.participant_type,
        data.server_link
    )

    match = await db.get_match(match_id)

    # Публикуем событие всем подписчикам
    await publish_tournament_event(
        tournament_id,
        "match_created",
        {"match": match}
    )

    return match
```

### Подписка на события на фронтенде

```tsx
// apps/web/hooks/useTournamentEvents.ts
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from './useWebSocket';
import { useHaptic } from './useHaptic';

export function useTournamentEvents(tournamentId: number) {
  const { subscribe, emit } = useWebSocket();
  const queryClient = useQueryClient();
  const { notification } = useHaptic();

  useEffect(() => {
    // Подписываемся на турнир
    emit('subscribe', { tournament_id: tournamentId });

    // Обработчики событий
    const unsubMatch = subscribe('match_created', (data) => {
      // Инвалидируем кэш bracket
      queryClient.invalidateQueries({
        queryKey: ['tournament', tournamentId, 'bracket']
      });
      notification('success');
    });

    const unsubMatchUpdated = subscribe('match_updated', (data) => {
      queryClient.invalidateQueries({
        queryKey: ['tournament', tournamentId, 'bracket']
      });
    });

    const unsubMatchCompleted = subscribe('match_completed', (data) => {
      queryClient.invalidateQueries({
        queryKey: ['tournament', tournamentId, 'bracket']
      });
      queryClient.invalidateQueries({
        queryKey: ['tournament', tournamentId]
      });
      notification('success');
    });

    const unsubTournament = subscribe('tournament_updated', () => {
      queryClient.invalidateQueries({
        queryKey: ['tournament', tournamentId]
      });
    });

    return () => {
      emit('unsubscribe', { tournament_id: tournamentId });
      unsubMatch();
      unsubMatchUpdated();
      unsubMatchCompleted();
      unsubTournament();
    };
  }, [tournamentId, subscribe, emit, queryClient, notification]);
}
```

---

## 11. UI/UX дизайн

### Дизайн-система

```
Принципы:
1. Telegram-native — используем цвета и паттерны Telegram
2. Mobile-first — всё работает идеально на телефоне
3. Минимализм — только нужная информация
4. Быстрый доступ — не более 2 тапов до цели
5. Feedback — haptic и визуальный отклик на действия
```

### Wireframes основных экранов

```
┌────────────────────────┐
│ 🏆 IMMA Championship   │
├────────────────────────┤
│ [🔍 Поиск...        ]  │
│                        │
│ ┌─ Фильтры ─────────┐  │
│ │ ○ Все  ● Open     │  │
│ │ ○ 1v1  ○ 2v2 ○5v5 │  │
│ └───────────────────┘  │
│                        │
│ ┌────────────────────┐ │
│ │ 🏆 CS2 Weekly #42  │ │
│ │ 1v1 • ⭐ 50        │ │
│ │ 12/16 ████████░░  │ │
│ │ 📅 Завтра, 18:00  │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ 🏆 Team Battle     │ │
│ │ 5v5 • Бесплатно   │ │
│ │ 4/8  ████░░░░░░   │ │
│ │ 📅 Сб, 15:00      │ │
│ └────────────────────┘ │
│                        │
├────────────────────────┤
│ 🏠    🏆    👤    ⚙️   │
└────────────────────────┘
      Главная

┌────────────────────────┐
│ ← CS2 Weekly #42       │
├────────────────────────┤
│                        │
│      🏆 CS2 Weekly     │
│        16 игроков      │
│                        │
│ ┌────────────────────┐ │
│ │ 📊 Статус: Открыт  │ │
│ │ 🎮 Формат: 1v1     │ │
│ │ 📅 Старт: Завтра   │ │
│ │ ⭐ Взнос: 50 Stars │ │
│ └────────────────────┘ │
│                        │
│ 🎁 Призы:              │
│ 🥇 500 Stars           │
│ 🥈 200 Stars           │
│ 🥉 100 Stars           │
│                        │
│ 🗺️ Карты:              │
│ Mirage, Inferno, Dust2 │
│                        │
│ 👥 Участники: 12/16    │
│ ████████████░░░░       │
│                        │
│ [    👁️ Сетка    ]     │
│ [   📋 Участники  ]    │
│                        │
├────────────────────────┤
│  [ ⭐ Участвовать ]    │ <- MainButton
└────────────────────────┘
     Детали турнира

┌────────────────────────┐
│ ← Турнирная сетка      │
├────────────────────────┤
│                        │
│  Раунд 1    Полуфинал  │
│  ────────   ─────────  │
│                        │
│  ┌──────┐              │
│  │Player│──┐           │
│  │ 16:9 │  │  ┌──────┐ │
│  └──────┘  ├──│Winner│ │
│  ┌──────┐  │  │      │ │
│  │Player│──┘  └──────┘ │
│  │ 9:16 │       │      │
│  └──────┘       │      │
│                 │      │
│  ┌──────┐       │      │
│  │Player│──┐    │      │
│  │  -   │  │    │      │
│  └──────┘  ├────┘      │
│  ┌──────┐  │           │
│  │Player│──┘           │
│  │  -   │              │
│  └──────┘              │
│                        │
│  ← Свайп для прокрутки │
│                        │
└────────────────────────┘
      Турнирная сетка

┌────────────────────────┐
│ ← Мой профиль          │
├────────────────────────┤
│                        │
│        [AVATAR]        │
│       @username        │
│     ⭐ Premium          │
│                        │
│ ┌────────────────────┐ │
│ │ Никнейм: ProPlayer │ │
│ │ Steam: связан ✓    │ │
│ │ Команда: Team Name │ │
│ └────────────────────┘ │
│                        │
│ 📊 Статистика:         │
│ ┌──────┬──────┬──────┐ │
│ │  42  │  28  │  14  │ │
│ │Турнир│Побед │Пораж │ │
│ └──────┴──────┴──────┘ │
│                        │
│ 📈 Рейтинг: 1,847      │
│      #127 в топе       │
│                        │
│ 🏆 Достижения:         │
│ [🥇] [🎯] [🔥] [⚡]    │
│                        │
│ [  ✏️ Редактировать  ] │
│                        │
└────────────────────────┘
        Профиль
```

### Анимации и микровзаимодействия

```tsx
// apps/web/components/animations/index.tsx
import { motion } from 'framer-motion';

// Появление элементов списка
export const listItemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.05,
      duration: 0.3,
      ease: 'easeOut',
    },
  }),
};

// Появление карточки
export const cardVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.2 }
  },
  hover: {
    scale: 1.02,
    transition: { duration: 0.15 }
  },
  tap: {
    scale: 0.98
  },
};

// Прогресс-бар
export function AnimatedProgress({ value }: { value: number }) {
  return (
    <div className="h-2 bg-muted rounded-full overflow-hidden">
      <motion.div
        className="h-full bg-primary"
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      />
    </div>
  );
}

// Счётчик
export function AnimatedCounter({ value }: { value: number }) {
  return (
    <motion.span
      key={value}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
    >
      {value}
    </motion.span>
  );
}

// Skeleton для загрузки
export function TournamentSkeleton() {
  return (
    <div className="bg-card rounded-xl p-4 border animate-pulse">
      <div className="flex justify-between mb-3">
        <div className="h-6 bg-muted rounded w-2/3" />
        <div className="h-6 bg-muted rounded w-16" />
      </div>
      <div className="flex gap-2 mb-3">
        <div className="h-5 bg-muted rounded w-12" />
        <div className="h-5 bg-muted rounded w-16" />
      </div>
      <div className="h-2 bg-muted rounded w-full" />
    </div>
  );
}
```

---

## 12. Продвинутые функции

### 1. Push уведомления

```typescript
// apps/web/lib/notifications.ts
export async function requestNotificationPermission(): Promise<boolean> {
  // Telegram Mini App не поддерживает Web Push напрямую
  // Используем Telegram Bot для уведомлений

  const { webApp } = useTelegram();

  return new Promise((resolve) => {
    webApp?.requestWriteAccess((granted) => {
      resolve(granted);
    });
  });
}

// На бэкенде используем существующий NotificationService
```

### 2. Офлайн режим (PWA)

```typescript
// apps/web/next.config.js
const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  skipWaiting: true,
});

module.exports = withPWA({
  // ... остальная конфигурация
});

// apps/web/public/manifest.json
{
  "name": "IMMA Championship",
  "short_name": "IMMA",
  "description": "Tournament platform for CS2",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#18222d",
  "theme_color": "#2481cc",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### 3. Drag-and-drop админ-панель

```tsx
// apps/web/components/admin/MatchManager.tsx
'use client';

import { useState } from 'react';
import { DndContext, closestCenter, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface Participant {
  id: number;
  name: string;
  status: 'ready' | 'in_match' | 'eliminated';
}

export function MatchManager({ tournamentId }: { tournamentId: number }) {
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [selectedForMatch, setSelectedForMatch] = useState<number[]>([]);

  const readyParticipants = participants.filter(p => p.status === 'ready');

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over?.id === 'match-zone' && selectedForMatch.length < 2) {
      setSelectedForMatch([...selectedForMatch, active.id as number]);
    }
  };

  const createMatch = async () => {
    if (selectedForMatch.length !== 2) return;

    await api.admin.createMatch(tournamentId, {
      participant1_id: selectedForMatch[0],
      participant2_id: selectedForMatch[1],
    });

    setSelectedForMatch([]);
  };

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="grid grid-cols-2 gap-4">
        {/* Список готовых участников */}
        <div>
          <h3 className="font-semibold mb-2">Готовые к игре</h3>
          <SortableContext items={readyParticipants} strategy={verticalListSortingStrategy}>
            {readyParticipants.map(p => (
              <SortableParticipant key={p.id} participant={p} />
            ))}
          </SortableContext>
        </div>

        {/* Зона создания матча */}
        <div
          id="match-zone"
          className="border-2 border-dashed rounded-lg p-4 min-h-[200px]"
        >
          <h3 className="font-semibold mb-2">Создать матч</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Перетащите 2 участников сюда
          </p>

          {selectedForMatch.map(id => {
            const p = participants.find(p => p.id === id);
            return p ? (
              <div key={id} className="bg-primary/10 rounded p-2 mb-2">
                {p.name}
              </div>
            ) : null;
          })}

          {selectedForMatch.length === 2 && (
            <Button onClick={createMatch} className="w-full mt-4">
              ⚔️ Создать матч
            </Button>
          )}
        </div>
      </div>
    </DndContext>
  );
}

function SortableParticipant({ participant }: { participant: Participant }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: participant.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-card p-3 rounded-lg mb-2 cursor-grab active:cursor-grabbing"
    >
      {participant.name}
    </div>
  );
}
```

### 4. Статистика и графики

```tsx
// apps/web/components/stats/PlayerStats.tsx
'use client';

import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Props {
  playerId: number;
}

export function PlayerStats({ playerId }: Props) {
  const { data: stats } = usePlayerStats(playerId);
  const { data: history } = useRatingHistory(playerId);

  if (!stats) return null;

  return (
    <div className="space-y-4">
      {/* Основные метрики */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="text-2xl font-bold">{stats.tournaments}</div>
            <div className="text-xs text-muted-foreground">Турниров</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="text-2xl font-bold text-green-500">{stats.wins}</div>
            <div className="text-xs text-muted-foreground">Побед</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="text-2xl font-bold">{stats.winRate}%</div>
            <div className="text-xs text-muted-foreground">Winrate</div>
          </CardContent>
        </Card>
      </div>

      {/* График рейтинга */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">История рейтинга</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={150}>
            <AreaChart data={history}>
              <defs>
                <linearGradient id="colorRating" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <YAxis hide domain={['dataMin - 50', 'dataMax + 50']} />
              <Tooltip
                contentStyle={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)'
                }}
              />
              <Area
                type="monotone"
                dataKey="rating"
                stroke="var(--primary)"
                fillOpacity={1}
                fill="url(#colorRating)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Достижения */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Достижения</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {stats.achievements.map(achievement => (
              <div
                key={achievement.id}
                className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-2xl"
                title={achievement.name}
              >
                {achievement.icon}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## 13. Инфраструктура и деплой

### Docker конфигурация

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: imma
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: imma_championship
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U imma"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    environment:
      DATABASE_URL: postgresql://imma:${DB_PASSWORD}@postgres:5432/imma_championship
      REDIS_URL: redis://redis:6379
      BOT_TOKEN: ${BOT_TOKEN}
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"

  # Telegram Bot (уведомления)
  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile.bot
    environment:
      DATABASE_URL: postgresql://imma:${DB_PASSWORD}@postgres:5432/imma_championship
      REDIS_URL: redis://redis:6379
      BOT_TOKEN: ${BOT_TOKEN}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Celery Worker
  celery:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    command: celery -A tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://imma:${DB_PASSWORD}@postgres:5432/imma_championship
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
      - postgres

  # Nginx (reverse proxy)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

### Dockerfile для API

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY apps/api .
COPY packages/database ./packages/database

# Запуск
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r apps/api/requirements.txt
          pip install pytest pytest-asyncio

      - name: Run tests
        run: pytest apps/api/tests

  build-api:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile.api
          push: true
          tags: ghcr.io/${{ github.repository }}/api:latest

  build-web:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install and Build
        working-directory: apps/web
        run: |
          npm ci
          npm run build

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: apps/web

  deploy:
    needs: [build-api, build-web]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/imma
            docker-compose pull
            docker-compose up -d
```

---

## 14. Монетизация

### Модель доходов

```
1. Комиссия с турниров (5-10% от entry fee)
2. Premium подписка (расширенная статистика, косметика)
3. Брендированные турниры (B2B)
4. Рекламные интеграции
5. API для третьих сторон
```

### Premium функции

```typescript
// apps/api/routers/subscription.py

PREMIUM_FEATURES = {
    "free": {
        "tournaments_per_month": 10,
        "team_size": 1,
        "stats_history_days": 30,
        "custom_avatar_frame": False,
        "priority_support": False,
    },
    "premium": {
        "price_stars": 100,  # в месяц
        "tournaments_per_month": -1,  # unlimited
        "team_size": 5,
        "stats_history_days": 365,
        "custom_avatar_frame": True,
        "priority_support": True,
        "early_access": True,
        "exclusive_tournaments": True,
    }
}
```

---

## 15. Roadmap

### Q1 2025: MVP

```
Месяц 1:
□ REST API на базе существующего кода
□ Базовый frontend (список турниров, детали)
□ Telegram WebApp интеграция
□ Аутентификация через initData

Месяц 2:
□ Регистрация на турниры
□ Профиль пользователя
□ Команды
□ Платежи (Stars)

Месяц 3:
□ Интерактивная турнирная сетка
□ Real-time обновления
□ Админ-панель
□ Бета-тестирование
```

### Q2 2025: Growth

```
□ Статистика и графики
□ Достижения
□ Лидерборды
□ PWA + офлайн
□ Push уведомления
□ Мультиязычность (EN, UA, KZ)
```

### Q3 2025: Scale

```
□ ELO рейтинговая система
□ Double Elimination формат
□ Swiss System формат
□ Premium подписки
□ API для третьих сторон
□ Discord интеграция
```

### Q4 2025: Expansion

```
□ Мобильное приложение (React Native)
□ Расширенная косметика
□ Клановая система
□ Fantasy League
□ Prediction Market
□ CS2 Server Integration
```

---

## Заключение

Трансформация IMMA Bot в Mini App — это эволюционный шаг, который позволит:

1. **Улучшить UX** — богатый визуальный интерфейс вместо текстовых сообщений
2. **Масштабироваться** — архитектура готова к росту пользователей
3. **Монетизироваться** — больше возможностей для Premium функций
4. **Конкурировать** — уникальный продукт для Telegram экосистемы

Ключевой принцип: **итеративная разработка**. Начинаем с MVP, получаем фидбек, улучшаем.

---

*Документ создан: Ноябрь 2025*
*Версия: 1.0*
