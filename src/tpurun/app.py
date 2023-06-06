from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import asyncssh
import typer
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TextLog
from textual.worker import Worker, WorkerState

from tpurun import __version__
from tpurun.model import TpuType, TpuVm

cli: typer.Typer = typer.Typer(no_args_is_help=True)


class SshLog(TextLog):
    DEFAULT_CSS = """
    SshLog{
        background: $surface;
        border: solid cornflowerblue;
        border-title-align: left;
        border-title-color: white;
        border-subtitle-align: right;
        border-subtitle-color: white;
        color: $text;
        height: 1fr;
        margin: 0 1;
        overflow-y: scroll;
    }
    """

    def __init__(self, *, tpu: TpuVm, **kwargs) -> None:
        id = kwargs.pop("id", f"ssh_{tpu.name}")
        name = kwargs.pop("name", tpu.name)
        max_lines = kwargs.pop("max_lines", None)
        super().__init__(id=id, name=name, max_lines=max_lines, **kwargs)
        # attach tpu object to self
        self.tpu = tpu
        # set border title and subtitle
        self.border_title = f"{self.tpu.name}"
        self.set_status("Preparing...", "orange")
        pass

    def set_status(self, status: str, color: Optional[str] = None) -> None:
        self.border_subtitle = status
        if color is not None:
            self.styles.border_subtitle_color = color


class TpuRunApp(App):
    TITLE = "TPUrun"
    CSS_PATH = files("tpurun.data").joinpath("app.css")
    BINDINGS = [
        Binding(key="q,esc", action="quit", description="Quit"),
        Binding(key="s", action="save_logs", description="Save logs"),
        Binding(key="t", action="toggle_dark", description="Toggle dark mode", show=False),
    ]

    def __init__(
        self,
        tpu_list: List[TpuVm] = ...,
        tpu_kind: TpuType = ...,
        ssh_user: str = ...,
        ssh_port: int = ...,
        connect_timeout: int = ...,
        command: List[str] = ...,
    ):
        self.command = command
        self.tpu_list = tpu_list
        self.tpu_kind = tpu_kind
        self.ssh_user = ssh_user
        self.ssh_port = ssh_port
        self.connect_timeout = connect_timeout

        self._num_vms = len(self.tpu_list)
        self._kind_str = (
            f"TPU{self.tpu_kind.value}"
            if self.tpu_kind is not None and self.tpu_kind.value not in ["all", "any"]
            else "TPU"
        )
        super().__init__()

    def compose(self) -> ComposeResult:
        self.title = f"TPUrun {__version__}"
        self.sub_title = f"Running command on {self._num_vms} {self._kind_str} VMs"
        self.header = Header(id="Header", show_clock=True)
        self.footer = Footer()
        self.footer.id = "Footer"

        yield self.header
        for tpu in self.tpu_list:
            yield SshLog(tpu=tpu)
        yield self.footer

    def on_ready(self) -> None:
        self.result = 1
        self.tpu_workers = [
            self.run_worker(
                self.run_on_tpu(tpu),
                name=f"ssh_{tpu.name}",
                exit_on_error=False,
            )
            for tpu in self.tpu_list
        ]
        self.run_worker(self.worker_watcher(), name="watcher", exit_on_error=False)

    async def run_on_tpu(self, tpu: TpuVm) -> None:
        tpu_log: SshLog = self.query_one(f"#ssh_{tpu.name}", SshLog)
        tpu_log.set_status(f"Connecting to {tpu.externalIp}...")
        exit_code = None
        try:
            async with asyncssh.connect(
                host=tpu.externalIp,
                port=self.ssh_port,
                username=self.ssh_user,
                known_hosts=None,
            ) as conn:
                tpu_log.set_status("Connected", "green")
                command_str = " ".join(self.command)
                tpu_log.write(f"{self.ssh_user}@{tpu.name}$ {command_str}")
                async with conn.create_process(command_str) as process:
                    async for line in process.stdout:
                        tpu_log.write(line)
                    exit_code = process.exit_status
                tpu_log.write("--- SSH connection closed ---")
            tpu_log.set_status(f"Completed (exit {exit_code})", "lime")
        except Exception as e:
            tpu_log.set_status(f"Failed: {e}", "red")
            exit_code = 1
        return exit_code

    async def worker_watcher(self) -> None:
        # wait for all workers to complete
        await self.workers.wait_for_complete(self.tpu_workers)
        results = [x.result for x in self.tpu_workers]
        # set return value to 0 if all workers completed successfully
        if all([x == 0 for x in results]):
            self.result = 0
            # change footer color to green if all workers completed successfully
            self.footer.styles.animate("background", value="lime", duration=0.5)
            self.sub_title = f"Execution complete on {self._num_vms} VMs"
        else:
            # change footer color to red if any worker failed, and save logs
            num_failed = len([x != 0 for x in results])
            self.footer.styles.animate("background", value="darkred", duration=0.5)
            self.sub_title = f"Command failed on {num_failed}/{self._num_vms} VMs! Saving logs..."
            self.action_save_logs()
            self.sub_title = f"Command failed on {num_failed}/{self._num_vms} VMs! Logs saved."

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Worker state change event handler."""
        # log event to console
        self.log(event)
        if event.state not in {WorkerState.PENDING, WorkerState.RUNNING}:
            self.log(f"Worker {event.worker.name} finished with result: {event.worker.result}")
        if event.state == WorkerState.ERROR:
            self.log(f"Worker {event.worker.name} failed with exception: {event.worker.result}")
            self.footer.styles.animate("background", value="red", duration=0.2)

    def action_save_logs(self):
        log_name = self.TITLE.replace(" ", "_").lower()
        log_file = Path.cwd().joinpath(f"{log_name}.log")
        with log_file.open("a", encoding="utf-8") as f:
            for tpu in self.tpu_list:
                f.write(f"\n-------- {tpu.name} --------\n")
                tpu_log: SshLog = self.query_one(f"#ssh_{tpu.name}", SshLog)
                f.writelines([(x.text + "\n") for x in tpu_log.lines])
                f.write("\n")
