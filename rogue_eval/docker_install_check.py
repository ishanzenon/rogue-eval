"""Executed only inside the disposable Hawk sandbox, never on the user's PC."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time


def command(args, timeout=30, env=None):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
        return {"exit_code": p.returncode, "stdout": p.stdout[-3500:], "stderr": p.stderr[-5000:]}
    except subprocess.TimeoutExpired:
        return {"timeout_seconds": timeout}


def daemon_test(name, extra, test_container=False):
    root = Path('/tmp/rogue-docker-' + name)
    root.mkdir()
    socket = 'unix://' + str(root / 'docker.sock')
    args = ['dockerd', '--data-root=' + str(root / 'data'),
            '--exec-root=' + str(root / 'exec'), '--pidfile=' + str(root / 'pid'),
            '--host=' + socket] + extra
    result = {}
    with (root / 'daemon.log').open('w') as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline and process.poll() is None:
                if (root / 'docker.sock').exists():
                    status = command(['docker', '--host=' + socket, 'info', '--format', '{{.ServerVersion}}'], timeout=3)
                    if status.get('exit_code') == 0:
                        result['daemon_ready'] = True
                        result['server_version'] = status['stdout'].strip()
                        break
                time.sleep(1)
            result.setdefault('daemon_ready', False)
            if result['daemon_ready'] and test_container:
                # A local static binary avoids registry downloads and network
                # ambiguity when testing the ability to create a container.
                archive = root / 'rootfs.tar'
                with tarfile.open(archive, 'w') as tar:
                    tar.add('/bin/busybox', arcname='bin/busybox')
                image = 'rogue-smoke:local'
                result['import_local_rootfs'] = command(['docker', '--host=' + socket, 'import', str(archive), image])
                if result['import_local_rootfs'].get('exit_code') == 0:
                    result['run_minimal_container'] = command(['docker', '--host=' + socket, 'run', '--rm', '--network=none', '--cap-drop=ALL', image, '/bin/busybox', 'echo', 'ROGUE_DOCKER_OK'])
                    result['run_with_rogue_capability'] = command(['docker', '--host=' + socket, 'run', '--rm', '--network=none', '--cap-add=NET_ADMIN', image, '/bin/busybox', 'echo', 'ROGUE_NET_ADMIN_OK'])
            result['daemon_exit_code_before_cleanup'] = process.poll()
        finally:
            if process.poll() is None:
                import signal
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
    result['daemon_log_tail'] = (root / 'daemon.log').read_text(errors='replace')[-7000:]
    return result


def main():
    report = {'uid': os.getuid(), 'kvm_present': Path('/dev/kvm').exists()}
    report['apt_update'] = command(['apt-get', 'update', '-o', 'Acquire::Retries=0', '-o', 'Acquire::http::Timeout=15'], timeout=70)
    if report['apt_update'].get('exit_code') != 0:
        print('ROGUE_DOCKER_INSTALL_RESULT ' + json.dumps(report), flush=True)
        return
    environment = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
    report['apt_install'] = command(['apt-get', 'install', '-y', '--no-install-recommends', 'docker.io', 'busybox-static', 'uidmap', 'rootlesskit', 'slirp4netns', 'util-linux'], timeout=180, env=environment)
    if report['apt_install'].get('exit_code') == 0:
        report['docker_client'] = command(['docker', '--version'])
        report['dockerd_binary'] = command(['dockerd', '--version'])
        report['normal_daemon'] = daemon_test('normal', [])
        # A diagnostic fallback only: it intentionally removes bridge/iptables
        # requirements and does not claim to satisfy ROGUE networking.
        report['minimal_daemon'] = daemon_test('minimal', [
            '--storage-driver=vfs', '--iptables=false', '--ip6tables=false',
            '--bridge=none', '--ip-forward=false', '--ip-masq=false'], test_container=True)
        report['create_rootless_user'] = command(['useradd', '--create-home', '--shell', '/bin/sh', 'rogueprobe'])
        report['rootless_user_namespace'] = command(['runuser', '-u', 'rogueprobe', '--', 'unshare', '--user', '--map-root-user', '/bin/true'])
        report['rootless_launchers'] = {n: shutil.which(n) for n in ['rootlesskit', 'dockerd-rootless.sh', 'newuidmap', 'newgidmap']}
    print('ROGUE_DOCKER_INSTALL_RESULT ' + json.dumps(report, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
