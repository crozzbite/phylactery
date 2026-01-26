import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer()
console = Console()
API_URL = "http://localhost:8000"

def print_banner() -> None:
    banner = r"""
    [bold red]
      _____  _           _            _
     |  __ \| |         | |          | |
     | |__) | |__  _   _| | __ _  ___| |_ ___ _ __ _   _
     |  ___/| '_ \| | | | |/ _` |/ __| __/ _ \ '__| | | |
     | |    | | | | |_| | | (_| | (__| ||  __/ |  | |_| |
     |_|    |_| |_|\__, |_|\__,_|\___|\__\___|_|   \__, |
                    __/ |                           __/ |
                   |___/                           |___/
    [/bold red]
    [white]Bones + Brain Architecture v0.1.0[/white]
    """
    console.print(banner)

@app.command(name="list")
def list_agents() -> None:
    """List all awake agents."""
    try:
        response = httpx.get(f"{API_URL}/")
        data = response.json()

        agents = data.get("loaded_agents", [])

        console.print(Panel(f"[bold green]Connected to {data['status']}[/bold green]", title="Status"))

        console.print("\n[bold white]Awake Agents:[/bold white]")
        for agent in agents:
            console.print(f"  💀 [cyan]{agent}[/cyan]")

    except httpx.ConnectError:
        console.print(
            "[bold red]❌ Could not connect to Phylactery API. Is it running on localhost:8000?[/bold red]"
        )

@app.command()
def chat(agent: str) -> None:
    """Start a chat session with an agent."""
    print_banner()
    console.print(f"[bold white]Connecting to agent:[/bold white] [cyan]{agent}[/cyan]...")

    try:
        response = httpx.get(f"{API_URL}/")
        agents = response.json().get("loaded_agents", [])
        if agent not in agents:
            console.print(f"[bold red]❌ Agent '{agent}' not found.[/bold red]")
            console.print(f"Available agents: {', '.join(agents)}")
            return
    except httpx.RequestError:
        console.print("[bold red]❌ API Offline.[/bold red]")
        return

    console.print("[dim]Type 'exit' or 'quit' to end session.[/dim]\n")

    while True:
        user_input = Prompt.ask("[bold green]You[/bold green]")

        if user_input.lower() in ["exit", "quit"]:
            console.print("[bold red]Disconnecting...[/bold red]")
            break

        with console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
            try:
                response = httpx.post(
                    f"{API_URL}/chat/{agent}",
                    json={"message": user_input},
                    timeout=60.0 # Generous timeout for local LLMs
                )

                if response.status_code == 200:
                    data = response.json()
                    ai_response = data.get("response", "No response content")
                    console.print(f"\n[bold cyan]{agent}[/bold cyan]: {ai_response}\n")
                else:
                    console.print(f"[bold red]Error {response.status_code}:[/bold red] {response.text}")

            except httpx.TimeoutException:
                 console.print("[bold red]❌ Response timed out.[/bold red]")

if __name__ == "__main__":
    app()
