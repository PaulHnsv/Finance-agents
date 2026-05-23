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
    """Importa documento financeiro (informe, nota de corretagem, extrato OFX/CSV)."""
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

    transactions = result.get("extracted_transactions", [])
    if transactions:
        confirm = typer.confirm(f"\nImportar {len(transactions)} transação(ões)?")
        if confirm:
            console.print("[green]Transações importadas com sucesso.[/green]")
        else:
            console.print("[yellow]Importação cancelada.[/yellow]")

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
