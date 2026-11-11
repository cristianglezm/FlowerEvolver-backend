import re
from flask_restful import fields

count_fields = {
    'count': fields.Integer
}


def parse_list_args(args, allowed_filters=()):
    """Splits request.args into (filters, limit, offset, count, error).

    count is True when the client asked for the total (see below).

    Only keys present in allowed_filters are kept as query filters, any other
    key is rejected with a sanitized error message instead of being passed
    straight into filter_by() and leaking a raw SQLAlchemy exception.
    """
    args = dict(args)
    limit = args.pop('limit', 0)
    offset = args.pop('offset', 0)
    count = args.pop('count', None)

    for name, value in (('limit', limit), ('offset', offset)):
        if value != 0 and not re.fullmatch(r'[0-9]+', value):
            return None, 0, 0, 0, f"{name} must be a non-negative integer"

    unknown = set(args) - set(allowed_filters)
    if unknown:
        return None, 0, 0, 0, f"unknown filter(s): {', '.join(sorted(unknown))}"

    # ?count=1 answers {"count": <all rows that match>}, ignoring limit and offset: it is what a pages widget
    # needs to know how many pages to draw. `count=0` and `count=false` are off.
    count = count is not None and count.strip().lower() not in ('0', 'false')
    return args, limit, offset, count, None
