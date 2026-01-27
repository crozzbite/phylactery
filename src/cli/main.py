import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer()
console = Console()
API_URL = "http://127.0.0.1:8000"

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
def chat(
    agent: str = typer.Argument("phylactery", help="The agent to chat with"),
    message: str | None = typer.Option(None, "--message", "-m", help="Send a single message and exit"),
) -> None:
    """Start a chat session with an agent. Defaults to 'phylactery' agent."""
    
    # 0. One-shot mode (No banner, direct output)
    if message:
        try:
            response = httpx.post(
                f"{API_URL}/chat/{agent}",
                json={"message": message},
                timeout=120.0
            )
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get("response", "No response content")
                console.print(ai_response) # Just print content for scripting
            else:
                 try:
                     error_detail = response.json().get("detail", response.text)
                     console.print(f"[bold red]Error {response.status_code}:[/bold red] {error_detail}")
                 except Exception:
                     console.print(f"[bold red]Error {response.status_code}[/bold red]")
            return
        except Exception as e:
            console.print(f"[bold red]Error sending message:[/bold red] {e}")
            return

    # 1. Interactive Mode
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
                    timeout=120.0 # Extended timeout for local LLMs
                )

                if response.status_code == 200:
                    data = response.json()
                    ai_response = data.get("response", "No response content")
                    console.print(f"\n[bold cyan]{agent}[/bold cyan]: {ai_response}\n")
                else:
                    try:
                        error_detail = response.json().get("detail", response.text)
                        console.print(f"[bold red]Server Error {response.status_code}:[/bold red] {error_detail}")
                    except Exception:
                        console.print(f"[bold red]Error {response.status_code}:[/bold red] {response.text}")

            except httpx.TimeoutException:
                 console.print("[bold red]❌ Response timed out.[/bold red]")

@app.command()
def doctor() -> None:
    """Diagnose the health of Phylactery and its brains."""
    console.print("[bold yellow]Running diagnostics...[/bold yellow]\n")

    # 1. API Check
    try:
        with console.status("[bold white]Checking API...[/bold white]"):
            response = httpx.get(f"{API_URL}/", timeout=10.0)
            if response.status_code == 200:
                console.print("✅ [green]API is Alive and breathing.[/green]")
            else:
                console.print(f"❌ [red]API returned error {response.status_code}[/red]")
    except Exception as e:
        console.print(f"❌ [red]API is Offline:[/red] {str(e)}")
        return

    # 2. Ollama Check
    try:
        with console.status("[bold white]Checking Ollama connection...[/bold white]"):
            # We try to ping the API which in turns pings Ollama
            response = httpx.post(f"{API_URL}/chat/phylactery", json={"message": "ping"}, timeout=30.0)
            if response.status_code == 200:
                console.print("✅ [green]Ollama is connected and responding.[/green]")
            else:
                 try:
                     error_detail = response.json().get("detail", "Unknown error")
                     if "connection error" in error_detail.lower() or "not found" in error_detail.lower():
                         console.print(f"❌ [red]Ollama service not found or failing:[/red] {error_detail}")
                     else:
                         console.print(f"❌ [red]Ollama connection test failed:[/red] {error_detail}")
                 except Exception:
                     console.print(f"❌ [red]Ollama connection test failed via API (Status {response.status_code}).[/red]")
    except httpx.TimeoutException:
        console.print("⚠️  [yellow]Ollama/API timed out during diagnosis (taking >30s).[/yellow]")
    except Exception as e:
        console.print(f"❌ [red]Ollama Check failed:[/red] {str(e)}")

    console.print("\n[bold green]Diagnostics complete.[/bold green]")


if __name__ == "__main__":
    app()
