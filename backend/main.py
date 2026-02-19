from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import os

from database import get_db, init_db
from models import Goal, Expense, WeeklyLimit, BalanceLedger
from schemas import (
    GoalCreate, GoalOut,
    ExpenseCreate, ExpenseOut,
    WeeklyLimitOut,
    BalanceSetRequest, BalanceCreditRequest, BalanceLedgerOut,
    DashboardOut,
    SimulateRequest, SimulateOut,
    AnalyticsOut,
)
from engine import (
    compute_projection,
    compute_clothing_spent,
    compute_cc_total,
    get_or_create_weekly_limit,
    compute_balance_state,
    compute_analytics,
)

app = FastAPI(title="Spender — Mission Budget API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ─── GOAL ─────────────────────────────────────────────────────────────────────

@app.get("/api/goal", response_model=GoalOut)
def get_goal(db: Session = Depends(get_db)):
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    if not goal:
        raise HTTPException(status_code=404, detail="No goal set")
    return goal


@app.post("/api/goal", response_model=GoalOut)
def set_goal(payload: GoalCreate, db: Session = Depends(get_db)):
    db.query(Goal).delete()
    goal = Goal(**payload.dict())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


# ─── EXPENSES ─────────────────────────────────────────────────────────────────

@app.get("/api/expenses", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.date.desc(), Expense.id.desc()).all()


@app.post("/api/expenses", response_model=ExpenseOut)
def add_expense(payload: ExpenseCreate, db: Session = Depends(get_db)):
    expense = Expense(**payload.dict())
    db.add(expense)
    db.commit()

    # Update weekly spending (counts for both UPI and card)
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    wl = get_or_create_weekly_limit(db, goal, payload.date)
    wl.spent_this_week += payload.amount
    db.commit()

    # Auto-debit from balance ledger ONLY for UPI payments
    if payload.payment_mode != "card":
        has_set = db.query(BalanceLedger).filter(BalanceLedger.type == "set").first()
        if has_set:
            debit = BalanceLedger(
                type="debit",
                amount=payload.amount,
                note=f"[UPI] {payload.note or payload.category}",
            )
            db.add(debit)
            db.commit()

    db.refresh(expense)
    return expense


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Reverse the weekly debit
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    wl = get_or_create_weekly_limit(db, goal, expense.date)
    wl.spent_this_week = max(0, wl.spent_this_week - expense.amount)

    # Reverse the balance debit ONLY for UPI payments
    mode = getattr(expense, 'payment_mode', 'upi') or 'upi'
    if mode != "card":
        has_set = db.query(BalanceLedger).filter(BalanceLedger.type == "set").first()
        if has_set:
            reversal = BalanceLedger(
                type="credit",
                amount=expense.amount,
                note=f"Reversal [UPI]: {expense.note or expense.category}",
            )
            db.add(reversal)

    db.delete(expense)
    db.commit()
    return {"ok": True}


# ─── WEEKLY ───────────────────────────────────────────────────────────────────

@app.get("/api/weekly", response_model=WeeklyLimitOut)
def get_weekly(db: Session = Depends(get_db)):
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    wl = get_or_create_weekly_limit(db, goal)
    return wl


@app.patch("/api/weekly/cap")
def update_weekly_cap(cap: int, db: Session = Depends(get_db)):
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    wl = get_or_create_weekly_limit(db, goal)
    wl.weekly_cap = cap
    db.commit()
    return {"ok": True, "new_cap": cap}


# ─── BALANCE LEDGER ───────────────────────────────────────────────────────────

@app.post("/api/balance/set", response_model=BalanceLedgerOut)
def set_balance(payload: BalanceSetRequest, db: Session = Depends(get_db)):
    """Manually set the current balance (e.g. after checking bank app)."""
    entry = BalanceLedger(type="set", amount=payload.amount, note=payload.note)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.post("/api/balance/credit", response_model=BalanceLedgerOut)
def add_credit(payload: BalanceCreditRequest, db: Session = Depends(get_db)):
    """Add money: salary, transfer, cashback, gift, etc."""
    # Check a base balance exists
    has_set = db.query(BalanceLedger).filter(BalanceLedger.type == "set").first()
    if not has_set:
        raise HTTPException(
            status_code=400,
            detail="Set your current balance first before adding credits."
        )
    entry = BalanceLedger(type="credit", amount=payload.amount, note=payload.note)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.get("/api/balance/ledger", response_model=list[BalanceLedgerOut])
def get_ledger(db: Session = Depends(get_db)):
    return (
        db.query(BalanceLedger)
        .order_by(BalanceLedger.recorded_at.desc())
        .limit(50)
        .all()
    )


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.get("/api/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    goal            = db.query(Goal).order_by(Goal.id.desc()).first()
    projection      = compute_projection(db, goal) if goal else None
    weekly          = get_or_create_weekly_limit(db, goal) if goal else None
    clothing_spent  = compute_clothing_spent(db)
    clothing_cap    = goal.clothing_cap if goal else 10000
    clothing_remaining = max(0, clothing_cap - clothing_spent)
    balance_state   = compute_balance_state(db, goal, weekly)
    cc_total        = compute_cc_total(db)

    return DashboardOut(
        goal=goal,
        projection=projection,
        weekly=weekly,
        clothing_spent=clothing_spent,
        clothing_remaining=clothing_remaining,
        balance_state=balance_state,
        cc_total=cc_total,
    )


# ─── SIMULATE ─────────────────────────────────────────────────────────────────

@app.post("/api/simulate", response_model=SimulateOut)
def simulate(payload: SimulateRequest, db: Session = Depends(get_db)):
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    wl   = get_or_create_weekly_limit(db, goal)

    weekly_balance_after = wl.weekly_cap - wl.spent_this_week - payload.amount

    clothing_spent = compute_clothing_spent(db)
    clothing_cap   = goal.clothing_cap if goal else 10000
    clothing_remaining_after = None
    if payload.category == "clothes":
        clothing_remaining_after = max(0, clothing_cap - clothing_spent - payload.amount)

    # Balance impact
    balance_state = compute_balance_state(db, goal, wl)
    actual_balance_after = None
    safe_to_spend_after  = None
    if balance_state:
        actual_balance_after = balance_state.current_balance - payload.amount
        if goal:
            monthly_fixed = goal.emi + goal.rent
            usable_after  = max(0, actual_balance_after - monthly_fixed)
            safe_to_spend_after = max(0, usable_after - balance_state.locked_for_goal)

    # Projection impact
    if goal:
        from engine import compute_total_saved
        total_saved = compute_total_saved(db, goal)
        remaining   = max(0, goal.target_amount - total_saved)
        days_left   = (goal.deadline - date.today()).days
        months_left = max(0.01, days_left / 30.44)
        usable      = goal.monthly_income - goal.emi - goal.rent
        req         = (remaining + payload.amount) / months_left

        if req <= usable * 0.6:
            status, risk = "On Track", "Low"
        elif req <= usable * 0.85:
            status, risk = "Slight Risk", "Medium"
        else:
            status, risk = "High Risk", "High"
    else:
        status, risk = "Unknown", "Unknown"

    return SimulateOut(
        weekly_balance_after=weekly_balance_after,
        actual_balance_after=actual_balance_after,
        clothing_remaining_after=clothing_remaining_after,
        updated_projection_status=status,
        risk_level=risk,
        safe_to_spend_after=safe_to_spend_after,
    )


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@app.get("/api/analytics", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db)):
    goal = db.query(Goal).order_by(Goal.id.desc()).first()
    return compute_analytics(db, goal)


# ─── STATIC FRONTEND ────────────────────────────────────────────────────────────────

frontend_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
)

if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=frontend_path), name="assets")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/analytics")
    def serve_analytics():
        return FileResponse(os.path.join(frontend_path, "analytics.html"))

    @app.get("/style.css")
    def serve_css():
        return FileResponse(os.path.join(frontend_path, "style.css"), media_type="text/css")

    @app.get("/app.js")
    def serve_js():
        return FileResponse(os.path.join(frontend_path, "app.js"), media_type="application/javascript")

    @app.get("/analytics.js")
    def serve_analytics_js():
        return FileResponse(os.path.join(frontend_path, "analytics.js"), media_type="application/javascript")
