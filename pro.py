"""
Personal Finance Tracker
-------------------------
Tracks income & expenses, computes budget usage, and renders
spending charts (pie + monthly trend) using pandas + matplotlib.

Run:
    python finance_tracker.py

Data is persisted to transactions.json in the same folder, so your
history survives between runs.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import date
from typing import List, Dict

import pandas as pd
import matplotlib.pyplot as plt

DATA_FILE = "transactions.json"

# Monthly budget per category (edit to match your own spending caps)
BUDGETS: Dict[str, float] = {
    "Food": 8000,
    "Transport": 3000,
    "Rent": 15000,
    "Utilities": 2500,
    "Entertainment": 2000,
    "Shopping": 4000,
    "Health": 2000,
    "Other": 1500,
}

CATEGORIES = list(BUDGETS.keys())


# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------

@dataclass
class Transaction:
    type: str          # "income" or "expense"
    category: str
    amount: float
    note: str = ""
    date: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------
# Core tracker class — owns state, persistence, and calculations
# ---------------------------------------------------------------------

class FinanceTracker:
    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.transactions: List[Transaction] = self._load()

    # ---- persistence ----
    def _load(self) -> List[Transaction]:
        if not os.path.exists(self.data_file):
            return []
        with open(self.data_file, "r") as f:
            raw = json.load(f)
        return [Transaction(**t) for t in raw]

    def _save(self) -> None:
        with open(self.data_file, "w") as f:
            json.dump([t.to_dict() for t in self.transactions], f, indent=2)

    # ---- CRUD ----
    def add(self, type_: str, category: str, amount: float, note: str = "") -> None:
        if type_ not in ("income", "expense"):
            raise ValueError("type must be 'income' or 'expense'")
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.transactions.append(Transaction(type_, category, amount, note))
        self._save()

    def delete(self, index: int) -> None:
        del self.transactions[index]
        self._save()

    # ---- derived data ----
    def as_dataframe(self) -> pd.DataFrame:
        if not self.transactions:
            return pd.DataFrame(columns=["type", "category", "amount", "note", "date"])
        df = pd.DataFrame([t.to_dict() for t in self.transactions])
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.strftime("%b")
        return df

    def summary(self) -> dict:
        df = self.as_dataframe()
        income = df.loc[df.type == "income", "amount"].sum()
        expense = df.loc[df.type == "expense", "amount"].sum()
        return {"income": income, "expense": expense, "net": income - expense}

    def category_breakdown(self) -> pd.Series:
        df = self.as_dataframe()
        expenses = df[df.type == "expense"]
        return expenses.groupby("category")["amount"].sum().sort_values(ascending=False)

    def monthly_trend(self) -> pd.DataFrame:
        df = self.as_dataframe()
        pivot = df.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0)
        for col in ("income", "expense"):
            if col not in pivot.columns:
                pivot[col] = 0
        return pivot[["income", "expense"]]

    def budget_status(self) -> pd.DataFrame:
        spent = self.category_breakdown()
        rows = []
        for cat in CATEGORIES:
            cat_spent = spent.get(cat, 0)
            budget = BUDGETS[cat]
            rows.append({
                "category": cat,
                "spent": cat_spent,
                "budget": budget,
                "pct_used": round(cat_spent / budget * 100, 1) if budget else 0,
                "over_budget": cat_spent > budget,
            })
        return pd.DataFrame(rows)

    # ---- charts ----
    def plot_category_pie(self) -> None:
        breakdown = self.category_breakdown()
        if breakdown.empty:
            print("No expenses to chart yet.")
            return
        plt.figure(figsize=(6, 6))
        plt.pie(breakdown.values, labels=breakdown.index, autopct="%1.0f%%", startangle=90)
        plt.title("Spending by Category")
        plt.tight_layout()
        plt.show()

    def plot_monthly_trend(self) -> None:
        trend = self.monthly_trend()
        if trend.empty:
            print("No transactions to chart yet.")
            return
        ax = trend.plot(kind="bar", figsize=(8, 5), color=["#5FCB9E", "#C96A4A"])
        ax.set_title("Income vs Expense by Month")
        ax.set_ylabel("Amount (₹)")
        plt.tight_layout()
        plt.show()


# ---------------------------------------------------------------------
# Simple CLI menu
# ---------------------------------------------------------------------

def print_summary(tracker: FinanceTracker) -> None:
    s = tracker.summary()
    print(f"\nIncome:  ₹{s['income']:,.0f}")
    print(f"Expense: ₹{s['expense']:,.0f}")
    print(f"Net:     ₹{s['net']:,.0f}\n")


def print_budgets(tracker: FinanceTracker) -> None:
    df = tracker.budget_status()
    df = df[df["spent"] > 0]
    if df.empty:
        print("No spending recorded yet.")
        return
    for _, row in df.iterrows():
        flag = " ⚠ OVER BUDGET" if row["over_budget"] else ""
        print(f"{row['category']:<14} ₹{row['spent']:>8,.0f} / ₹{row['budget']:>8,.0f}  ({row['pct_used']}%){flag}")


def print_transactions(tracker: FinanceTracker) -> None:
    if not tracker.transactions:
        print("No transactions yet.")
        return
    for i, t in enumerate(tracker.transactions):
        sign = "+" if t.type == "income" else "-"
        print(f"[{i}] {t.date}  {t.category:<14} {sign}₹{t.amount:,.0f}  {t.note}")


def main() -> None:
    tracker = FinanceTracker()

    menu = """
--- Personal Finance Tracker ---
1. Add transaction
2. View summary
3. View transactions
4. View budget status
5. Show category pie chart
6. Show monthly trend chart
7. Delete a transaction
0. Exit
"""
    while True:
        print(menu)
        choice = input("Choose an option: ").strip()

        if choice == "1":
            type_ = input("Type (income/expense): ").strip().lower()
            print("Categories:", ", ".join(CATEGORIES))
            category = input("Category: ").strip().title()
            amount = float(input("Amount: ").strip())
            note = input("Note (optional): ").strip()
            try:
                tracker.add(type_, category, amount, note)
                print("Added.")
            except ValueError as e:
                print("Error:", e)

        elif choice == "2":
            print_summary(tracker)

        elif choice == "3":
            print_transactions(tracker)

        elif choice == "4":
            print_budgets(tracker)

        elif choice == "5":
            tracker.plot_category_pie()

        elif choice == "6":
            tracker.plot_monthly_trend()

        elif choice == "7":
            print_transactions(tracker)
            idx = input("Index to delete: ").strip()
            if idx.isdigit():
                tracker.delete(int(idx))
                print("Deleted.")

        elif choice == "0":
            print("Goodbye!")
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()