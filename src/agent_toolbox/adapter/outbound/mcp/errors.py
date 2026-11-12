def root_causes(error: BaseException) -> str:
    if isinstance(error, BaseExceptionGroup):
        return "; ".join(root_causes(inner) for inner in error.exceptions)
    return f"{type(error).__name__}: {error}"
