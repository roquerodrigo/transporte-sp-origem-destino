"""``transporte-sp-od`` — one entry point for the disaggregation pipeline."""

from __future__ import annotations

import logging

import typer

app = typer.Typer(
    add_completion=False,
    help="Disaggregate the Metrô-SP OD 2023 survey from zone to address level.",
)


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v", help="debug logging")) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname).1s %(name)s: %(message)s",
    )


@app.command()
def fetch(source: str = typer.Argument("all", help="all | od | cnefe")) -> None:
    """Store a dated raw snapshot of the survey and/or the CNEFE archives."""
    from transporte_sp_od.sources import cnefe, survey

    if source in ("all", "od"):
        typer.echo("→ survey")
        survey_zip = __import__("transporte_sp_od.snapshot", fromlist=["download"])
        payload = survey_zip.download(
            __import__("transporte_sp_od.config", fromlist=["settings"]).settings.od_zip_url
        )
        survey_zip.write("od_survey", "od2023.zip", payload,
                         "metrosp OD2023", "Portal da Transparência Metrô-SP")
    if source in ("all", "cnefe"):
        typer.echo("→ cnefe (39 municipalities)")
        cnefe.fetch()
    _ = survey


@app.command()
def prepare() -> None:
    """Read CNEFE, assign each address to its OD zone, write data/dist/enderecos.parquet."""
    from transporte_sp_od.build import prepare as step

    step.run()


@app.command()
def build() -> None:
    """Disaggregate the survey onto the prepared addresses and write data/dist/."""
    from transporte_sp_od import export
    from transporte_sp_od.build import disaggregate

    summary = disaggregate.run()
    export.write_all(disaggregate.run.layers, summary)


@app.command()
def flows(
    target: int = typer.Option(
        None, "--target", help="number of address-level arcs to materialise (default 100000)"
    ),
) -> None:
    """Materialise the OD arcs by motive: fluxos.* (~target) + fluxos_completo.* (full, gzipped)."""
    from transporte_sp_od import export
    from transporte_sp_od.build import flows as step
    from transporte_sp_od.config import settings

    summary = step.run(target=target)
    export.write_flows(step.run.arcs, summary)
    export.write_flow_points(step.run.arcs)

    # The full base: one arc per ~people_per_point trips, the finest sensible resolution.
    full_target = round(summary["trips"] / settings.people_per_point)
    full_summary = step.run(target=full_target)
    export.write_flows(step.run.arcs, full_summary, stem="fluxos_completo", compress_csv=True)


if __name__ == "__main__":
    app()
