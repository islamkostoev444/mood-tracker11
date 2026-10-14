from datetime import timedelta
from io import BytesIO
import math

import matplotlib


matplotlib.use("Agg")
from matplotlib.figure import Figure

WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")


def period(today, days):
    if days not in (7, 30):
        raise ValueError("Период должен быть 7 или 30 дней.")

    return today - timedelta(days=days - 1), today


def correlation_text(value):
    if value is None or not math.isfinite(value):
        return "не определяется: один из показателей не менялся"
    if abs(value) < 0.3:
        strength = "слабая"
    elif abs(value) < 0.7:
        strength = "умеренная"
    else:
        strength = "сильная"
    direction = "положительная" if value >= 0 else "отрицательная"
    return f"{strength} {direction} связь (r = {value:+.2f})"


def summary_text(summary, start, end, best_days):
    if not summary["n"]:
        return "За этот период записей нет. Нажми «➕ Записать день»."
    covered = (end - start).days + 1
    best = ", ".join(row["entry_date"].strftime("%d.%m") for row in best_days)
    return (
        f"📊 {start:%d.%m.%Y} — {end:%d.%m.%Y}\n"
        f"Заполнено дней: {summary['n']} из {covered}\n"
        f"Среднее настроение: {summary['mood']:.2f}/5\n"
        f"Работа/учёба: {summary['work']:.2f} ч/день; всего {summary['total_work']:.2f} ч\n"
        f"Средний сон: {summary['sleep']:.2f} ч\n"
        f"Лучшее настроение ({summary['best_mood']}/5): {best}\n\n"
        "Средние рассчитаны только по заполненным дням. Пропуски не считаются нулями."
    )


def insights_text(data, weekdays, start, end):
    lines = [f"🔍 Наблюдения за {start:%d.%m} — {end:%d.%m.%Y}", f"Записей: {data['n']}."]
    if data["n"] < 10:
        lines.append("Нужно хотя бы 10 заполненных дней для сравнения и корреляций. Продолжай записывать дни.")
        return "\n".join(lines)
    lines.extend([
        f"Сон и продуктивные часы: {correlation_text(data['sleep_work_corr'])}.",
        f"Учёба/работа и настроение: {correlation_text(data['work_mood_corr'])}.",
    ])
    if data["long_sleep_n"] >= 3 and data["short_sleep_n"] >= 3:
        lines.append(
            f"При сне ≥ 8 ч настроение {data['long_sleep_mood']:.2f}/5 "
            f"({data['long_sleep_n']} дн.), при сне < 8 ч — {data['short_sleep_mood']:.2f}/5 "
            f"({data['short_sleep_n']} дн.)."
        )
    else:
        lines.append("Для сравнения сна нужно ≥ 3 дней в каждой группе: ≥ 8 ч и < 8 ч.")
    if data["long_work_n"] >= 3 and data["short_work_n"] >= 3:
        lines.append(
            f"При работе/учёбе ≥ 6 ч настроение {data['long_work_mood']:.2f}/5 "
            f"({data['long_work_n']} дн.), при < 6 ч — {data['short_work_mood']:.2f}/5 "
            f"({data['short_work_n']} дн.)."
        )
    else:
        lines.append("Для сравнения нагрузки нужно ≥ 3 дней в каждой группе: ≥ 6 ч и < 6 ч.")
    if len(weekdays) >= 2:
        best = weekdays[0]
        lines.append(f"Среди дней недели с ≥ 2 записями выше среднее в день «{WEEKDAYS[best['weekday'] - 1]}»: "
                     f"{best['mood']:.2f}/5 ({best['n']} дн.).")
    lines.append("Это наблюдения, а не доказательство причин. Усталость отдельно не измеряется; "
                 "настроение не заменяет её оценку. Пороги 8 ч и 6 ч нужны для сравнения, это не рекомендации.")
    return "\n\n".join(lines)


def build_chart(entries, start, end):

    by_date = {row["entry_date"]: row for row in entries}
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    figure = Figure(figsize=(10, 6), layout="constrained")
    axes = figure.subplots(2, 1, sharex=True)
    for ax in axes:
        ax.grid(alpha=0.15)
    for field, ax, label, color in (
        ("mood", axes[0], "Настроение", "#7c3aed"),
        ("productive_hours", axes[1], "Работа/учёба", "#0891b2"),
        ("sleep_hours", axes[1], "Сон", "#16a34a"),
    ):
        values = [float(by_date[day][field]) if day in by_date else math.nan for day in dates]
        ax.plot(dates, values, "o-", label=label, color=color, linewidth=2, markersize=4)
        ax.legend(loc="upper left")
    axes[0].set_ylim(0.8, 5.2)
    axes[0].set_yticks([1, 2, 3, 4, 5])
    axes[0].set_ylabel("Оценка (1–5)")
    axes[1].set_ylabel("Часы")
    axes[1].set_ylim(bottom=0)
    figure.suptitle(f"Настроение и привычки · {start:%d.%m} — {end:%d.%m.%Y}", fontsize=15)
    figure.autofmt_xdate()
    buffer = BytesIO()
    buffer.name = "mood-chart.png"
    figure.savefig(buffer, format="png", dpi=140)
    buffer.seek(0)
    return buffer
