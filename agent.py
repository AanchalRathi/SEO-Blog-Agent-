
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule

from keyword_discovery import discover_all_keywords
from keyword_analysis import analyze_keywords
from blog_generator import generate_blog

console = Console()

def run():

    os.makedirs("output", exist_ok=True)

    console.print(Panel.fit(
        "[bold magenta] Times Prime SEO Agent[/bold magenta]\n"
        "[dim]Keyword Discovery  →  Scoring  →  Blog Generation[/dim]",
        border_style="magenta"
    ))

    # mode selection
    console.print("\n[bold cyan]Choose mode:[/bold cyan]")
    console.print("  [green]1[/green] → Type a search query  (like Google)")
    console.print("  [green]2[/green] → Auto run on default seeds\n")

    mode = input("Enter 1 or 2: ").strip()

    if mode == "1":
        console.print("\n[dim]Examples: 'zomato gold coupon'  |  'hotstar offer india'  |  'times prime vs amazon'[/dim]")
        user_query = input("🔍 Your search: ").strip()

        if not user_query:
            console.print("[yellow]No input — running on default seeds.[/yellow]\n")
            from keyword_discovery import discover_all_keywords
            raw = discover_all_keywords()
        else:
            from keyword_discovery import discover_from_input
            console.print(f"\n[green]Running for:[/green] [white]{user_query}[/white]\n")
            raw = discover_from_input(user_query)
    else:
        from keyword_discovery import discover_all_keywords
        raw = discover_all_keywords()

    #phase 1
    console.print(Rule("[bold cyan]Phase 1 — Keyword Discovery[/bold cyan]"))
    console.print(f"[green] Discovered {len(raw)} unique keywords[/green]\n")

    # phase 2
    console.print(Rule("[bold cyan]Phase 2 — Scoring & Intent Analysis[/bold cyan]"))

    analyzed = analyze_keywords(raw)

    table = Table(header_style="bold cyan", border_style="dim", show_lines=True)
    table.add_column("#",       width=4)
    table.add_column("Keyword", width=42)
    table.add_column("Intent",  width=19)
    table.add_column("Score",   width=16)
    table.add_column("Source",  width=19)

    intent_colors = {
        "transactional": "green",
        "informational": "blue",
        "commercial":    "yellow"
    }

    for i, kw in enumerate(analyzed[:15], 1):
        color = intent_colors.get(kw["intent"], "white")
        table.add_row(
            str(i),
            kw["keyword"],
            f"[{color}]{kw['intent']}[/{color}]",
            f"[green]{kw['score']}[/green]" if kw["score"] >= 70 else f"[yellow]{kw['score']}[/yellow]",
            kw["source"]
        )

    console.print(table)

    best = analyzed[0]
    related = [k["keyword"] for k in analyzed[1:12]]

    console.print(f"\n[bold green] Best keyword selected:[/bold green] [bold white]{best['keyword']}[/bold white]")
    console.print(f"  Intent: [yellow]{best['intent']}[/yellow]   Score: [green]{best['score']}[/green]\n")

    # phase 3
    console.print(Rule("[bold cyan]Phase 3 — SEO Blog Generation (Llama 3.3 via Groq)[/bold cyan]"))
    console.print("[dim]Generating full blog post...[/dim]\n")

    blog = generate_blog(best["keyword"], best["intent"], related)

    console.print(Panel(
        blog,
        title=f"[bold green]Generated Blog — '{best['keyword']}'[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = best["keyword"][:40].replace(" ", "_").replace("/", "-").replace("?", "")
    fname = f"output/blog_{safe_keyword}_{timestamp}.txt"

    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"KEYWORD: {best['keyword']}\n")
        f.write(f"INTENT: {best['intent']} | SCORE: {best['score']}\n\n")
        f.write(blog)

    console.print(f"\n[bold green] Saved to:[/bold green] {fname}")
    console.print(Panel.fit(
        f"[bold]Done.[/bold] {len(raw)} keywords found → top 15 shown → 1 blog generated",
        border_style="magenta"
    ))

if __name__ == "__main__":
    run()