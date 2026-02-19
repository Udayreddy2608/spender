from datetime import date, timedelta, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from models import Goal, Expense, WeeklyLimit, BalanceLedger, WeeklyHistory
from schemas import ProjectionOut, BalanceState, AnalyticsOut, WeeklyHistoryOut, CategoryBreakdownItem, DailySpendItem


def get_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def get_or_create_weekly_limit(db: Session, goal: Optional[Goal], ref_date: date = None) -> WeeklyLimit:
    if ref_date is None:
        ref_date = date.today()
    week_start = get_week_start(ref_date)
    wl = db.query(WeeklyLimit).filter(WeeklyLimit.week_start_date == week_start).first()
    if not wl:
        cap = 4000
        if goal:
            usable = goal.monthly_income - goal.emi - goal.rent
            cap = max(1000, usable // 4)
        wl = WeeklyLimit(week_start_date=week_start, weekly_cap=cap, spent_this_week=0)
        db.add(wl)
        db.commit()
        db.refresh(wl)
    return wl


def compute_clothing_spent(db: Session) -> int:
    rows = db.query(Expense).filter(Expense.category == "clothes").all()
    return sum(r.amount for r in rows)


def compute_cc_total(db: Session) -> int:
    """Sum of all credit-card expenses (never deducted from balance)."""
    rows = db.query(Expense).filter(Expense.payment_mode == "card").all()
    return sum(r.amount for r in rows)


def compute_total_saved(db: Session, goal: Goal) -> int:
    if not goal:
        return 0
    today = date.today()
    created = goal.created_at.date() if hasattr(goal.created_at, 'date') else goal.created_at
    months_elapsed = max(0, (today.year - created.year) * 12 + (today.month - created.month))
    usable = goal.monthly_income - goal.emi - goal.rent
    total_income_received = usable * months_elapsed
    total_expenses = sum(e.amount for e in db.query(Expense).all())
    base = getattr(goal, 'initial_savings', 0) or 0
    return max(0, base + total_income_received - total_expenses)


def compute_projection(db: Session, goal: Goal) -> ProjectionOut:
    today    = date.today()
    deadline = goal.deadline
    days_left  = (deadline - today).days
    months_left = max(0.01, days_left / 30.44)

    total_saved      = compute_total_saved(db, goal)
    remaining_target = max(0, goal.target_amount - total_saved)

    required_monthly_saving = remaining_target / months_left if months_left > 0 else remaining_target
    required_weekly_saving  = required_monthly_saving / 4.33

    usable = goal.monthly_income - goal.emi - goal.rent
    predicted_june1_balance = total_saved + int(usable * months_left)

    if required_monthly_saving <= usable * 0.6:
        status = "On Track"
    elif required_monthly_saving <= usable * 0.85:
        status = "Slight Risk"
    else:
        status = "High Risk"

    return ProjectionOut(
        total_saved=total_saved,
        remaining_target=remaining_target,
        months_left=round(months_left, 1),
        days_left=days_left,
        required_monthly_saving=round(required_monthly_saving, 0),
        required_weekly_saving=round(required_weekly_saving, 0),
        predicted_june1_balance=predicted_june1_balance,
        status=status,
    )


# ─── Balance Ledger Engine ────────────────────────────────────────────────────

def compute_balance_state(
    db: Session,
    goal: Optional[Goal],
    weekly_limit: Optional[WeeklyLimit],
) -> Optional[BalanceState]:
    """
    Current balance = last 'set' amount
                    + sum of 'credit' entries after that set
                    - sum of 'debit'  entries after that set
    """
    # Find the most recent 'set' entry
    last_set = (
        db.query(BalanceLedger)
        .filter(BalanceLedger.type == "set")
        .order_by(BalanceLedger.recorded_at.desc())
        .first()
    )
    if not last_set:
        return None

    # Sum credits and debits since that set
    since = last_set.recorded_at
    rows_since = (
        db.query(BalanceLedger)
        .filter(BalanceLedger.recorded_at > since)
        .all()
    )
    total_credits = sum(r.amount for r in rows_since if r.type == "credit")
    total_debits  = sum(r.amount for r in rows_since if r.type == "debit")

    current_balance = last_set.amount + total_credits - total_debits

    # ── Analysis ──────────────────────────────────────────────────────────────
    today = date.today()

    monthly_fixed = (goal.emi + goal.rent) if goal else 0
    usable_balance = max(0, current_balance - monthly_fixed)

    # How much must be locked for the goal this month
    locked_for_goal = 0
    if goal:
        proj = compute_projection(db, goal)
        locked_for_goal = max(0, int(proj.required_monthly_saving))

    # Weekly remaining
    weekly_remaining = 0
    burn_rate_pct    = 0.0
    if weekly_limit:
        weekly_remaining = max(0, weekly_limit.weekly_cap - weekly_limit.spent_this_week)
        burn_rate_pct = round(
            (weekly_limit.spent_this_week / weekly_limit.weekly_cap * 100)
            if weekly_limit.weekly_cap > 0 else 0,
            1,
        )

    # Days until next salary (1st of next month)
    if today.month == 12:
        next_salary = date(today.year + 1, 1, 1)
    else:
        next_salary = date(today.year, today.month + 1, 1)
    days_until_next_salary = max(1, (next_salary - today).days)

    # Safe to spend = usable balance minus what's locked for goal
    safe_to_spend = max(0, usable_balance - locked_for_goal)

    # Daily budget
    daily_budget = safe_to_spend // days_until_next_salary

    # Overspend risk
    days_in_week_elapsed = today.weekday() + 1
    if weekly_limit and days_in_week_elapsed > 0 and weekly_limit.spent_this_week > 0:
        daily_burn = weekly_limit.spent_this_week / days_in_week_elapsed
        projected  = daily_burn * days_until_next_salary
        overspend_risk = projected > usable_balance
    else:
        overspend_risk = False

    # Health score — based on ratio of current_balance to target_amount (goal progress health)
    # Use a multi-factor score: balance health relative to monthly income + goal progress
    if goal and goal.monthly_income > 0:
        # Factor 1: safe-to-spend vs monthly income (40%)
        spend_ratio = min(1.0, safe_to_spend / goal.monthly_income)
        # Factor 2: current balance vs (monthly_income * 3) as emergency fund benchmark (40%)
        balance_ratio = min(1.0, current_balance / max(1, goal.monthly_income * 3))
        # Factor 3: weekly burn rate (20%) — lower burn = healthier
        burn_factor = max(0.0, 1.0 - burn_rate_pct / 100)
        score = int((spend_ratio * 0.4 + balance_ratio * 0.4 + burn_factor * 0.2) * 100)
    else:
        # No goal set — just use balance vs a reasonable threshold
        score = min(100, int(current_balance / 50000 * 100)) if current_balance > 0 else 0
    score = max(0, min(100, score))
    health = "Healthy" if score >= 60 else ("Tight" if score >= 30 else "Critical")

    return BalanceState(
        current_balance=current_balance,
        last_set_amount=last_set.amount,
        last_set_at=last_set.recorded_at,
        last_set_note=last_set.note,
        total_credits_since=total_credits,
        total_debits_since=total_debits,
        usable_balance=usable_balance,
        safe_to_spend=safe_to_spend,
        locked_for_goal=locked_for_goal,
        weekly_remaining=weekly_remaining,
        burn_rate_pct=burn_rate_pct,
        days_until_next_salary=days_until_next_salary,
        balance_health=health,
        balance_health_score=score,
        daily_budget=daily_budget,
        overspend_risk=overspend_risk,
    )


# ─── Analytics Engine ─────────────────────────────────────────────────────────

def compute_analytics(db: Session, goal: Optional[Goal]) -> AnalyticsOut:
    today = date.today()

    # ── Weekly history (all WeeklyLimit rows, sorted) ──────────────────────
    all_wl = db.query(WeeklyLimit).order_by(WeeklyLimit.week_start_date.asc()).all()
    current_week_start = get_week_start(today)

    weekly_history: List[WeeklyHistoryOut] = []
    current_week_underspend = None

    for wl in all_wl:
        saved = wl.weekly_cap - wl.spent_this_week
        if wl.week_start_date == current_week_start:
            current_week_underspend = saved  # positive = under, negative = over
        weekly_history.append(WeeklyHistoryOut(
            week_start_date=wl.week_start_date,
            weekly_cap=wl.weekly_cap,
            spent=wl.spent_this_week,
            saved=saved,
        ))

    # ── Category breakdown (all time) ──────────────────────────────────────
    expenses = db.query(Expense).all()
    cat_map: dict = {}
    for e in expenses:
        if e.category not in cat_map:
            cat_map[e.category] = {"total": 0, "count": 0}
        cat_map[e.category]["total"] += e.amount
        cat_map[e.category]["count"] += 1

    category_breakdown = [
        CategoryBreakdownItem(category=cat, total=v["total"], count=v["count"])
        for cat, v in sorted(cat_map.items(), key=lambda x: -x[1]["total"])
    ]

    # ── Daily spend last 30 days ────────────────────────────────────────────
    cutoff = today - timedelta(days=30)
    recent = [e for e in expenses if e.date >= cutoff]
    day_map: dict = {}
    for e in recent:
        key = e.date
        day_map[key] = day_map.get(key, 0) + e.amount

    daily_spend_30d = [
        DailySpendItem(date=d, total=t)
        for d, t in sorted(day_map.items())
    ]

    # ── Aggregates ─────────────────────────────────────────────────────────
    total_spent_all = sum(e.amount for e in expenses)
    completed_weeks = [w for w in weekly_history if w.week_start_date < current_week_start]
    avg_weekly_spend = (
        sum(w.spent for w in completed_weeks) / len(completed_weeks)
        if completed_weeks else 0.0
    )

    underspends = [w.saved for w in completed_weeks if w.saved > 0]
    overspends  = [abs(w.saved) for w in completed_weeks if w.saved < 0]

    best_week_saved     = max(underspends) if underspends else None
    worst_week_overspend = max(overspends) if overspends else None

    # ── Payment mode totals ──────────────────────────────────────────────────────
    cc_total  = sum(e.amount for e in expenses if getattr(e, 'payment_mode', 'upi') == 'card')
    upi_total = sum(e.amount for e in expenses if getattr(e, 'payment_mode', 'upi') != 'card')

    return AnalyticsOut(
        weekly_history=weekly_history,
        category_breakdown=category_breakdown,
        daily_spend_30d=daily_spend_30d,
        total_spent_all=total_spent_all,
        avg_weekly_spend=round(avg_weekly_spend, 0),
        best_week_saved=best_week_saved,
        worst_week_overspend=worst_week_overspend,
        current_week_underspend=current_week_underspend,
        cc_total=cc_total,
        upi_total=upi_total,
    )
