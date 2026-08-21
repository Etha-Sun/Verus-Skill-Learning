#!/usr/bin/env python3
"""Enter a read-isolated mount namespace, then execute one Codex actor."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import errno
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


DEFAULT_SCRATCH_ROOT = Path(
    os.environ.get(
        "VERUS_SKILL_SCRATCH_ROOT", str(Path(__file__).resolve().parents[3])
    )
)
IP_BIN = Path("/usr/sbin/ip")
UNSHARE_BIN = Path("/usr/bin/unshare")

PR_CAPBSET_DROP = 24
PR_SET_SECUREBITS = 28
PR_SET_NO_NEW_PRIVS = 38
SECBIT_NOROOT = 1
SECBIT_NOROOT_LOCKED = 2
SECBIT_NO_SETUID_FIXUP = 4
SECBIT_NO_SETUID_FIXUP_LOCKED = 8
LINUX_CAPABILITY_VERSION_3 = 0x20080522
SCMP_ACT_ALLOW = 0x7FFF0000
SCMP_ACT_ERRNO = 0x00050000
SCMP_CMP_MASKED_EQ = 7
CLONE_NAMESPACE_FLAGS = (
    0x00020000,  # CLONE_NEWNS
    0x02000000,  # CLONE_NEWCGROUP
    0x04000000,  # CLONE_NEWUTS
    0x08000000,  # CLONE_NEWIPC
    0x10000000,  # CLONE_NEWUSER
    0x20000000,  # CLONE_NEWPID
    0x40000000,  # CLONE_NEWNET
)
FORBIDDEN_ACTOR_SYSCALLS = (
    "mount",
    "umount2",
    "pivot_root",
    "move_mount",
    "open_tree",
    "fsopen",
    "fsconfig",
    "fsmount",
    "fspick",
    "mount_setattr",
    "unshare",
    "setns",
    "chroot",
    "ptrace",
    "process_vm_readv",
    "process_vm_writev",
    "bpf",
    "perf_event_open",
    "kexec_load",
    "init_module",
    "finit_module",
    "delete_module",
    "reboot",
    "swapon",
    "swapoff",
)


class CapabilityHeader(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


class CapabilityData(ctypes.Structure):
    _fields_ = [
        ("effective", ctypes.c_uint32),
        ("permitted", ctypes.c_uint32),
        ("inheritable", ctypes.c_uint32),
    ]


class SeccompArgCompare(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_uint),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    ]


def run_mount(*arguments: str) -> None:
    subprocess.run(["/usr/bin/mount", *arguments], check=True)


def run_umount(path: Path, *, check: bool = True) -> bool:
    completed = subprocess.run(["/usr/bin/umount", "-l", str(path)], check=check)
    return completed.returncode == 0


class SocketRelay:
    """Small full-duplex relay between TCP and Unix-domain sockets."""

    def __init__(
        self,
        *,
        listen_family: socket.AddressFamily,
        listen_address: str | tuple[str, int],
        target_family: socket.AddressFamily,
        target_address: str | tuple[str, int],
    ) -> None:
        self.listen_family = listen_family
        self.listen_address = listen_address
        self.target_family = target_family
        self.target_address = target_address
        self.listener: socket.socket | None = None
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.listen_family == socket.AF_UNIX:
            Path(str(self.listen_address)).unlink(missing_ok=True)
        listener = socket.socket(self.listen_family, socket.SOCK_STREAM)
        listener.settimeout(0.25)
        listener.bind(self.listen_address)
        listener.listen(16)
        self.listener = listener
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    @staticmethod
    def _pump(source: socket.socket, destination: socket.socket) -> None:
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                destination.sendall(data)
        except OSError:
            pass
        finally:
            try:
                destination.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def _handle(self, incoming: socket.socket) -> None:
        try:
            outgoing = socket.socket(self.target_family, socket.SOCK_STREAM)
            outgoing.connect(self.target_address)
        except OSError:
            incoming.close()
            return
        with incoming, outgoing:
            forward = threading.Thread(
                target=self._pump, args=(incoming, outgoing), daemon=True
            )
            reverse = threading.Thread(
                target=self._pump, args=(outgoing, incoming), daemon=True
            )
            forward.start()
            reverse.start()
            forward.join()
            reverse.join()

    def _serve(self) -> None:
        assert self.listener is not None
        while not self.stop_event.is_set():
            try:
                incoming, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(incoming,), daemon=True).start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.listener is not None:
            self.listener.close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        if self.listen_family == socket.AF_UNIX:
            Path(str(self.listen_address)).unlink(missing_ok=True)


def _checked_prctl(option: int, argument: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, argument, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def drop_all_capabilities() -> None:
    """Prevent the actor from removing mounts or regaining namespace powers."""
    libc = ctypes.CDLL(None, use_errno=True)
    for capability in range(64):
        if libc.prctl(PR_CAPBSET_DROP, capability, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            if error != errno.EINVAL:
                raise OSError(error, os.strerror(error))
    securebits = (
        SECBIT_NOROOT
        | SECBIT_NOROOT_LOCKED
        | SECBIT_NO_SETUID_FIXUP
        | SECBIT_NO_SETUID_FIXUP_LOCKED
    )
    _checked_prctl(PR_SET_SECUREBITS, securebits)
    header = CapabilityHeader(LINUX_CAPABILITY_VERSION_3, 0)
    data = (CapabilityData * 2)()
    if libc.capset(ctypes.byref(header), ctypes.byref(data)) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    _checked_prctl(PR_SET_NO_NEW_PRIVS, 1)


def install_actor_seccomp() -> None:
    """Deny mount/namespace escape while retaining ordinary build syscalls."""
    library = ctypes.util.find_library("seccomp")
    if not library:
        raise RuntimeError("libseccomp is required for actor confinement")
    seccomp = ctypes.CDLL(library, use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add_array.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.POINTER(SeccompArgCompare),
    ]
    seccomp.seccomp_rule_add_array.restype = ctypes.c_int
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_load.restype = ctypes.c_int

    context = seccomp.seccomp_init(SCMP_ACT_ALLOW)
    if not context:
        raise RuntimeError("seccomp_init failed")
    deny = SCMP_ACT_ERRNO | errno.EPERM
    unavailable = SCMP_ACT_ERRNO | errno.ENOSYS
    try:
        for name in FORBIDDEN_ACTOR_SYSCALLS:
            number = seccomp.seccomp_syscall_resolve_name(name.encode("ascii"))
            if number < 0:
                continue
            result = seccomp.seccomp_rule_add_array(context, deny, number, 0, None)
            if result != 0:
                raise OSError(-result, f"seccomp rule failed for {name}")

        clone = seccomp.seccomp_syscall_resolve_name(b"clone")
        if clone >= 0:
            for flag in CLONE_NAMESPACE_FLAGS:
                comparison = SeccompArgCompare(0, SCMP_CMP_MASKED_EQ, flag, flag)
                result = seccomp.seccomp_rule_add_array(
                    context, deny, clone, 1, ctypes.byref(comparison)
                )
                if result != 0:
                    raise OSError(-result, "seccomp clone namespace rule failed")

        clone3 = seccomp.seccomp_syscall_resolve_name(b"clone3")
        if clone3 >= 0:
            result = seccomp.seccomp_rule_add_array(
                context, unavailable, clone3, 0, None
            )
            if result != 0:
                raise OSError(-result, "seccomp clone3 rule failed")
        result = seccomp.seccomp_load(context)
        if result != 0:
            raise OSError(-result, "seccomp_load failed")
    finally:
        seccomp.seccomp_release(context)


def remove_empty_stage(stage: Path, paths: tuple[Path, ...]) -> None:
    """Remove placeholders only; never recurse through a leaked bind mount."""
    for path in reversed(paths):
        try:
            path.rmdir() if path.is_dir() else path.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        stage.rmdir()
    except OSError:
        pass


def bind(source: Path, destination: Path, *, read_only: bool = False) -> None:
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.touch(exist_ok=True)
    run_mount("--bind", str(source), str(destination))
    if read_only:
        run_mount("-o", "remount,bind,ro", str(destination))


def strict_child(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    parent = root.resolve()
    if resolved == parent or parent not in resolved.parents:
        raise ValueError(f"{label} must be a strict child of {parent}: {resolved}")
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--codex-bin", type=Path)
    parser.add_argument("--code-mode-host", type=Path)
    parser.add_argument("--verus-root", type=Path)
    parser.add_argument("--rust-root", type=Path)
    parser.add_argument("--lynette-bin", type=Path)
    parser.add_argument("--bridge-port", type=int, required=True)
    parser.add_argument("--bridge-socket", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH_ROOT)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("an actor command is required after --")
    if args.network_child:
        if args.bridge_socket is None:
            parser.error("--network-child requires --bridge-socket")
    elif any(
        value is None
        for value in (args.codex_bin, args.verus_root, args.rust_root, args.lynette_bin)
    ):
        parser.error("the outer isolation mode requires all tool paths")
    return args


def run_network_child(args: argparse.Namespace) -> int:
    """Run Codex with private PID/network views and one bridge-only relay."""
    subprocess.run(
        [str(IP_BIN), "link", "set", "lo", "up"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    relay = SocketRelay(
        listen_family=socket.AF_INET,
        listen_address=("127.0.0.1", args.bridge_port),
        target_family=socket.AF_UNIX,
        target_address=str(args.bridge_socket),
    )
    relay.start()
    try:
        drop_all_capabilities()
        install_actor_seccomp()
        completed = subprocess.run(args.command, cwd=args.workspace, check=False)
        return completed.returncode
    finally:
        relay.stop()


def main() -> int:
    args = parse_args()
    if args.network_child:
        return run_network_child(args)
    scratch_root = args.scratch_root.resolve()
    if scratch_root == Path("/"):
        raise ValueError("scratch root must not be the filesystem root")
    workspace = strict_child(args.workspace, scratch_root, "workspace")
    verus_root = strict_child(args.verus_root, scratch_root, "verus root")
    rust_root = strict_child(args.rust_root, scratch_root, "rust root")
    lynette_bin = strict_child(args.lynette_bin, scratch_root, "lynette")
    codex_bin = args.codex_bin.resolve()
    code_mode_host = (
        args.code_mode_host.resolve() if args.code_mode_host is not None else None
    )

    if not workspace.is_dir():
        raise ValueError(f"workspace is not a directory: {workspace}")
    if not verus_root.is_dir() or not rust_root.is_dir():
        raise ValueError("Verus and Rust roots must be directories")
    if not lynette_bin.is_file() or not codex_bin.is_file():
        raise ValueError("Lynette and Codex must be files")
    if code_mode_host is not None and (
        not code_mode_host.is_file() or not os.access(code_mode_host, os.X_OK)
    ):
        raise ValueError(f"Codex Code Mode host is invalid: {code_mode_host}")
    if Path(args.command[0]).resolve() != codex_bin:
        raise ValueError("actor command executable does not match --codex-bin")

    run_mount("--make-rprivate", "/")
    stage = Path(tempfile.mkdtemp(prefix="codex-actor-isolation-", dir="/tmp"))
    staged = {
        "workspace": stage / "workspace",
        "verus": stage / "verus",
        "rust": stage / "rust",
        "lynette": stage / "lynette",
        "codex": stage / "codex",
        "code_mode_host": stage / "codex-code-mode-host",
        "isolation_runner": stage / "actor_isolation.py",
    }
    staged_mounts: list[Path] = []
    try:
        for source, destination in (
            (workspace, staged["workspace"]),
            (verus_root, staged["verus"]),
            (rust_root, staged["rust"]),
            (lynette_bin, staged["lynette"]),
            (codex_bin, staged["codex"]),
            (Path(__file__).resolve(), staged["isolation_runner"]),
        ):
            bind(source, destination)
            staged_mounts.append(destination)
        if code_mode_host is not None:
            bind(code_mode_host, staged["code_mode_host"])
            staged_mounts.append(staged["code_mode_host"])

        os.chdir("/")
        run_mount("-t", "tmpfs", "-o", "size=64m,mode=755", "tmpfs", str(scratch_root))
        run_mount("-t", "tmpfs", "-o", "size=64m,mode=755", "tmpfs", "/home")

        bind(staged["workspace"], workspace)
        bind(staged["verus"], verus_root, read_only=True)
        bind(staged["rust"], rust_root, read_only=True)
        bind(staged["lynette"], lynette_bin, read_only=True)
        isolated_codex = workspace / ".actor_codex"
        bind(staged["codex"], isolated_codex, read_only=True)
        if code_mode_host is not None:
            isolated_code_mode_host = workspace / "codex-code-mode-host"
            bind(
                staged["code_mode_host"], isolated_code_mode_host, read_only=True
            )
        isolated_runner = workspace / ".actor_isolation.py"
        bind(staged["isolation_runner"], isolated_runner, read_only=True)

        actor_home = Path(os.environ.get("HOME", "/home/codex"))
        if actor_home == Path("/home") or Path("/home") not in actor_home.parents:
            raise ValueError(f"actor HOME must be below /home: {actor_home}")
        (actor_home / ".codex").mkdir(parents=True, exist_ok=True)

        for path in reversed(staged_mounts):
            run_umount(path)
        staged_mounts.clear()
        remove_empty_stage(stage, tuple(staged.values()))
        run_mount("-t", "tmpfs", "-o", "size=512m,mode=1777", "tmpfs", "/tmp")

        forbidden = (Path(__file__).resolve().parents[2],)
        visible = [str(path) for path in forbidden if path.exists()]
        if visible:
            raise RuntimeError(f"actor isolation leaked forbidden paths: {visible}")

        command = list(args.command)
        command[0] = str(isolated_codex)
        bridge_socket = Path("/tmp/.actor_bridge.sock")
        outer_relay = SocketRelay(
            listen_family=socket.AF_UNIX,
            listen_address=str(bridge_socket),
            target_family=socket.AF_INET,
            target_address=("127.0.0.1", args.bridge_port),
        )
        outer_relay.start()
        try:
            child = [
                str(UNSHARE_BIN),
                "--net",
                "--pid",
                "--fork",
                "--mount-proc",
                "--kill-child=SIGKILL",
                sys.executable,
                str(isolated_runner),
                "--network-child",
                "--workspace",
                str(workspace),
                "--bridge-port",
                str(args.bridge_port),
                "--bridge-socket",
                str(bridge_socket),
                "--",
                *command,
            ]
            return subprocess.run(child, cwd=workspace, check=False).returncode
        finally:
            outer_relay.stop()
    finally:
        for path in reversed(staged_mounts):
            run_umount(path, check=False)
        remove_empty_stage(stage, tuple(staged.values()))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
