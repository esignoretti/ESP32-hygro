def downsample(values, max_points):
    n = len(values)
    if n <= max_points:
        return values
    step = n / max_points
    result = []
    for i in range(max_points):
        idx = int(i * step)
        result.append(values[idx])
    return result


def auto_scale(values):
    if not values:
        return 0, 1
    mn = min(values)
    mx = max(values)
    if mx == mn:
        mn -= 1
        mx += 1
    return mn, mx


def render_sparkline(display, data, metric, x, y, w, h):
    values = [d[metric] for d in data]
    if len(values) < 2:
        return None, None

    max_points = w
    values = downsample(values, max_points)
    vmin, vmax = auto_scale(values)
    vrange = vmax - vmin
    if vrange == 0:
        vrange = 1

    for i, v in enumerate(values):
        col_h = int(((v - vmin) / vrange) * (h - 1)) + 1
        for row in range(col_h):
            display.pixel(x + i, y + h - 1 - row, 1)

    return vmin, vmax
