# Spender — Mission Budget

A personal finance application designed to help you track spending against specific goals, manage recurring expenses, and visualize your financial health.

## Features

- **Goal Tracking**: Set and track progress towards financial goals.
- **Expense Management**: Log expenses with categories and payment modes.
- **Weekly Limits**: Monitor weekly spending against a cap.
- **Balance Ledger**: Maintain a ledger of your current balance, including credits.
- **Recurring Expenses**: Manage monthly fixed costs like Rent and EMI.
- **Simulations**: Estimate the impact of potential expenses on your goals.
- **Analytics**: Visualize spending trends and category breakdowns.

## Tech Stack

- **Backend**: Python (FastAPI), SQLAlchemy (SQLite)
- **Frontend**: Vanilla HTML/CSS/JS
- **Containerization**: Docker

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (optional)

### Local Development

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd spender
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r backend/requirements.txt
    ```

4.  **Run the application**:
    ```bash
    ./start.sh
    # OR manually:
    uvicorn backend.main:app --reload --app-dir .
    ```

    The API will be available at `http://localhost:8000`.
    The frontend is served at the root `/`.

### Docker Setup

1.  **Build the image**:
    ```bash
    docker build -t spender .
    ```

2.  **Run the container**:
    ```bash
    docker run -p 8000:8000 spender
    ```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Project Structure

```
spender/
├── backend/          # FastAPI application code
│   ├── main.py       # Entry point
│   ├── models.py     # SQLAlchemy models
│   ├── schemas.py    # Pydantic schemas
│   ├── engine.py     # Core business logic
│   └── database.py   # Database connection
├── frontend/         # Static frontend files
│   ├── index.html    # Main dashboard
│   ├── app.js        # Frontend logic
│   └── style.css     # Styles
├── Dockerfile        # Docker configuration
└── start.sh          # Local startup script
```
