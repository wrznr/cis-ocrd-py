import json
import subprocess
from ocrd.utils import getLogger
from pathlib import Path


class ProfilerProcess:
    def __init__(self, exe, backend, language):
        self.exe = exe
        self.config = Path(backend) / Path(language + ".ini")
        self.log = getLogger('ProfilerProcess')
        if not Path(self.exe).is_file():
            raise FileNotFoundError("no such file: {}".format(self.exe))
        if not Path(self.config).is_file():
            raise FileNotFoundError("no such file: {}".format(self.config))

    def run(self, _input):
        """
        Run the profiler with the given input and get its output.
        The process writes _input to stdin of the profiler.
        """
        cmd = self.get_cmd()
        self.log.info('command: %s', cmd)
        with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                # only since 3.6: encoding='utf-8',
                stderr=subprocess.DEVNULL,
        ) as p:
            output, err = p.communicate(input=_input.encode('utf-8'))
            retval = p.wait()
            self.log.info("command: %s, %i", err, retval)
            if retval != 0:
                raise ValueError(
                    "cannot execute {}: {}\nreturned: {}"
                    .format(cmd, err.decode('utf-8') if err else u'', retval))
            output = output.decode('utf-8')
            return output

    def get_cmd(self):
        cmd = [
            self.exe,
            "--sourceFile", "/dev/stdin",
            "--sourceFormat", "TXT",
            "--config", self.config,
            "--jsonOutput", "/dev/stdout",
            "--types",
        ]
        return cmd
