def parse_list_args(args, allowed_filters=()):
    """Splits request.args into (filters, limit, offset, count, error).

    Only keys present in allowed_filters are kept as query filters, any other
    key is rejected with a sanitized error message instead of being passed
    straight into filter_by() and leaking a raw SQLAlchemy exception.
    """
    args = dict(args)
    limit = args.pop('limit', 0)
    offset = args.pop('offset', 0)
    count = args.pop('count', 0)

    unknown = set(args) - set(allowed_filters)
    if unknown:
        return None, 0, 0, 0, f"unknown filter(s): {', '.join(sorted(unknown))}"

    return args, limit, offset, count, None
