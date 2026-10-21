class ContractError(ValueError):
    """Raised when data does not match a contract. Callers drop or dead-letter it; they never 'fix it up'."""
