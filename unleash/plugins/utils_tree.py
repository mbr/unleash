def require_file(ctx, path, error, suggestion=None):
    # find setup.py
    if not ctx['commit'].path_exists(path):
        ctx['issues'].error(error, suggestion)

    return ctx['commit'].get_path_data(path)
