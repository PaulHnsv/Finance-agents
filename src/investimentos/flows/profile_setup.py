"""
Suitability questionnaire flow. Deterministic scoring logic.
LLM only used to explain terms. Final profile computed from rule-based scoring.
"""
from datetime import date
from rich.console import Console
from rich.prompt import IntPrompt
from investimentos.domain.models import InvestorProfile, RiskProfile

console = Console()

QUESTIONS = [
    {
        "id": "age",
        "text": "Qual é a sua idade?",
        "type": "int",
        "scoring": lambda v: 3 if v < 30 else (2 if v < 50 else 1),
    },
    {
        "id": "horizon",
        "text": "Em quantos anos você pretende usar estes investimentos?",
        "type": "int",
        "scoring": lambda v: 3 if v >= 10 else (2 if v >= 5 else 1),
    },
    {
        "id": "loss_tolerance",
        "text": "Se sua carteira cair 20% em um ano, você:\n  1 = Venderia tudo\n  2 = Esperaria\n  3 = Compraria mais",
        "type": "choice",
        "choices": [1, 2, 3],
        "scoring": lambda v: v,
    },
    {
        "id": "income_stability",
        "text": "Como você descreveria sua renda?\n  1 = Instável/autônomo\n  2 = Moderada\n  3 = Estável/CLT",
        "type": "choice",
        "choices": [1, 2, 3],
        "scoring": lambda v: v,
    },
    {
        "id": "emergency_reserve",
        "text": "Você possui reserva de emergência (>= 6 meses de gastos)?\n  1 = Não\n  2 = Parcial\n  3 = Sim",
        "type": "choice",
        "choices": [1, 2, 3],
        "scoring": lambda v: v,
    },
]

def compute_risk_profile(total_score: int, max_score: int) -> RiskProfile:
    ratio = total_score / max_score
    if ratio >= 0.80:
        return RiskProfile.AGRESSIVO
    if ratio >= 0.60:
        return RiskProfile.ARROJADO
    if ratio >= 0.40:
        return RiskProfile.MODERADO
    return RiskProfile.CONSERVADOR

def run_profile_setup() -> InvestorProfile:
    console.print("\n[bold blue]📋 Questionário de Perfil de Investidor[/bold blue]\n")
    answers = {}
    total_score = 0
    max_score = len(QUESTIONS) * 3

    for q in QUESTIONS:
        console.print(f"[yellow]{q['text']}[/yellow]")
        if q["type"] == "int":
            value = IntPrompt.ask("> ")
        else:
            value = IntPrompt.ask("> ", choices=[str(c) for c in q["choices"]])
        answers[q["id"]] = value
        total_score += q["scoring"](value)

    risk_profile = compute_risk_profile(total_score, max_score)
    horizon = answers.get("horizon", 5)

    console.print(f"\n[green]✅ Perfil calculado: [bold]{risk_profile.value.upper()}[/bold][/green]")

    return InvestorProfile(
        risk_profile=risk_profile,
        horizon_years=horizon,
        questionnaire_answers=answers,
        valid_from=date.today(),
    )
