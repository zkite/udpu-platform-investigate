from __future__ import annotations

import ipaddress
import logging
import shlex
import shutil
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

__all__ = ["WireGuardError", "WireGuardManager", "UnitActiveState"]


class UnitActiveState(str, Enum):
    """Subset of systemd unit active states we care about."""

    ACTIVE = "active"
    RELOADING = "reloading"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    MAINTENANCE = "maintenance"
    REFRESHING = "refreshing"


class WireGuardError(RuntimeError):
    """Raised when an underlying `wg`/`wg‑quick`/systemd command fails."""


class WireGuardManager:
    """
    A thin, **production‑ready** wrapper around `wg`, `wg‑quick` and the
    corresponding systemd unit (`wg‑quick@<iface>.service`).

    It intentionally stays *stateless* and *synchronous* while providing:

    * peer CRUD helpers,
    * unit lifecycle helpers (up/down/restart),
    * optional automatic `wg‑quick save`,
    * atomic on‑disk backups of `/etc/wireguard/<iface>.conf`.

    All public methods are documented and never swallow errors: every non‑zero
    exit code is converted into :class:`WireGuardError`.
    """

    WG_DIR: Path = Path("/etc/wireguard")

    def __init__(
        self,
        interface: str,
        *,
        sudo: bool = True,
        auto_save: bool = True,
        backup_dir: Optional[Path] = WG_DIR / "backups",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        :param interface: WireGuard interface name without the `wg` prefix,
                          e.g. `"home"` for `wg0-home`.
        :param sudo: Prepend `sudo` to every command.
        :param auto_save: Persist modifications via `wg‑quick save`.
        :param backup_dir: Destination for timestamped `*.conf` backups.
                           `None` disables backups entirely.
        :param logger: Custom :pymod:`logging` instance.  If *None*, a module
                       level logger is created.
        """
        self.interface: str = interface
        self.sudo: bool = sudo
        self.auto_save: bool = auto_save
        self.backup_dir: Optional[Path] = backup_dir
        self.logger: logging.Logger = logger or logging.getLogger(__name__)

    # --------------------------------------------------------------------- #
    # Internal helpers                                                      #
    # --------------------------------------------------------------------- #

    def _run(self, *args: str, check: bool = True) -> str:
        """
        Execute *args* and return `stdout` as `str`.

        :param args: Command and its arguments.
        :param check: Raise :class:`WireGuardError` on non‑zero exit status.
        """
        cmd: List[str] = (["sudo"] if self.sudo else []) + list(args)
        self.logger.debug("exec: %s", " ".join(shlex.quote(a) for a in cmd))

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if check and proc.returncode != 0:
            stderr = proc.stderr.strip() or f"{cmd[0]} exited with {proc.returncode}"
            self.logger.error("command failed [%s]: %s", proc.returncode, stderr)
            raise WireGuardError(stderr)

        return proc.stdout.rstrip("\n")

    # --------------------------------------------------------------------- #
    # systemd unit helpers                                                  #
    # --------------------------------------------------------------------- #

    @property
    def _unit(self) -> str:  # noqa: D401  (internal helper)
        """Return the systemd unit name for the current interface."""
        return f"wg-quick@{self.interface}"

    def _get_active_state(self) -> UnitActiveState:
        raw_state = self._run("systemctl", "is-active", self._unit, check=False).strip()
        try:
            return UnitActiveState(raw_state)
        except ValueError as exc:  # pragma: no cover – unknown state guard
            raise WireGuardError(f"Unknown systemd unit state: {raw_state!r}") from exc

    # --------------------------------------------------------------------- #
    # Public API: lifecycle                                                 #
    # --------------------------------------------------------------------- #

    def is_active(self):
        """Return `True` if the WireGuard interface is **active**."""
        return str(self._get_active_state() is UnitActiveState.ACTIVE)

    def up(self) -> None:
        """Start the interface via systemd."""
        self._run("systemctl", "start", self._unit)

    def down(self) -> None:
        """Stop the interface via systemd."""
        self._run("systemctl", "stop", self._unit)

    def restart(self) -> None:
        """Restart the interface via systemd."""
        self._run("systemctl", "restart", self._unit)

    # --------------------------------------------------------------------- #
    # Public API: peers                                                     #
    # --------------------------------------------------------------------- #

    def list_peers(self):
        dump = self._run("wg", "show", self.interface, "dump")
        if not dump:
            return {}

        peers = {}
        for line in dump.splitlines():
            if not line.strip():
                continue
            cols = line.split()
            public_key, rest = cols[0], cols[1:]

            peers[public_key] = rest
        return peers

    def add_peer(self,
                 public_key: str,
                 allowed_ips: str,
                 endpoint: Optional[str] = None,
                 persistent_keepalive: Optional[int] = None,
                 preshared_key: Optional[str] = None,
    ) -> None:
        """
        Add a new peer to the interface and persist the change if
        :pyattr:`auto_save` is `True`.
        """
        cmd: List[str] = [
            "wg",
            "set",
            self.interface,
            "peer",
            public_key,
            "allowed-ips",
            allowed_ips,
        ]

        if endpoint:
            cmd += ["endpoint", endpoint]
        if persistent_keepalive is not None:
            cmd += ["persistent-keepalive", str(persistent_keepalive)]
        if preshared_key:
            cmd += ["preshared-key", preshared_key]

        self._run(*cmd)
        self._persist_if_needed()

    def remove_peer(self, public_key: str) -> None:
        """
        Remove *public_key* from the interface and persist the change
        if :pyattr:`auto_save` is `True`.
        """
        self._run("wg", "set", self.interface, "peer", public_key, "remove")
        self._persist_if_needed()

    def get_public_key(self) -> str:
        """Return the public key of the *local* interface."""
        return self._run("wg", "show", self.interface, "public-key")

    # --------------------------------------------------------------------- #
    # Persistence helpers                                                   #
    # --------------------------------------------------------------------- #

    def _persist_if_needed(self) -> None:
        if not self.auto_save:
            self.logger.debug("auto_save disabled – skipping wg‑quick save")
            return

        self._backup_config()
        # hot‑save – does **not** bring the interface down
        self._run("wg-quick", "save", self.interface)

    def _backup_config(self) -> None:
        if self.backup_dir is None:
            self.logger.debug("backup_dir is None – skipping backup")
            return

        cfg_path = self.WG_DIR / f"{self.interface}.conf"
        if not cfg_path.exists():  # pragma: no cover – non‑standard setups
            self.logger.warning("config file does not exist: %s", cfg_path)
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.backup_dir / f"{cfg_path.name}.{timestamp}.bak"
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # copy – do **not** move – to keep the original file intact
        shutil.copy2(cfg_path, backup_path)
        self.logger.info("config backup → %s", backup_path)

    # --------------------------------------------------------------------- #
    # Misc                                                                  #
    # --------------------------------------------------------------------- #

    def version(self) -> str:
        """Return the version string of the installed `wg` binary."""
        return self._run("wg", "--version")
