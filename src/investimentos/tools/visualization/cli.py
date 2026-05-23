"""ASCII charts for terminal output using plotext."""
from decimal import Decimal
import plotext as plt

def show_allocation_pie(allocations: dict[str, Decimal], title: str = "Alocação Atual") -> None:
    labels = list(allocations.keys())
    values = [float(v) for v in allocations.values()]
    plt.clf()
    plt.pie(values, labels=labels)
    plt.title(title)
    plt.show()

def show_performance_line(
    dates: list[str],
    portfolio_returns: list[float],
    benchmark_returns: list[float] | None = None,
    title: str = "Performance vs Benchmark",
) -> None:
    plt.clf()
    plt.plot(dates, portfolio_returns, label="Carteira")
    if benchmark_returns:
        plt.plot(dates, benchmark_returns, label="CDI")
    plt.title(title)
    plt.xlabel("Data")
    plt.ylabel("Retorno (%)")
    plt.show()

def show_drift_bars(
    asset_classes: list[str],
    actual: list[float],
    target: list[float],
    title: str = "Alocação: Atual vs Target",
) -> None:
    plt.clf()
    plt.bar(asset_classes, actual, label="Atual", width=0.4)
    plt.bar(asset_classes, target, label="Target", width=0.4)
    plt.title(title)
    plt.show()
