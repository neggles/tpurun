from os import getlogin
from pathlib import Path
from typing import Annotated, List, Optional, Union

import typer

from tpurun import __version__, console
from tpurun.app import TpuRunApp
from tpurun.model import TpuType, TpuVm

cli: typer.Typer = typer.Typer(
    context_settings=dict(help_option_names=["-h", "--help"]),
    rich_markup_mode="rich",
)


def version_callback(value: bool):
    if value is True:
        console.print(f"TPUrun v{__version__}")
        raise typer.Exit()


def int_list_callback(value: str):
    return [int(node) for node in value.split(",")]


@cli.command(
    help="Execute a command on one or more TPU VMs",
    no_args_is_help=True,
    rich_help_panel="TPUrun options",
)
def exec(
    tpu_file: Annotated[
        Path,
        typer.Option(
            ...,
            "--tpu-file",
            "-f",
            path_type=Path,
            help="Path to TPU VM list JSON file",
            rich_help_panel="TPU VM",
        ),
    ] = "./tpus.json",
    tpu_kind: Annotated[
        TpuType,
        typer.Option(
            "--type",
            "-t",
            help="TPU node type",
            show_choices=True,
            rich_help_panel="TPU VM",
        ),
    ] = TpuType.all,
    tpu_nodes: Annotated[
        Optional[str],
        typer.Option(
            "--nodes",
            "-n",
            help="TPU node number (multiple allowed, must specify node type)",
            rich_help_panel="TPU VM",
            show_default=False,
            callback=int_list_callback,
        ),
    ] = None,
    ssh_user: Annotated[
        Optional[str],
        typer.Option(
            "--user",
            "-u",
            help="Username to connect as",
            rich_help_panel="SSH",
        ),
    ] = getlogin(),
    ssh_port: Annotated[
        Optional[int],
        typer.Option(
            "--port",
            "-P",
            help="SSH port to connect to",
            show_default=True,
            rich_help_panel="SSH",
        ),
    ] = 22,
    connect_timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-T",
            help="SSH connect timeout",
            show_default=True,
            rich_help_panel="SSH",
        ),
    ] = 10,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            is_flag=True,
            help="Show version",
        ),
    ] = None,
    command: Annotated[
        List[str],
        typer.Argument(help="Command to execute on TPU VMs"),
    ] = ...,
):
    """
    Main entrypoint for your application.
    """
    if tpu_nodes is not None:
        if tpu_kind is TpuType.all:
            raise typer.BadParameter("Cannot filter by node number without specifying node type")
        tpu_nodes = sorted(tpu_nodes)

    tpu_list = TpuVm.load_json(tpu_file=tpu_file, kind=tpu_kind, encoding="utf-8")
    tpu_list = TpuVm.filter_tpu_vms(tpu_vms=tpu_list, kind=tpu_kind, nodes=tpu_nodes)
    app = TpuRunApp(
        command=command,
        tpu_list=tpu_list,
        tpu_kind=tpu_kind,
        ssh_user=ssh_user,
        ssh_port=ssh_port,
        connect_timeout=connect_timeout,
    )
    app.run()
    raise typer.Exit()
