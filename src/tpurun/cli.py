from __future__ import annotations

import sys
from importlib.resources import files
from os import getlogin
from pathlib import Path
from typing import List, Optional

import typer
from typing_extensions import Annotated

from tpurun import __version__, console
from tpurun.app import TpuRunApp
from tpurun.model import TpuType, TpuVm

cli: typer.Typer = typer.Typer(no_args_is_help=True)


def version_callback(value: bool):
    if value is True:
        console.print(f"TPUrun v{__version__}")
        raise typer.Exit()


@cli.callback()
def callback(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version",
            show_default=False,
        ),
    ] = None,
):
    del version


@cli.command()
def exec(
    tpu_file: Annotated[
        Path,
        typer.Option(
            "--tpu-list",
            "-l",
            path_type=Path,
            help="Path to TPU VM list JSON file",
            rich_help_panel="TPU VM options",
        ),
    ] = "./tpus.json",
    tpu_kind: Annotated[
        Optional[TpuType],
        typer.Option(
            "--type",
            "-t",
            help="TPU node type",
            show_choices=True,
            rich_help_panel="TPU VM options",
        ),
    ] = TpuType.all,
    ssh_user: Annotated[
        Optional[str],
        typer.Option(
            "--user",
            "-u",
            help="Username to connect as",
            show_default=True,
            rich_help_panel="SSH options",
        ),
    ] = getlogin(),
    ssh_port: Annotated[
        Optional[int],
        typer.Option(
            "--port",
            "-p",
            help="SSH port to connect to",
            show_default=True,
            rich_help_panel="SSH options",
        ),
    ] = 22,
    connect_timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-T",
            help="SSH connect timeout",
            show_default=True,
            rich_help_panel="SSH options",
        ),
    ] = 10,
    command: Annotated[
        List[str],
        typer.Argument(help="Command to execute on TPU VMs"),
    ] = ...,
):
    """
    Main entrypoint for your application.
    """
    tpu_list = TpuVm.load_json(
        tpu_file=tpu_file,
        kind=tpu_kind,
        encoding="utf-8",
    )
    app = TpuRunApp(
        command=command,
        tpu_list=tpu_list,
        tpu_kind=tpu_kind,
        ssh_user=ssh_user,
        ssh_port=ssh_port,
        connect_timeout=connect_timeout,
    )
    app.run()
    sys.exit(0)
