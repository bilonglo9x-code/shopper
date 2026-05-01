"""CLI interface for Shopper - Shopee data scraper."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from shopper.collectors.scraper import ShopeeScraper
from shopper.constants import DEFAULT_DOMAIN, SortBy
from shopper.exporters.exporter import export_csv, export_json, export_reviews_csv
from shopper.models import CategoryResult, Product, SearchResult, ShopDetail
from shopper.parsers.link_parser import detect_input

app = typer.Typer(
    name="shopper",
    help="Shopper - Thu thập dữ liệu từ Shopee",
    rich_markup_mode="rich",
)
console = Console()


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False, show_path=False)],
    )


def _print_product_summary(product: Product) -> None:
    """Print a summary of a scraped product."""
    table = Table(title=f"[bold]{product.name}[/bold]", show_header=False, padding=(0, 1))
    table.add_column("Field", style="cyan", width=25)
    table.add_column("Value", style="white")

    table.add_row("ID", f"{product.item_id}")
    table.add_row("Shop", f"{product.shop_info.name} (ID: {product.shop_id})")
    table.add_row("Brand", product.brand or "N/A")
    table.add_row(
        "Price",
        f"{product.price_info.price_min:,.0f} - "
        f"{product.price_info.price_max:,.0f} {product.price_info.currency}",
    )
    if product.price_info.price_before_discount:
        table.add_row(
            "Original Price",
            f"{product.price_info.price_min_before_discount:,.0f} - "
            f"{product.price_info.price_max_before_discount:,.0f}",
        )
        table.add_row("Discount", str(product.price_info.discount))
    table.add_row("Rating", f"{product.rating_summary.rating_star:.1f}/5")
    table.add_row("Sold", f"{product.historical_sold:,}")
    table.add_row("Stock", f"{product.stock:,}")
    table.add_row("Views", f"{product.view_count:,}")
    table.add_row("Likes", f"{product.liked_count:,}")
    table.add_row("Images", f"{len(product.images)}")
    table.add_row("Video", "Yes" if product.video_url else "No")
    table.add_row("Variants", f"{len(product.models)}")
    table.add_row("Attributes", f"{len(product.attributes)}")
    table.add_row("Reviews fetched", f"{len(product.reviews)}")
    if product.ctime:
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(product.ctime, tz=timezone.utc)
        table.add_row("Created", dt.strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("URL", product.url)

    console.print(table)


def _print_search_summary(result: SearchResult) -> None:
    """Print search results summary."""
    console.print(
        Panel(
            f"[bold]Search: '{result.keyword}'[/bold]\n"
            f"Total results: {result.total_count:,}\n"
            f"Fetched: {len(result.items)}",
            title="Search Results",
        )
    )
    if result.items:
        table = Table(title="Products", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", width=40)
        table.add_column("Price", justify="right", width=15)
        table.add_column("Sold", justify="right", width=10)
        table.add_column("Rating", justify="right", width=8)

        for i, item in enumerate(result.items[:20], 1):
            table.add_row(
                str(i),
                item.name[:40],
                f"{item.price_info.price_min:,.0f}",
                f"{item.historical_sold:,}",
                f"{item.rating_summary.rating_star:.1f}",
            )

        console.print(table)
        if len(result.items) > 20:
            console.print(f"  ... and {len(result.items) - 20} more products")


def _print_shop_summary(result: ShopDetail) -> None:
    """Print shop details summary."""
    shop = result.shop_info
    console.print(
        Panel(
            f"[bold]{shop.name}[/bold]\n"
            f"Username: {shop.username}\n"
            f"Location: {shop.shop_location}\n"
            f"Followers: {shop.follower_count:,}\n"
            f"Products: {shop.item_count:,}\n"
            f"Rating: {shop.rating_star:.1f}/5\n"
            f"Response rate: {shop.response_rate}%\n"
            f"Official: {'Yes' if shop.is_official_shop else 'No'}",
            title="Shop Info",
        )
    )
    console.print(f"  Fetched {len(result.items)} products")


@app.command()
def scrape(
    input_url: Annotated[
        str,
        typer.Argument(help="Shopee URL, keyword, or shop username to scrape"),
    ],
    output: Annotated[
        str | None,
        typer.Option(
            "--output", "-o",
            help="Output file path (auto-detects format from extension)",
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json or csv"),
    ] = "json",
    domain: Annotated[
        str,
        typer.Option("--domain", "-d", help="Shopee domain (e.g., shopee.vn, shopee.sg)"),
    ] = DEFAULT_DOMAIN,
    max_items: Annotated[
        int,
        typer.Option("--max-items", "-m", help="Maximum number of items to fetch (0 = all)"),
    ] = 0,
    reviews: Annotated[
        bool,
        typer.Option("--reviews", "-r", help="Include product reviews"),
    ] = False,
    max_reviews: Annotated[
        int,
        typer.Option("--max-reviews", help="Maximum reviews per product"),
    ] = 50,
    sort_by: Annotated[
        str,
        typer.Option("--sort", "-s", help="Sort by: relevancy, ctime, sales, price"),
    ] = "relevancy",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Verbose output"),
    ] = False,
) -> None:
    """Scrape data from Shopee - auto-detects URL type.

    Examples:
        shopper scrape "https://shopee.vn/product-name-i.123456.789012"
        shopper scrape "áo thun nam" --max-items 100
        shopper scrape "https://shopee.vn/shopname" --reviews
        shopper scrape "https://shopee.vn/Thoi-Trang-Nam-cat.11035567" -m 50
    """
    _setup_logging(verbose)
    asyncio.run(
        _scrape_async(
            input_url=input_url,
            output=output,
            format=format,
            domain=domain,
            max_items=max_items,
            reviews=reviews,
            max_reviews=max_reviews,
            sort_by=sort_by,
        )
    )


async def _scrape_async(
    input_url: str,
    output: str | None,
    format: str,
    domain: str,
    max_items: int,
    reviews: bool,
    max_reviews: int,
    sort_by: str,
) -> None:
    """Async scraping logic."""
    # Detect input type first
    parsed = detect_input(input_url)
    console.print(f"[cyan]Detected type:[/cyan] [bold]{parsed.link_type}[/bold]")

    if parsed.domain:
        domain = parsed.domain

    try:
        async with ShopeeScraper(domain=domain) as scraper:
            result = await scraper.scrape(
                input_url,
                max_items=max_items,
                include_reviews=reviews,
                max_reviews=max_reviews,
                sort_by=SortBy(sort_by),
            )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "[yellow]Tip:[/yellow] Shopee may block requests from servers. "
            "Try using --domain or providing cookies via the Python API."
        )
        raise typer.Exit(code=1)

    # Display summary
    if isinstance(result, Product):
        _print_product_summary(result)
    elif isinstance(result, SearchResult):
        _print_search_summary(result)
    elif isinstance(result, ShopDetail):
        _print_shop_summary(result)
    elif isinstance(result, CategoryResult):
        console.print(
            f"[cyan]Category {result.category_id}:[/cyan] "
            f"{result.total_count:,} total, fetched {len(result.items)}"
        )

    # Export
    if output:
        output_path = Path(output)
        ext = output_path.suffix.lower()
        if ext == ".csv" or format == "csv":
            export_csv(result, output_path)
            if isinstance(result, Product) and result.reviews:
                reviews_path = output_path.with_name(
                    output_path.stem + "_reviews.csv"
                )
                export_reviews_csv(result, reviews_path)
                console.print(f"[green]Reviews exported to:[/green] {reviews_path}")
        else:
            export_json(result, output_path)

        console.print(f"[green]Data exported to:[/green] {output_path}")
    else:
        # Default output path
        if isinstance(result, Product):
            default_name = f"product_{result.item_id}"
        elif isinstance(result, SearchResult):
            safe_kw = result.keyword.replace(" ", "_")[:30]
            default_name = f"search_{safe_kw}"
        elif isinstance(result, ShopDetail):
            default_name = f"shop_{result.shop_info.shop_id}"
        elif isinstance(result, CategoryResult):
            default_name = f"category_{result.category_id}"
        else:
            default_name = "output"

        output_dir = Path("output")
        if format == "csv":
            path = export_csv(result, output_dir / f"{default_name}.csv")
        else:
            path = export_json(result, output_dir / f"{default_name}.json")

        console.print(f"[green]Data exported to:[/green] {path}")


@app.command()
def detect(
    input_text: Annotated[
        str,
        typer.Argument(help="URL or text to detect"),
    ],
) -> None:
    """Detect the type of a Shopee URL or input.

    Examples:
        shopper detect "https://shopee.vn/product-i.123.456"
        shopper detect "áo thun nam"
    """
    parsed = detect_input(input_text)
    table = Table(title="Link Detection Result", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Type", parsed.link_type)
    table.add_row("Domain", parsed.domain or "N/A")
    if parsed.shop_id is not None:
        table.add_row("Shop ID", str(parsed.shop_id))
    if parsed.item_id is not None:
        table.add_row("Item ID", str(parsed.item_id))
    if parsed.category_id is not None:
        table.add_row("Category ID", str(parsed.category_id))
    if parsed.keyword is not None:
        table.add_row("Keyword", parsed.keyword)
    table.add_row("Original URL", parsed.original_url)

    console.print(table)


@app.command()
def info() -> None:
    """Show supported Shopee domains and URL formats."""
    from shopper.constants import SHOPEE_DOMAINS

    console.print(Panel("[bold]Shopper[/bold] - Shopee Data Scraper", title="Info"))

    table = Table(title="Supported Domains")
    table.add_column("Code", style="cyan")
    table.add_column("Domain", style="white")
    for code, domain in SHOPEE_DOMAINS.items():
        table.add_row(code, domain)
    console.print(table)

    console.print("\n[bold]Supported URL formats:[/bold]")
    console.print("  Product: https://shopee.vn/Product-Name-i.{shop_id}.{item_id}")
    console.print("  Product: https://shopee.vn/product/{shop_id}/{item_id}")
    console.print("  Shop:    https://shopee.vn/{shop_username}")
    console.print("  Shop:    https://shopee.vn/shop/{shop_id}")
    console.print("  Category: https://shopee.vn/Category-Name-cat.{category_id}")
    console.print("  Search:  https://shopee.vn/search?keyword={keyword}")
    console.print("  Keyword: any text (auto-detected as search)")


if __name__ == "__main__":
    app()
