"""A read-only prerequisite check; never calls a model or starts a guest VM."""

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import solver
from inspect_ai.util import sandbox


PROBE = r'''
import fcntl, json, os, platform, shutil, socket, urllib.request, urllib.error
report = {
    "architecture": platform.machine(),
    "kernel": platform.release(),
    "kvm_device_present": os.path.exists("/dev/kvm"),
    "kvm_usable": False,
    "docker_socket_present": os.path.exists("/var/run/docker.sock"),
    "binaries": {name: shutil.which(name) for name in
                 ["qemu-system-x86_64", "qemu-img", "docker", "Xvfb", "chromium"]},
    "network": {},
}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = urllib.request.build_opener(NoRedirect())
if report["kvm_device_present"]:
    try:
        fd = os.open("/dev/kvm", os.O_RDWR | os.O_CLOEXEC)
        try:
            report["kvm_api_version"] = fcntl.ioctl(fd, 0xAE00, 0)
            report["kvm_usable"] = report["kvm_api_version"] == 12
        finally:
            os.close(fd)
    except OSError as exc:
        report["kvm_error"] = str(exc)
for host in ["accounts.google.com", "drive.google.com", "docs.google.com"]:
    item = {}
    try:
        socket.getaddrinfo(host, 443)
        item["dns"] = True
    except OSError as exc:
        item["dns"] = False
        item["dns_error"] = str(exc)
    try:
        # A public HEAD request only; no login, credentials or Drive fixtures.
        request = urllib.request.Request("https://" + host + "/", method="HEAD")
        with opener.open(request, timeout=5) as response:
            item["https_status"] = response.status
    except urllib.error.HTTPError as exc:
        item["https_status"] = exc.code
    except Exception as exc:
        item["https_error"] = str(exc)
    report["network"][host] = item
print(json.dumps(report, sort_keys=True))
'''


@solver
def probe_solver():
    async def solve(state, generate):
        result = await sandbox().exec(["python", "-c", PROBE], timeout=30)
        state.metadata["infrastructure_probe"] = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        print("ROGUE_INFRASTRUCTURE_PROBE", result.stdout, flush=True)
        if result.returncode:
            raise RuntimeError("Infrastructure probe failed: " + result.stderr)
        state.completed = True
        return state
    return solve


@task
def infrastructure_probe():
    return Task(
        dataset=[Sample(id="prerequisites", input="Read-only infrastructure check")],
        solver=probe_solver(),
        sandbox=("k8s", str(Path(__file__).with_name("probe-values.yaml"))),
        time_limit=45,
    )
