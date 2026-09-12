"""Domain matching for Odoo XML-RPC fakes used by connector tests."""


def _scalar(val):
    if isinstance(val, (list, tuple)) and val:
        return val[0]
    return val


def _term_ok(rec: dict, term) -> bool:
    if not isinstance(term, (list, tuple)) or len(term) < 3:
        return True
    field, op, expected = term[0], term[1], term[2]
    if "." in str(field):
        return True
    cur = rec.get(field)
    cur_id = _scalar(cur)
    if op == "=":
        return cur_id == expected or cur == expected
    if op == "!=":
        if expected is False:
            return bool(cur_id)
        return cur_id != expected
    if op == "in":
        return cur_id in (expected or [])
    if op == ">":
        try:
            return float(cur_id or 0) > float(expected)
        except (TypeError, ValueError):
            return False
    return True


def match_domain(records, domain) -> list:
    domain = list(domain or [])
    if not domain:
        return list(records)
    if domain[0] == "|":
        rest = [t for t in domain[1:] if t not in ("|", "&", "!")]
        return [r for r in records if any(_term_ok(r, t) for t in rest)]
    terms = [t for t in domain if t not in ("|", "&", "!")]
    return [r for r in records if all(_term_ok(r, t) for t in terms)]
