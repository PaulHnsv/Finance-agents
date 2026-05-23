"""
Portfolio objective setup flow. Guides user to define target allocations.
Validates that sum == 100%. Deterministic logic; LLM not used.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from investimentos.domain.models import PortfolioObjective, AllocationTarget, AssetClass

console = Console()

AVAILABLE_CLASSES = [c.value for c in AssetClass if c != AssetClass.CAIXA]

def run_objective_setup(name: str | None = None) -> PortfolioObjective:
    console.print("\n[bold blue]🎯 Configuração de Objetivo de Carteira[/bold blue]\n")
    if not name:
        name = Prompt.ask("Nome do objetivo (ex: Crescimento de Longo Prazo)")

    console.print("\nClasses disponíveis: " + ", ".join(AVAILABLE_CLASSES))
    console.print("Digite as alocações para cada classe (pressione Enter para 0%).\n")

    allocations = []
    total = Decimal("0")

    for cls in AVAILABLE_CLASSES:
        raw = Prompt.ask(f"  {cls} (%)", default="0")
        try:
            pct = Decimal(raw.replace(",", "."))
        except InvalidOperation:
            pct = Decimal("0")
        if pct > 0:
            allocations.append(AllocationTarget(asset_class=AssetClass(cls), target_pct=pct))
            total += pct

    if abs(total - Decimal("100")) > Decimal("0.01"):
        console.print(f"[red]⚠️ Soma das alocações = {total}% (deve ser 100%). Tente novamente.[/red]")
        return run_objective_setup(name)

    table = Table(title="Objetivo Configurado")
    table.add_column("Classe")
    table.add_column("Target (%)", justify="right")
    for a in allocations:
        table.add_row(a.asset_class.value, str(a.target_pct))
    console.print(table)

    return PortfolioObjective(
        name=name,
        allocations=allocations,
        valid_from=date.today(),
    )
