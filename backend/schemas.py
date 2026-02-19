from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class CategoryEnum(str, Enum):
    food          = "food"
    travel        = "travel"
    clothes       = "clothes"
    skincare      = "skincare"
    studies       = "studies"
    rent          = "rent"
    emi           = "emi"
    health        = "health"
    subscriptions = "subscriptions"
    misc          = "misc"


class MoodEnum(str, Enum):
    calm     = "calm"
    stressed = "stressed"
    bored    = "bored"
    happy    = "happy"


# ─── Goal ─────────────────────────────────────────────────────────────────────
class GoalCreate(BaseModel):
    target_amount:  int
    deadline:       date
    monthly_income: int
    emi:            int = 0
    rent:           int = 0
    clothing_cap:   int = 10000
    initial_savings: int = 0


class GoalOut(GoalCreate):
    id:         int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Expense ──────────────────────────────────────────────────────────────────
class ExpenseCreate(BaseModel):
    amount:       int
    category:     CategoryEnum
    date:         date
    note:         Optional[str]      = None
    mood:         Optional[MoodEnum] = None
    payment_mode: str                = "upi"   # 'upi' | 'card'


class ExpenseOut(ExpenseCreate):
    id: int

    class Config:
        from_attributes = True


# ─── WeeklyLimit ──────────────────────────────────────────────────────────────
class WeeklyLimitOut(BaseModel):
    week_start_date: date
    weekly_cap:      int
    spent_this_week: int

    class Config:
        from_attributes = True


# ─── Balance Ledger ───────────────────────────────────────────────────────────
class BalanceSetRequest(BaseModel):
    """Manually set the current balance (e.g. after checking bank app)."""
    amount: int
    note:   Optional[str] = None


class BalanceCreditRequest(BaseModel):
    """Add money: salary, transfer, cashback, etc."""
    amount: int
    note:   Optional[str] = None


class BalanceLedgerOut(BaseModel):
    id:          int
    type:        str        # 'set' | 'credit' | 'debit'
    amount:      int
    note:        Optional[str]
    recorded_at: datetime

    class Config:
        from_attributes = True


class BalanceState(BaseModel):
    """Computed current balance + full analysis."""
    current_balance:       int
    last_set_amount:       int
    last_set_at:           Optional[datetime]
    last_set_note:         Optional[str]
    total_credits_since:   int
    total_debits_since:    int
    # Analysis
    usable_balance:        int
    safe_to_spend:         int
    locked_for_goal:       int
    weekly_remaining:      int
    burn_rate_pct:         float
    days_until_next_salary: int
    balance_health:        str   # Healthy / Tight / Critical
    balance_health_score:  int   # 0–100
    daily_budget:          int
    overspend_risk:        bool


# ─── Dashboard ────────────────────────────────────────────────────────────────
class ProjectionOut(BaseModel):
    total_saved:              int
    remaining_target:         int
    months_left:              float
    days_left:                int
    required_monthly_saving:  float
    required_weekly_saving:   float
    predicted_june1_balance:  int
    status:                   str   # On Track / Slight Risk / High Risk


class DashboardOut(BaseModel):
    goal:               Optional[GoalOut]
    projection:         Optional[ProjectionOut]
    weekly:             Optional[WeeklyLimitOut]
    clothing_spent:     int
    clothing_remaining: int
    balance_state:      Optional[BalanceState]
    cc_total:           int   # total unpaid credit-card spend


# ─── Simulation ───────────────────────────────────────────────────────────────
class SimulateRequest(BaseModel):
    amount:   int
    category: CategoryEnum


class SimulateOut(BaseModel):
    weekly_balance_after:      int
    actual_balance_after:      Optional[int]
    clothing_remaining_after:  Optional[int]
    updated_projection_status: str
    risk_level:                str
    safe_to_spend_after:       Optional[int]


# ─── Analytics ────────────────────────────────────────────────────────────────
class WeeklyHistoryOut(BaseModel):
    week_start_date: date
    weekly_cap:      int
    spent:           int
    saved:           int

    class Config:
        from_attributes = True


class CategoryBreakdownItem(BaseModel):
    category: str
    total:    int
    count:    int


class DailySpendItem(BaseModel):
    date:  date
    total: int


class AnalyticsOut(BaseModel):
    weekly_history:          List[WeeklyHistoryOut]
    category_breakdown:      List[CategoryBreakdownItem]
    daily_spend_30d:         List[DailySpendItem]
    total_spent_all:         int
    avg_weekly_spend:        float
    best_week_saved:         Optional[int]
    worst_week_overspend:    Optional[int]
    current_week_underspend: Optional[int]
    cc_total:                int   # total credit-card spend (all time)
    upi_total:               int   # total UPI spend (all time)
