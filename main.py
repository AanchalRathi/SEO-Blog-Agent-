"""
main.py — CLI entry point (generalized)

What changed from original:
    - No longer hardcoded for Times Prime
    - Collects full company config from user (name, niche, audience,
      competitors, docs path)
    - Passes config into CompanyConfig → run_crew()
    - Rich UI preserved and extended with new input sections
    - Output now includes SEO title, meta description, slug separately
"""

import os
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Prompt

from crew import CompanyConfig, run_crew

console = Console()


# ── HELPERS ───────────────────────────────────────────────────────────────────

def collect_company_config() -> CompanyConfig:
    """
    Collects all company details interactively from the CLI.
    Returns a fully built CompanyConfig ready for run_crew().
    """
    console.print(Rule("[bold cyan]Company Setup[/bold cyan]"))
    console.print("[dim]Fill in your company details — press Enter to use defaults\n[/dim]")

    company_name = Prompt.ask(
        "[green]Company name[/green]",
        default="My Company"
    )

    niche = Prompt.ask(
        "[green]Niche / industry[/green]",
        default="e-commerce"
    )

    target_audience = Prompt.ask(
        "[green]Target audience[/green]",
        default="online shoppers in India"
    )

    console.print("\n[dim]Enter competitor names separated by commas[/dim]")
    competitors_raw = Prompt.ask(
        "[green]Competitors[/green]",
        default=""
    )
    competitors = [c.strip() for c in competitors_raw.split(",") if c.strip()]

    console.print("\n[dim]Path to folder containing brand docs (PDF/TXT/MD)[/dim]")
    docs_path = Prompt.ask(
        "[green]Brand docs folder[/green]",
        default="brand_docs/"
    )

    tone = Prompt.ask(
        "\n[green]Writing tone[/green]",
        choices=["conversational", "professional", "casual", "authoritative"],
        default="conversational"
    )

    region = Prompt.ask(
        "[green]Target region[/green]",
        default="India"
    )

    return CompanyConfig(
        company_name=company_name,
        niche=niche,
        target_audience=target_audience,
        competitors=competitors,
        docs_path=docs_path,
        tone=tone,
        region=region,
    )


def print_keyword_table(result: dict):
    """Prints the keyword summary table — same style as original."""
    table = Table(
        header_style="bold cyan",
        border_style="dim",
        show_lines=True
    )
    table.add_column("#",        width=4)
    table.add_column("Keyword",  width=42)
    table.add_column("Intent",   width=19)
    table.add_column("Score",    width=10)

    intent_colors = {
        "transactional": "green",
        "informational": "blue",
        "commercial":    "yellow",
    }

    color = intent_colors.get(result["intent"], "white")
    table.add_row(
        "1",
        result["keyword"],
        f"[{color}]{result['intent']}[/{color}]",
        f"[green]{result['score']}[/green]"
        if result["score"] >= 70
        else f"[yellow]{result['score']}[/yellow]",
    )
    console.print(table)


def save_output(result: dict, company_name: str) -> str:
    """Saves blog + meta to output/ folder."""
    os.makedirs("output", exist_ok=True)
    timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw    = result["keyword"][:40].replace(" ", "_").replace("/", "-").replace("?", "")
    safe_co    = company_name[:20].replace(" ", "_")
    fname      = f"output/blog_{safe_co}_{safe_kw}_{timestamp}.txt"

    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"COMPANY       : {company_name}\n")
        f.write(f"KEYWORD       : {result['keyword']}\n")
        f.write(f"INTENT        : {result['intent']} | SCORE: {result['score']}\n")
        f.write(f"SEO TITLE     : {result['seo_title']}\n")
        f.write(f"META DESC     : {result['meta_description']}\n")
        f.write(f"SLUG          : {result['slug']}\n")
        f.write(f"\n{'='*60}\n\n")
        f.write(result["blog"])

    return fname


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run():
    console.print(Panel.fit(
        "[bold magenta]SEO Agent — Powered by CrewAI + RAG[/bold magenta]\n"
        "[dim]Any company · Keyword Discovery → Strategy → Blog Generation[/dim]",
        border_style="magenta"
    ))

    # ── COLLECT COMPANY CONFIG ─────────────────────────────────────────────────
    config = collect_company_config()

    # ── MODE SELECTION ─────────────────────────────────────────────────────────
    console.print("\n[bold cyan]Choose keyword mode:[/bold cyan]")
    console.print("  [green]1[/green] → Type a search query  (like Google)")
    console.print("  [green]2[/green] → Auto-generate from company details\n")

    mode = input("Enter 1 or 2: ").strip()

    if mode == "1":
        console.print(
            "\n[dim]Example: 'best food delivery discount india'  |  "
            "'zomato vs swiggy'[/dim]"
        )
        user_query = input("🔍 Your search: ").strip()
        if user_query:
            config.user_query = user_query
            console.print(
                f"\n[green]Running for:[/green] [white]{user_query}[/white]\n"
            )

    # ── RUN CREW ───────────────────────────────────────────────────────────────
    console.print(Rule("[bold cyan]Running SEO Agent Pipeline[/bold cyan]"))
    console.print(
        f"[dim]Company: {config.company_name} | "
        f"Niche: {config.niche} | "
        f"Region: {config.region}[/dim]\n"
    )

    result = run_crew(config)

    # ── PHASE 1 SUMMARY ────────────────────────────────────────────────────────
    console.print(Rule("[bold cyan]Phase 1 — Keyword Discovery[/bold cyan]"))
    console.print(
        f"[green]✓ Discovered {result['keywords_found']} unique keywords[/green]\n"
    )

    # ── PHASE 2 SUMMARY ────────────────────────────────────────────────────────
    console.print(Rule("[bold cyan]Phase 2 — Scoring & Strategy[/bold cyan]"))
    print_keyword_table(result)
    console.print(
        f"\n[bold green]✓ Best keyword selected:[/bold green] "
        f"[bold white]{result['keyword']}[/bold white]"
    )
    console.print(
        f"  Intent: [yellow]{result['intent']}[/yellow]   "
        f"Score: [green]{result['score']}[/green]\n"
    )

    # ── PHASE 3 OUTPUT ─────────────────────────────────────────────────────────
    console.print(Rule("[bold cyan]Phase 3 — Blog Output[/bold cyan]"))

    console.print(Panel(
        f"[bold]SEO Title:[/bold]  {result['seo_title']}\n"
        f"[bold]Meta Desc:[/bold]  {result['meta_description']}\n"
        f"[bold]Slug:     [/bold]  {result['slug']}",
        title="[bold green]SEO Meta[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    console.print(Panel(
        result["blog"],
        title=f"[bold green]Generated Blog — '{result['keyword']}'[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    # ── SAVE ──────────────────────────────────────────────────────────────────
    fname = save_output(result, config.company_name)
    console.print(f"\n[bold green]✓ Saved to:[/bold green] {fname}")
    console.print(Panel.fit(
        f"[bold]Done.[/bold] {result['keywords_found']} keywords found → "
        f"1 blog generated for {config.company_name}",
        border_style="magenta"
    ))


if __name__ == "__main__":
    run()