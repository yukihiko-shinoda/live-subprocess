# Live Subprocess

[![Test](https://github.com/yukihiko-shinoda/live-subprocess/workflows/Test/badge.svg)](https://github.com/yukihiko-shinoda/live-subprocess/actions?query=workflow%3ATest)
[![CodeQL](https://github.com/yukihiko-shinoda/live-subprocess/workflows/CodeQL/badge.svg)](https://github.com/yukihiko-shinoda/live-subprocess/actions?query=workflow%3ACodeQL)
[![Code Coverage](https://qlty.sh/gh/yukihiko-shinoda/projects/live-subprocess/coverage.svg)](https://qlty.sh/gh/yukihiko-shinoda/projects/live-subprocess)
[![Maintainability](https://qlty.sh/gh/yukihiko-shinoda/projects/live-subprocess/maintainability.svg)](https://qlty.sh/gh/yukihiko-shinoda/projects/live-subprocess)
[![Dependabot](https://flat.badgen.net/github/dependabot/yukihiko-shinoda/live-subprocess?icon=dependabot)](https://github.com/yukihiko-shinoda/live-subprocess/security/dependabot)
[![Python versions](https://img.shields.io/pypi/pyversions/livesubprocess)](https://pypi.org/project/livesubprocess/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/livesubprocess)](https://pypi.org/project/livesubprocess/)
[![X URL](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Fgithub.com%2Fyukihiko-shinoda%2Flive-subprocess)](https://x.com/intent/post?text=Live%20Subprocess&url=https%3A%2F%2Fpypi.org%2Fproject%2Flivesubprocess%2F&hashtags=python)

Displays the stdout and stderr of the subprocess in real time.

## Advantage

* Displays subprocess stdout and stderr in real time as the process runs — not buffered until exit.
* Uses a PTY (pseudo-terminal) on POSIX so the child process keeps line-buffering active, just as it would in a real terminal.
* Cross-platform: PTY-based on POSIX, thread-backed pipe reader on Windows.
* Zero runtime dependencies.
* Async/await native; captures and returns the full output string for programmatic use.

## Quickstart

Install:

```shell
pip install livesubprocess
```

Run a command with real-time output (POSIX):

```python
import asyncio
from livesubprocess import LiveSubProcessFactory

async def main() -> None:
    pty = LiveSubProcessFactory.create_pty()
    stdout, returncode = await pty.run(["python", "-u", "script.py"])

asyncio.run(main())
```

Run a command with real-time output (POSIX and Windows):

```python
import asyncio
import subprocess
from livesubprocess import LiveSubProcessFactory

async def main() -> None:
    proc = subprocess.Popen(
        ["python", "-u", "script.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    live = LiveSubProcessFactory.create_popen(proc)
    stdout, returncode = await live.wait()

asyncio.run(main())
```

## PTY vs. Popen

| | PTY (`create_pty`) | Popen (`create_popen`) |
|---|---|---|
| **Platforms** | POSIX only | POSIX and Windows |
| **Process creation** | Managed by `livesubprocess` | You create the `Popen` object |
| **Line-buffering** | Yes — child sees a real TTY | Depends on the child process |
| **Use when** | Simplest API on POSIX | Windows support needed, or you need to configure `Popen` directly (env, cwd, shell, etc.) |

Both `run()` and `wait()` return `(stdout_and_stderr: str, returncode: int)`.

<!-- markdownlint-disable no-trailing-punctuation -->
## How do I...
<!-- markdownlint-enable no-trailing-punctuation -->

* **Wrap an existing `subprocess.Popen`?** Use `LiveSubProcessFactory.create_popen()`. This works on both POSIX and Windows.

  ```python
  import asyncio
  import subprocess
  from livesubprocess import LiveSubProcessFactory

  async def main() -> None:
      proc = subprocess.Popen(
          ["ffmpeg", "-i", "input.mp4", "output.mp4"],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
      live = LiveSubProcessFactory.create_popen(proc)
      stdout, returncode = await live.wait()

  asyncio.run(main())
  ```

* **Stop the reader early (before terminating the process)?** Call `live.stop()` before `popen.terminate()` or `popen.communicate()` to deregister the fd readers cleanly.

## Credits

This package was created with [Cookiecutter] and the [yukihiko-shinoda/cookiecutter-pypackage] project template.

[Cookiecutter]: https://github.com/audreyr/cookiecutter
[yukihiko-shinoda/cookiecutter-pypackage]: https://github.com/audreyr/cookiecutter-pypackage
