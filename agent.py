from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule

from keyword_discovery import discover_all_keywords
from keyword_analysis import analyze_keywords
from blog_generator import generate_blog

console = Console()

def run():
    console.print(Panel.fit(
        "[bold magenta] Times Prime SEO Agent[/bold magenta]\n"
        "[dim]Keyword Discovery  →  Scoring  →  Blog Generation[/dim]",
        border_style="magenta"
    ))

    # phase 1
    console.print(Rule("[bold cyan]Phase 1 — Keyword Discovery[/bold cyan]"))
    console.print("[dim]Scraping Google autocomplete + Serper related searches...[/dim]\n")

    raw = discover_all_keywords()# returns a list of dicts and stores it in raw
    console.print(f"[green] Discovered {len(raw)} unique keywords[/green]\n")

    #phase 2
    console.print(Rule("[bold cyan]Phase 2 — Scoring & Intent Analysis[/bold cyan]"))

    analyzed = analyze_keywords(raw)#returns a new list sorted by score descending

    table = Table(header_style="bold cyan", border_style="dim", show_lines=True)
    table.add_column("#",        width=4)
    table.add_column("Keyword",  width=42)
    table.add_column("Intent",   width=19)
    table.add_column("Score",    width=16)
    table.add_column("Source",   width=19)

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

    best = analyzed[0]#blog written about this keyword
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

    #save to file
    fname = "output_blog.txt"
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