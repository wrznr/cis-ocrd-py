import json
from ocrd import Processor
from ocrd_cis import get_ocrd_tool
from ocrd.utils import getLogger
from ocrd.model.ocrd_page import from_file
from ocrd_cis import JavaProcess


class Profiler(Processor):
    def __init__(self, *args, **kwargs):
        ocrd_tool = get_ocrd_tool()
        kwargs['ocrd_tool'] = ocrd_tool['tools']['ocrd-cis-profile']
        kwargs['version'] = ocrd_tool['version']
        super(Profiler, self).__init__(*args, **kwargs)
        self.log = getLogger('Processor.Profiler')

    def process(self):
        profile = self.read_profile()
        self.add_output_file(
            mimetype="application/json",
            content=json.dumps(profile),
            basename="profile.json",
        )

    def read_profile(self):
        _input = []
        for (line, pcgts, ifile) in self.get_all_lines():
            _input.append(line.get_TextEquiv()[0].Unicode)
        p = JavaProcess.profiler(
             jar=self.parameter['cisOcrdJar'],
             args=[
                 self.parameter['profilerExecutable'],
                 self.parameter['profilerBackend'],
                 self.parameter['profilerLanguage'],
             ]
        )
        return json.loads(p.run("\n".join(_input)))

    def get_all_lines(self):
        """Returns a list of tuples of lines, their parent and
        their according workspace file."""
        lines = []
        ifs = sorted(
            self.workspace.mets.find_files(fileGrp=self.input_file_grp),
            key=lambda ifile: ifile.ID
        )
        for ifile in ifs:
            pcgts = from_file(
                self.workspace.download_file(ifile)
            )
            for region in pcgts.get_Page().get_TextRegion():
                for line in region.get_TextLine():
                    lines.append((line, pcgts, ifile))
        return lines

    def get_all_words(self):
        words = []
        for (line, pcgts, ifile) in self.get_all_lines():
            for word in line.get_Word():
                words.append((word, pcgts, ifile))
        return words
