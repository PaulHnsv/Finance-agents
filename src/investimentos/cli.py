"""CLI entry point using Typer. Subcommands: query, import, profile, objective, report."""
import typer
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(help="Sistema de Agentes para Gestão Financeira Pessoal")
console = Console()

@app.command()
def query(
    question: str = typer.Argument(..., help="Pergunta sobre sua carteira"),
    account_id: str = typer.Option(None, "--account", "-a", help="ID da conta (omitir = todas)"),
):
    """Faça uma pergunta sobre sua carteira."""
    from investimentos.workflows.portfolio_query import build_portfolio_query_graph
    from investimentos.agents.state import AgentState

    console.print(f"[dim]Processando: {question}...[/dim]")
    graph = build_portfolio_query_graph()
    result = graph.invoke(AgentState(user_query=question, account_id=account_id))
    if result.get("report_markdown"):
        console.print(Markdown(result["report_markdown"]))
    elif result.get("error"):
        console.print(f"[red]Erro: {result['error']}[/red]")

@app.command()
def report(
    account_id: str = typer.Option(None, "--account", "-a", help="ID da conta"),
    output: Path = typer.Option(None, "--output", "-o", help="Salvar relatório em arquivo"),
):
    """Gera relatório completo da carteira."""
    from investimentos.workflows.portfolio_query import build_portfolio_query_graph
    from investimentos.agents.state import AgentState

    graph = build_portfolio_query_graph()
    result = graph.invoke(AgentState(
        user_query="Gere um relatório completo da minha carteira",
        account_id=account_id,
        intent="report",
    ))
    md = result.get("report_markdown", "Sem dados.")
    if output:
        output.write_text(md, encoding="utf-8")
        console.print(f"[green]Relatório salvo em {output}[/green]")
    else:
        console.print(Markdown(md))

@app.command(name="import")
def import_document(
    file: Path = typer.Argument(..., help="Caminho para o arquivo (PDF, OFX, CSV)"),
    account_id: str = typer.Option(..., "--account", "-a", help="ID da conta de destino"),
):
    """Importa documento financeiro (nota de corretagem, OFX/CSV, carteira sugerida)."""
    if not file.exists():
        console.print(f"[red]Arquivo não encontrado: {file}[/red]")
        raise typer.Exit(1)

    from investimentos.workflows.portfolio_query import build_portfolio_query_graph
    from investimentos.agents.state import AgentState

    graph = build_portfolio_query_graph()
    result = graph.invoke(AgentState(
        user_query="Importe este documento",
        account_id=account_id,
        document_path=str(file),
        intent="document_ingest",
    ))
    for output in result.get("specialist_outputs", []):
        console.print(Markdown(output))

    doc_type = result.get("document_type")

    if doc_type == "transactions":
        transactions = result.get("extracted_transactions", []) or []
        snapshot = result.get("extracted_snapshot") or {}
        _handle_extrato_import(file, account_id, transactions, snapshot)
        return

    if doc_type == "suggested_portfolio":
        suggestion = result.get("extracted_suggestion") or {}
        _handle_suggested_portfolio(file, suggestion)
        return

    console.print("[yellow]Nada a importar.[/yellow]")


def _handle_extrato_import(
    file: Path, account_id: str, transactions: list[dict], snapshot: dict
) -> None:
    from datetime import date
    from decimal import Decimal
    from sqlalchemy.orm import Session
    from investimentos.config import get_settings
    from investimentos.domain.db import engine_from_url
    from investimentos.domain.models import (
        Transaction,
        TransactionType,
        EquityPositionSnapshot,
        FixedIncomePosition,
        PortfolioSnapshot,
    )
    from investimentos.repository.transaction import TransactionRepository
    from investimentos.repository.portfolio_snapshot_repo import PortfolioSnapshotRepository

    settings = get_settings()
    engine = engine_from_url(settings.database_url)

    # --- Transactions ---
    if transactions:
        console.print("\n[bold]Transações encontradas:[/bold]")
        for t in transactions[:20]:
            console.print(
                f"  {t.get('date','?'):<12} {t.get('type','?'):<6} "
                f"{t.get('ticker','?'):<8} {t.get('quantity','?')} × R${t.get('price','?')}"
            )
        if len(transactions) > 20:
            console.print(f"  ... e mais {len(transactions) - 20} transação(ões)")

        if typer.confirm(f"\nSalvar {len(transactions)} transação(ões)?"):
            _type_map = {
                "compra": TransactionType.COMPRA,
                "venda": TransactionType.VENDA,
                "dividendo": TransactionType.DIVIDENDO,
                "jcp": TransactionType.JCP,
            }
            with Session(engine) as session:
                repo = TransactionRepository(session)
                saved = 0
                for raw in transactions:
                    try:
                        txn = Transaction(
                            account_id=account_id,
                            ticker=raw["ticker"],
                            transaction_type=_type_map.get(
                                raw.get("type", "").lower(), TransactionType.COMPRA
                            ),
                            quantity=Decimal(str(raw.get("quantity", 0))),
                            unit_price=Decimal(str(raw.get("price", 0))),
                            date=date.fromisoformat(raw["date"]),
                            fees=Decimal(str(raw.get("fees", 0))),
                        )
                        repo.save(txn)
                        saved += 1
                    except (KeyError, ValueError) as exc:
                        console.print(f"  [yellow]Ignorando transação inválida: {exc}[/yellow]")
            console.print(f"[green]{saved} transação(ões) salva(s).[/green]")
        else:
            console.print("[yellow]Transações não salvas.[/yellow]")

    # --- Snapshot ---
    equity = snapshot.get("equity_snapshot", [])
    fixed = snapshot.get("fixed_income_snapshot", [])
    period_end = snapshot.get("period_end")

    if equity or fixed:
        console.print("\n[bold]Snapshot de posições:[/bold]")
        for p in equity:
            console.print(
                f"  {p.get('ticker','?'):<8} {p.get('quantity','?')} un."
                f"  (PM hint: R${p.get('avg_cost_hint','?')})"
            )
        for fi in fixed:
            console.print(
                f"  {fi.get('name','?'):<30} R${fi.get('current_value','?')}"
                f"  {fi.get('rate_description','')}"
            )

        if typer.confirm(
            f"\nSalvar snapshot de posições (data: {period_end or 'desconhecida'})?",
            default=True,
        ):
            try:
                snap_date = date.fromisoformat(period_end) if period_end else date.today()
            except ValueError:
                snap_date = date.today()

            snap = PortfolioSnapshot(
                account_id=account_id,
                snapshot_date=snap_date,
                source_file=str(file),
                equity_positions=[
                    EquityPositionSnapshot(
                        ticker=p["ticker"],
                        quantity=Decimal(str(p.get("quantity", 0))),
                        avg_cost_hint=(
                            Decimal(str(p["avg_cost_hint"])) if p.get("avg_cost_hint") else None
                        ),
                    )
                    for p in equity
                ],
                fixed_income_positions=[
                    FixedIncomePosition(
                        name=fi["name"],
                        issuer=fi.get("issuer"),
                        maturity_date=(
                            date.fromisoformat(fi["maturity_date"])
                            if fi.get("maturity_date")
                            else None
                        ),
                        invested_amount=Decimal(str(fi.get("invested_amount", 0))),
                        rate_description=fi.get("rate_description"),
                        current_value=Decimal(str(fi.get("current_value", 0))),
                    )
                    for fi in fixed
                ],
            )
            with Session(engine) as session:
                snap_repo = PortfolioSnapshotRepository(session)
                snap_repo.save(snap)
            console.print(
                f"[green]Snapshot salvo (data: {snap_date.isoformat()}, id={snap.id}).[/green]"
            )
        else:
            console.print("[yellow]Snapshot não salvo.[/yellow]")


def _handle_suggested_portfolio(file: Path, suggestion: dict) -> None:
    from decimal import Decimal
    from sqlalchemy.orm import Session
    from investimentos.config import get_settings
    from investimentos.domain.db import engine_from_url
    from investimentos.domain.models import (
        AssetClass,
        SuggestedAssetAllocation,
        SuggestedClassAllocation,
        SuggestedPortfolio,
    )
    from investimentos.repository.suggested_portfolio_repo import SuggestedPortfolioRepository

    classes = suggestion.get("class_allocations", [])
    assets = suggestion.get("asset_allocations", [])

    if not classes and not assets:
        console.print("[yellow]Nenhum ativo ou classe extraída do documento.[/yellow]")
        return

    console.print("\n[bold]Pré-visualização:[/bold]")
    for c in classes:
        console.print(f"  {c['asset_class']:<15} {c['target_pct']}%")
    if classes and assets:
        console.print()
    for a in assets[:20]:
        line = f"  {a['ticker']:<8} {a['target_pct']}%"
        if a.get("thesis"):
            line += f"  — {a['thesis'][:60]}"
        console.print(line)
    if len(assets) > 20:
        console.print(f"  ... e mais {len(assets) - 20} ativo(s)")

    if not typer.confirm("\nSalvar como rascunho?"):
        console.print("[yellow]Cancelado.[/yellow]")
        return

    sp = SuggestedPortfolio(
        name=file.stem,
        source_file=str(file),
        class_allocations=[
            SuggestedClassAllocation(
                asset_class=AssetClass(c["asset_class"]),
                target_pct=Decimal(str(c["target_pct"])),
            )
            for c in classes
        ],
        asset_allocations=[
            SuggestedAssetAllocation(
                ticker=a["ticker"],
                target_pct=Decimal(str(a["target_pct"])),
                thesis=a.get("thesis"),
            )
            for a in assets
        ],
    )
    settings = get_settings()
    engine = engine_from_url(settings.database_url)
    with Session(engine) as session:
        repo = SuggestedPortfolioRepository(session)
        repo.save(sp)
        console.print(f"[green]Rascunho salvo (id={sp.id}).[/green]")
        if typer.confirm("Ativar como alocação-alvo agora?", default=False):
            repo.activate(sp.id)
            console.print("[green]Ativada.[/green]")

@app.command()
def profile():
    """Configura ou atualiza o perfil de investidor (questionário de suitability)."""
    from investimentos.flows.profile_setup import run_profile_setup
    investor_profile = run_profile_setup()
    console.print(f"\n[green]Perfil configurado: {investor_profile.risk_profile.value}[/green]")

@app.command()
def objective():
    """Configura o objetivo e alocação-alvo da carteira."""
    from investimentos.flows.objective_setup import run_objective_setup
    obj = run_objective_setup()
    console.print(f"\n[green]Objetivo '{obj.name}' configurado com sucesso.[/green]")

if __name__ == "__main__":
    app()
