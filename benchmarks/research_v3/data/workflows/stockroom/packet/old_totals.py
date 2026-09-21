# Current clerk helper; does not handle the entire SOP.
def sum_units(rows):
    return sum(row["quantity"] for row in rows)
