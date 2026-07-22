"""``transporte-sp-od`` — one entry point for the disaggregation pipeline."""

from __future__ import annotations

import logging

import typer

app = typer.Typer(
    add_completion=False,
    help="Map the Metrô-SP OD 2023 survey at its real coordinates: demand and trips.",
)


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v", help="debug logging")) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname).1s %(name)s: %(message)s",
    )


@app.command()
def fetch() -> None:
    """Store a dated raw snapshot of the OD survey."""
    from transporte_sp_od import snapshot
    from transporte_sp_od.config import settings

    typer.echo("→ survey")
    payload = snapshot.download(settings.od_zip_url)
    snapshot.write("od_survey", "od2023.zip", payload,
                   "metrosp OD2023", "Portal da Transparência Metrô-SP")


@app.command()
def build() -> None:
    """Materialise the demand point layers from the survey's coordinates and write data/dist/."""
    from transporte_sp_od import export
    from transporte_sp_od.build import demand

    summary = demand.run()
    export.write_all(demand.run.layers, summary)


@app.command()
def flows() -> None:
    """Compile the observed origin→destination trips at their real coordinates to data/dist/."""
    from transporte_sp_od import export
    from transporte_sp_od.build import flows as step

    summary = step.run()
    export.write_flows(step.run.arcs, summary)
    export.write_flow_points(step.run.arcs)

    # Lighter subsamples for smaller downloads; each still sums to the full daily total.
    for target, stem in ((50_000, "fluxos_50k"), (20_000, "fluxos_20k")):
        lighter, light_summary = step.subsample(step.run.arcs, target)
        export.write_flows(lighter, light_summary, stem=stem)


if __name__ == "__main__":
    app()
