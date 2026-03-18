def col_to_a1(col_num: int) -> str:
    """Convierte columna 1-based a letra A1 (1->A, 27->AA)."""
    if col_num < 1:
        raise ValueError("col debe ser >= 1")
    result = []
    n = col_num
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result.append(chr(65 + rem))
    return "".join(reversed(result))
