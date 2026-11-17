import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import solver
from inspect_ai.util import sandbox


@solver
def docker_install_solver():
    async def solve(state, generate):
        code = Path(__file__).with_name("docker_install_check.py").read_text()
        result = await sandbox().exec(["python", "-c", code], timeout=360)
        print(result.stdout, flush=True)
        state.metadata["docker_install_exit_code"] = result.returncode
        if result.stderr:
            print("ROGUE_DOCKER_INSTALL_STDERR " + result.stderr[-4000:], flush=True)
        for line in result.stdout.splitlines():
            if line.startswith("ROGUE_DOCKER_INSTALL_RESULT "):
                state.metadata["docker_install_result"] = json.loads(line.split(" ", 1)[1])
        if result.returncode:
            raise RuntimeError("Docker installation check exited with " + str(result.returncode))
        state.completed = True
        return state

    return solve


@task
def docker_install_check():
    return Task(
        dataset=[
            Sample(id="docker-install", input="Install Docker and test daemon/container creation")
        ],
        solver=docker_install_solver(),
        sandbox=("k8s", str(Path(__file__).with_name("docker-install-values.yaml"))),
        time_limit=420,
    )
