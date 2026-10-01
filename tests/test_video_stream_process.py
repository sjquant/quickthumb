"""Failure and process-ownership contracts for streaming video input."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from io import BytesIO
from pathlib import Path

import pytest
import quickthumb._export_video as video
from quickthumb.errors import RenderingError


class _InputPipe:
    def __init__(self, events, *, write_error=None, close_error=None):
        self.events = events
        self.write_error = write_error
        self.close_error = close_error
        self.data = bytearray()
        self.closed = False

    def write(self, data):
        self.events.append("stdin.write")
        if self.write_error is not None:
            raise self.write_error
        self.data.extend(data)
        return len(data)

    def close(self):
        self.events.append("stdin.close")
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class _ErrorPipe(BytesIO):
    def __init__(self, events, data):
        super().__init__(data)
        self.events = events
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)

    def close(self):
        self.events.append("stderr.close")
        super().close()


class _Process:
    def __init__(
        self,
        *,
        exit_code=0,
        write_error=None,
        close_error=None,
        wait_error=None,
        stderr=b"",
    ):
        self.events = []
        self.stdin = _InputPipe(self.events, write_error=write_error, close_error=close_error)
        self.stderr = _ErrorPipe(self.events, stderr)
        self.exit_code = exit_code
        self.wait_error = wait_error
        self.returncode = None

    def wait(self, timeout=None):
        self.events.append(("wait", timeout))
        if self.wait_error is not None:
            error, self.wait_error = self.wait_error, None
            raise error
        self.returncode = self.exit_code
        return self.returncode

    def kill(self):
        self.events.append("kill")


@pytest.fixture
def install_process(monkeypatch):
    def install(process, *, start_error=None, constructor_error=None):
        def popen(command, **kwargs):
            process.events.append("Popen")
            assert kwargs == {
                "stdin": subprocess.PIPE,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.PIPE,
            }
            return process

        class Reader:
            def __init__(self, *, target, name):
                if constructor_error is not None:
                    raise constructor_error
                self.ident = None
                self.target = target

            def start(self):
                process.events.append("reader.start")
                if start_error is not None:
                    raise start_error
                self.ident = 1
                self.target()

            def join(self):
                process.events.append("reader.join")

        monkeypatch.setattr(video.subprocess, "Popen", popen)
        monkeypatch.setattr(video.threading, "Thread", Reader)
        return process

    return install


def _partial_output(tmp_path):
    output = tmp_path / "segment.mp4"
    output.write_bytes(b"partial segment")
    return output


def _stream(frames, output):
    video._stream_video_ffmpeg(["fake-ffmpeg", str(output)], frames, "mp4", str(output))


def _assert_reaped_before_close(process):
    events = process.events
    assert events.index("kill") < events.index(("wait", None)) < events.index("stdin.close")
    assert process.returncode is not None
    assert process.stdin.closed
    assert process.stderr.closed


def test_stream_success_closes_input_before_waiting_and_joins_reader(install_process, tmp_path):
    process = install_process(_Process())
    output = _partial_output(tmp_path)

    _stream(iter([b"first", b"second"]), output)

    assert process.stdin.data == b"firstsecond"
    assert process.events.index("stdin.close") < process.events.index(("wait", None))
    assert process.events.index(("wait", None)) < process.events.index("reader.join")
    assert process.events.index("reader.join") < process.events.index("stderr.close")
    assert "kill" not in process.events
    assert process.returncode == 0
    assert output.exists()


@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt, BrokenPipeError])
def test_producer_failure_reaps_before_close_and_preserves_original(
    install_process, tmp_path, error_type
):
    error = error_type("producer failed")
    process = install_process(_Process(close_error=BrokenPipeError("cleanup failed")))
    output = _partial_output(tmp_path)

    def frames():
        yield b"first"
        raise error

    with pytest.raises(error_type) as caught:
        _stream(frames(), output)

    assert caught.value is error
    _assert_reaped_before_close(process)
    assert "reader.join" in process.events
    assert not output.exists()


def test_reader_start_failure_reaps_process_without_joining(install_process, tmp_path):
    error = RuntimeError("cannot start reader")
    process = install_process(_Process(), start_error=error)
    output = _partial_output(tmp_path)

    with pytest.raises(RuntimeError) as caught:
        _stream([b"frame"], output)

    assert caught.value is error
    _assert_reaped_before_close(process)
    assert "reader.join" not in process.events
    assert "stdin.write" not in process.events
    assert not output.exists()


def test_reader_construction_failure_reaps_process(install_process, tmp_path):
    error = RuntimeError("cannot construct reader")
    process = install_process(_Process(), constructor_error=error)
    output = _partial_output(tmp_path)

    with pytest.raises(RuntimeError) as caught:
        _stream([b"frame"], output)

    assert caught.value is error
    _assert_reaped_before_close(process)
    assert "reader.start" not in process.events
    assert not output.exists()


@pytest.mark.parametrize("failure_stage", ["write", "close"])
@pytest.mark.parametrize("exit_code", [0, 7])
def test_pipe_failure_is_an_error_even_when_process_exits_zero(
    install_process, tmp_path, failure_stage, exit_code
):
    pipe_error = BrokenPipeError("encoder closed input")
    options = {f"{failure_stage}_error": pipe_error}
    process = install_process(
        _Process(exit_code=exit_code, stderr=b"encoder diagnostic", **options)
    )
    output = _partial_output(tmp_path)

    with pytest.raises(RenderingError, match="ffmpeg failed.*") as caught:
        _stream([b"first", b"second"], output)

    assert caught.value.__cause__ is pipe_error
    assert "encoder diagnostic" in str(caught.value)
    assert process.returncode == exit_code
    assert process.stdin.closed
    assert process.stderr.closed
    assert "reader.join" in process.events
    assert not output.exists()


def test_unresponsive_process_is_killed_after_pipe_failure(install_process, tmp_path):
    process = install_process(
        _Process(
            write_error=BrokenPipeError("closed input"),
            wait_error=subprocess.TimeoutExpired("fake-ffmpeg", 2),
        )
    )
    output = _partial_output(tmp_path)

    with pytest.raises(RenderingError, match="ffmpeg failed"):
        _stream([b"frame"], output)

    assert process.events.index(("wait", 2)) < process.events.index("kill")
    assert process.events.index("kill") < process.events.index(("wait", None))
    assert process.returncode is not None
    assert process.stderr.closed
    assert not output.exists()


def test_interrupt_during_wait_reaps_process_and_preserves_interrupt(install_process, tmp_path):
    error = KeyboardInterrupt("interrupted wait")
    process = install_process(_Process(wait_error=error))
    output = _partial_output(tmp_path)

    with pytest.raises(KeyboardInterrupt) as caught:
        _stream([b"frame"], output)

    assert caught.value is error
    assert process.events.count(("wait", None)) == 2
    assert "kill" in process.events
    assert process.returncode is not None
    assert process.stderr.closed
    assert not output.exists()


def test_nonzero_exit_keeps_only_bounded_diagnostic_tail(install_process, tmp_path):
    diagnostic = b"discarded-prefix" + b"x" * 20000 + b"\xfffinal-diagnostic"
    process = install_process(_Process(exit_code=7, stderr=diagnostic))
    output = _partial_output(tmp_path)

    with pytest.raises(RenderingError) as caught:
        _stream([b"frame"], output)

    detail = str(caught.value).split(":\n", 1)[1]
    assert detail == diagnostic[-2000:].decode("utf-8", errors="replace")
    assert all(0 < size <= 8192 for size in process.stderr.read_sizes)
    assert process.returncode == 7
    assert process.stderr.closed
    assert not output.exists()


def test_popen_failure_removes_partial_output_with_install_guidance(tmp_path):
    output = _partial_output(tmp_path)

    with pytest.raises(RenderingError, match="could not start ffmpeg") as caught:
        video._stream_video_ffmpeg(
            [str(tmp_path / "missing-ffmpeg")], [b"frame"], "mp4", str(output)
        )

    assert isinstance(caught.value.__cause__, OSError)
    assert "QUICKTHUMB_FFMPEG" in str(caught.value)
    assert not output.exists()


def test_real_subprocess_drains_newline_free_stderr_flood_and_reaps(tmp_path):
    """An outer timeout turns a pipe-drain deadlock into a bounded test failure."""
    output = tmp_path / "partial.mp4"
    child = textwrap.dedent(
        r"""
        import sys
        from pathlib import Path
        Path(sys.argv[1]).write_bytes(b'partial')
        sys.stderr.buffer.write(
            b'discarded-prefix' + b'x' * (256 * 1024) + b'\xfffinal-diagnostic'
        )
        sys.stderr.buffer.flush()
        sys.stdin.buffer.read()
        sys.exit(7)
        """
    )
    script = textwrap.dedent(
        r"""
        import subprocess
        import sys
        from pathlib import Path
        import quickthumb._export_video as video
        from quickthumb.errors import RenderingError

        output = Path(sys.argv[1])
        original_popen = subprocess.Popen
        processes = []
        def record_popen(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            processes.append(process)
            return process
        video.subprocess.Popen = record_popen
        child = sys.argv[2]
        try:
            video._stream_video_ffmpeg(
                [sys.executable, '-c', child, str(output)],
                (b'frame' * 20000 for _ in range(4)),
                'mp4', str(output),
            )
        except RenderingError as error:
            detail = str(error).split(':\n', 1)[1]
            assert detail.endswith('\ufffdfinal-diagnostic'), repr(detail[-40:])
            assert len(detail) <= 2000
            assert 'discarded-prefix' not in detail
        else:
            raise AssertionError('nonzero encoder exit was accepted')
        assert len(processes) == 1
        assert processes[0].returncode == 7
        assert processes[0].stdin.closed
        assert processes[0].stderr.closed
        assert not output.exists()
        """
    )

    subprocess.run(
        [sys.executable, "-c", script, str(output), child],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert not output.exists()


@pytest.mark.parametrize("error_name", ["RuntimeError", "KeyboardInterrupt"])
def test_real_producer_failure_kills_and_reaps_encoder(tmp_path, error_name):
    """The child is already consuming input when the producer aborts."""
    output = tmp_path / "partial.mp4"
    child = textwrap.dedent(
        """
        import sys
        from pathlib import Path
        Path(sys.argv[1]).write_bytes(b'partial')
        sys.stdin.buffer.read()
        """
    )
    script = textwrap.dedent(
        """
        import builtins
        import subprocess
        import sys
        from pathlib import Path
        import quickthumb._export_video as video

        output = Path(sys.argv[1])
        original_popen = subprocess.Popen
        processes = []
        def record_popen(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            processes.append(process)
            return process
        video.subprocess.Popen = record_popen
        error_type = getattr(builtins, sys.argv[3])
        original_error = error_type('producer failed')
        def frames():
            yield b'x' * (1024 * 1024)
            raise original_error
        try:
            video._stream_video_ffmpeg(
                [sys.executable, '-c', sys.argv[2], str(output)],
                frames(), 'mp4', str(output),
            )
        except error_type as error:
            assert error is original_error
        else:
            raise AssertionError('producer failure was swallowed')
        assert len(processes) == 1
        assert processes[0].returncode is not None
        assert processes[0].returncode != 0
        assert processes[0].stdin.closed
        assert processes[0].stderr.closed
        assert not output.exists()
        """
    )

    subprocess.run(
        [sys.executable, "-c", script, str(output), child, error_name],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert not output.exists()
