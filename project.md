# Mission-Based Budgeting App (Private Tool) -- Project Requirements

## 1. Project Overview

A goal-driven budgeting dashboard designed to enforce financial
discipline. Primary use case: Track and achieve a fixed financial target
(₹1,25,000 by June 1) while controlling weekly spending and category
caps.

This is NOT a generic expense tracker. It is a constraint-based
financial mission system.

------------------------------------------------------------------------

## 2. Core Objectives

The app must answer instantly:

1.  Am I on track for my financial goal?
2.  How much can I spend this week?
3.  Will this expense delay my goal?

------------------------------------------------------------------------

## 3. Tech Stack (V1 -- Private Tool)

Backend: - FastAPI - SQLite (local) - SQLAlchemy ORM

Frontend: - Simple React dashboard (or basic HTML + JS for V1)

Deployment: - Localhost (Docker optional)

------------------------------------------------------------------------

## 4. Core Data Models

### 4.1 Goals Table

-   id
-   target_amount (int)
-   deadline (date)
-   monthly_income (int)
-   emi (int)
-   rent (int)
-   clothing_cap (int)
-   created_at (datetime)

------------------------------------------------------------------------

### 4.2 Expenses Table

-   id
-   amount (int)
-   category (enum: fixed, living, clothing, misc)
-   date (date)
-   note (text)
-   mood (optional: calm, stressed, bored, happy)

------------------------------------------------------------------------

### 4.3 WeeklyLimit Table

-   week_start_date (date)
-   weekly_cap (int)
-   spent_this_week (int)

------------------------------------------------------------------------

## 5. Core Functional Requirements

### 5.1 Goal Projection Engine

Must calculate:

-   Total invested so far
-   Remaining target
-   Months left until deadline
-   Required monthly saving
-   Required weekly saving

Output status: - On Track - Slight Risk - High Risk

------------------------------------------------------------------------

### 5.2 Weekly Budget Engine

-   Weekly cap: ₹4,000 (configurable)
-   Reset every Monday
-   Track weekly spending
-   Carry forward unused balance
-   Show warning if exceeded

------------------------------------------------------------------------

### 5.3 Clothing Cap Tracker

-   Total clothing cap: ₹10,000
-   Show remaining clothing budget
-   Hard warning if exceeded

------------------------------------------------------------------------

### 5.4 Expense Logging

Expense logging must: - Take less than 5 seconds - Auto-update weekly
usage - Update goal projection - Store optional mood tag

------------------------------------------------------------------------

### 5.5 Expense Simulation Feature (Important)

Before logging expense:

User enters amount. System returns: - Weekly balance after expense -
Remaining clothing cap (if applicable) - Updated goal projection - Risk
level

------------------------------------------------------------------------

## 6. Dashboard Requirements

The dashboard must show:

-   Target progress bar
-   Total invested so far
-   Remaining amount
-   Days left until deadline
-   Weekly remaining balance
-   Clothing remaining balance
-   Risk status
-   Predicted June 1 balance

No complex pie charts in V1.

------------------------------------------------------------------------

## 7. Business Logic (Core Math)

Monthly usable income: monthly_income - emi - rent

Remaining target: target_amount - total_saved

Required monthly saving: remaining_target / months_left

Weekly limit: monthly_living_budget / 4

------------------------------------------------------------------------

## 8. Non-Functional Requirements

-   Minimal UI clutter
-   Fast loading (\<1 sec locally)
-   Simple clean design
-   Mobile responsive (basic level)
-   All calculations must be deterministic and testable

------------------------------------------------------------------------

## 9. Future Enhancements (Post-V1)

-   SMS auto bank parsing (India)
-   EMI amortization view
-   Savings velocity graph
-   Risk score based on spending trend
-   Habit streak (no-impulse days)
-   Notification reminders

------------------------------------------------------------------------

## 10. Success Criteria

The tool is successful if:

-   User logs expenses daily
-   Weekly cap prevents overspending
-   June 1 goal is achieved without stress
-   Emotional spending reduces

------------------------------------------------------------------------

End of Project Requirements
