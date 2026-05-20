def auto_scale(values):
    if not values:
        return 0, 1
    mn = min(values)
    mx = max(values)
    if mx == mn:
        mn -= 1
        mx += 1
    return mn, mx


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


def render_graph(display, data, metric, x, y, w, h):
    values = [d[metric] for d in data]
    if len(values) < 2:
        display.text("-- no data --", x + 4, y + h // 2 - 4)
        return None, None

    max_points = w - 2
    values = downsample(values, max_points)

    vmin, vmax = auto_scale(values)
    vrange = vmax - vmin
    if vrange == 0:
        vrange = 1

    step_x = (w - 2) / (len(values) - 1) if len(values) > 1 else 1

    for i in range(len(values) - 1):
        x1 = int(x + 1 + i * step_x)
        x2 = int(x + 1 + (i + 1) * step_x)
        y1 = int(y + h - 1 - ((values[i] - vmin) / vrange) * (h - 2))
        y2 = int(y + h - 1 - ((values[i + 1] - vmin) / vrange) * (h - 2))
        display.line(x1, y1, x2, y2, 1)
    return vmin, vmax


