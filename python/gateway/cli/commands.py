"""
CLI commands for the AI Gateway.
"""
import logging
import os
import sys
import time
import click
import yaml
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from gateway.constants import LOGO, APP_VERSION
from gateway.telemetry.setup import init_telemetry
from gateway.core.models import model_registry
from gateway.main import run_server


# Set up console
console = Console()


@click.group()
@click.version_option(APP_VERSION)
def main():
    """AI Gateway - Govern, Secure, and Optimize your AI Traffic."""
    console.print(LOGO, style="bold blue")
    console.print(f"[bold]AI Gateway[/bold] v{APP_VERSION}", style="blue")
    console.print()


@main.command()
@click.option("--host", help="Host to bind to")
@click.option("--port", type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--log-level", help="Log level")
def serve(host: Optional[str] = None, port: Optional[int] = None, reload: bool = False, log_level: Optional[str] = None):
    """Start the AI Gateway server."""
    run_server(host, port, reload, log_level)


@main.command()
def models():
    """List available models."""
    # Initialize telemetry
    init_telemetry()
    
    # Load models
    models_path = os.environ.get("MODELS_PATH") or "models.yaml"
    models = model_registry.load_models(models_path)
    
    if not models:
        console.print("[bold red]No models found![/bold red]")
        return
    
    # Create table
    table = Table(title="Available Models")
    table.add_column("ID", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Input Cost", style="magenta")
    table.add_column("Output Cost", style="magenta")
    table.add_column("Context Size", style="blue")
    
    # Add rows
    for model in models:
        table.add_row(
            model.model,
            model.model_provider,
            model.type.value,
            f"${model.price.per_input_token * 1000000:.6f}/M",
            f"${model.price.per_output_token * 1000000:.6f}/M",
            str(model.limits.max_context_size)
        )
    
    # Print table
    console.print(table)


@main.command()
def info():
    """Show system information."""
    # Initialize telemetry
    init_telemetry()
    
    # Get system info
    import platform
    import psutil
    
    # Create table
    table = Table(title="System Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    # Add system info
    table.add_row("Platform", platform.platform())
    table.add_row("Python Version", platform.python_version())
    table.add_row("Processor", platform.processor() or "Unknown")
    table.add_row("CPU Cores", str(psutil.cpu_count(logical=False)))
    table.add_row("Logical CPUs", str(psutil.cpu_count(logical=True)))
    table.add_row("Memory", f"{psutil.virtual_memory().total / (1024**3):.2f} GB")
    table.add_row("Environment", os.environ.get("ENVIRONMENT") or "development")
    
    # Print table
    console.print(table)
    
    # Show loaded models count
    models_path = os.environ.get("MODELS_PATH") or "models.yaml"
    models = model_registry.load_models(models_path)
    console.print(f"[bold]Models:[/bold] {len(models)}")


@main.command()
@click.option("--endpoint", help="Endpoint URL to test")
@click.option("--model", help="Model to test")
@click.option("--prompt", help="Prompt to test")
def test(endpoint: Optional[str] = None, model: Optional[str] = None, prompt: Optional[str] = None):
    """Test the AI Gateway."""
    import httpx
    
    # Set defaults
    endpoint = endpoint or "http://localhost:8000/v1/chat/completions"
    model = model or "gpt-3.5-turbo"
    prompt = prompt or "Hello, world!"
    
    # Create request
    request = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    console.print(f"[bold]Testing endpoint:[/bold] {endpoint}")
    console.print(f"[bold]Model:[/bold] {model}")
    console.print(f"[bold]Prompt:[/bold] {prompt}")
    console.print()
    
    # Send request
    with Progress() as progress:
        task = progress.add_task("[cyan]Sending request...", total=1)
        
        start_time = time.time()
        
        try:
            response = httpx.post(
                endpoint,
                json=request,
                timeout=30.0
            )
            
            elapsed_time = time.time() - start_time
            progress.update(task, completed=1)
            
            # Print response
            if response.status_code == 200:
                console.print(f"[bold green]Success![/bold green] ({elapsed_time:.2f}s)")
                
                # Parse response
                response_json = response.json()
                
                # Extract content
                content = "No content"
                if "choices" in response_json and response_json["choices"]:
                    first_choice = response_json["choices"][0]
                    if "message" in first_choice and "content" in first_choice["message"]:
                        content = first_choice["message"]["content"]
                
                # Show usage
                if "usage" in response_json:
                    usage = response_json["usage"]
                    console.print(f"[bold]Tokens:[/bold] {usage.get('total_tokens', 0)} total "
                                 f"({usage.get('prompt_tokens', 0)} prompt, {usage.get('completion_tokens', 0)} completion)")
                
                # Show content
                console.print(Panel(content, title="Response", border_style="green"))
                
            else:
                console.print(f"[bold red]Error {response.status_code}![/bold red] ({elapsed_time:.2f}s)")
                console.print(Panel(response.text, title="Error Response", border_style="red"))
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            progress.update(task, completed=1)
            console.print(f"[bold red]Error![/bold red] ({elapsed_time:.2f}s)")
            console.print(Panel(str(e), title="Exception", border_style="red"))


@main.command()
@click.option("--file", default="models.yaml", help="Path to models file")
@click.option("--force", is_flag=True, help="Force update even if up to date")
def update(file: str = "models.yaml", force: bool = False):
    """Update models from GitHub."""
    import httpx
    
    # Initialize telemetry
    init_telemetry()
    
    console.print("[bold]Updating models...[/bold]")
    
    # GitHub raw URL for models.yaml
    github_url = "https://raw.githubusercontent.com/example/ai-gateway/main/models.yaml"
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Downloading models...", total=1)
        
        try:
            # Get models file from GitHub
            response = httpx.get(github_url)
            
            if response.status_code == 200:
                # Parse models
                models_data = yaml.safe_load(response.text)
                
                # Write to file
                with open(file, "w") as f:
                    yaml.dump(models_data, f)
                
                progress.update(task, completed=1)
                console.print(f"[bold green]Successfully updated {len(models_data)} models![/bold green]")
                
            else:
                progress.update(task, completed=1)
                console.print(f"[bold red]Failed to download models: HTTP {response.status_code}[/bold red]")
                console.print(response.text)
                sys.exit(1)
            
        except Exception as e:
            progress.update(task, completed=1)
            console.print(f"[bold red]Error updating models: {str(e)}[/bold red]")
            sys.exit(1)


if __name__ == "__main__":
    main()