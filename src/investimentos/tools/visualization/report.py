"""PNG charts for markdown/PDF reports using matplotlib."""
from decimal import Decimal
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def save_allocation_pie(allocations: dict[str, Decimal], output_path: Path, title: str = "Alocação da Carteira") -> Path:
    labels = list(allocations.keys())
    values = [float(v) for v in allocations.values()]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path

def save_performance_line(
    dates: list[str],
    portfolio_returns: list[float],
    benchmark_returns: list[float] | None = None,
    output_path: Path = Path("perf.png"),
    title: str = "Performance Acumulada",
) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, portfolio_returns, label="Carteira", linewidth=2)
    if benchmark_returns:
        ax.plot(dates, benchmark_returns, label="CDI", linewidth=1, linestyle="--")
    ax.set_title(title)
    ax.set_xlabel("Data")
    ax.set_ylabel("Retorno Acumulado (%)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path

def save_drawdown_area(
    dates: list[str],
    drawdowns: list[float],
    output_path: Path = Path("drawdown.png"),
    title: str = "Drawdown",
) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(dates, drawdowns, 0, alpha=0.4, color="red", label="Drawdown")
    ax.plot(dates, drawdowns, color="red", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel("Data")
    ax.set_ylabel("Drawdown (%)")
    ax.invert_yaxis()
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
