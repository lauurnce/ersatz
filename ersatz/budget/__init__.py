"""Request budgets per provider and the spend ledger for model calls.

Every limit is checked before a call is sent.
"""

from ersatz.budget.requests import BudgetExhaustedError, RequestBudget

__all__ = ["BudgetExhaustedError", "RequestBudget"]
