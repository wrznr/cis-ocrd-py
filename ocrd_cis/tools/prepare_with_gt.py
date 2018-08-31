from __future__ import absolute_import
from ocrd.model.ocrd_page_generateds import parseString
from ocrd import MIMETYPE_PAGE
from ocrd.model.ocrd_page import to_xml
from mimetypes import guess_type
from ocrd import Processor
from ocrd.utils import getLogger
from ocrd_cis import get_ocrd_tool
from zipfile import ZipFile
from os.path import splitext
from os.path import dirname
from os.path import basename
from ocrd_cis import get_file_id
from ocrd_cis import get_file_group_id
import re


class PrepareWithGT(Processor):
    ZIPS = ()

    def __init__(self, *args, **kwargs):
        ocrd_tool = get_ocrd_tool()
        kwargs['ocrd_tool'] = ocrd_tool['tools']['ocrd-cis-prepare-with-gt']
        kwargs['version'] = ocrd_tool['version']
        super(PrepareWithGT, self).__init__(*args, **kwargs)
        self.log = getLogger('cis.Processor.AddGTToWorkspace')

    def process(self):
        for zip in PrepareWithGT.ZIPS:
            self._process(zip)

    def _process(self, zip):
        self.log.debug("processing: {}".format(zip))
        imgs = list()
        xmls = list()
        with ZipFile(zip, 'r') as ar:
            for f in ar.namelist():
                if f.endswith('.xml') and dirname(f).endswith("page"):
                    xmls.append(f)
                elif splitext(f)[1] in [
                        '.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                    imgs.append(f)
            if len(imgs) != len(xmls):
                raise Exception("invalid archive contents: {} and {}"
                                .format(imgs, xmls))
            imgs.sort()
            xmls.sort()
            for i in range(len(imgs)):
                self._add((imgs[i], xmls[i]), ar, i+1)

    def _add(self, pair, ar, _id):
        self.log.debug("adding: {}".format(pair))
        iid = get_file_id(_id, "IMG")
        ifg = get_file_group_id("IMG")
        gid = get_file_id(_id, "COR", gt=True)
        gfg = get_file_group_id("COR", gt=True)
        sid = get_file_id(_id, "SEG")
        sfg = get_file_group_id("SEG")
        ipath = ''

        # image
        with ar.open(pair[0]) as stream:
            ipath = self.workspace.add_file(
                ID=iid,
                mimetype=guess_type(pair[0])[0],
                basename=basename(pair[0]),
                file_grp=ifg,
                content=stream.read(),
            )

        # gt
        with ar.open(pair[1]) as stream:
            content = stream.read()
            content = re.sub(
                b'imageFilename\\s*=\\s*"[^"]*"',
                b'imageFilename="' + bytes(ipath.url, 'utf-8') + b'"',
                content
            )
            self.workspace.add_file(
                ID=gid,
                file_grp=gfg,
                groupId=iid,
                mimetype=MIMETYPE_PAGE,
                basename=basename(pair[1]),
                content=content,
            )

            # segments (parse xml and remove all TextEquivs)
            pcgts = parseString(content, silence=True)
            self._clear(pcgts)
            self.workspace.add_file(
                ID=sid,
                file_grp=sfg,
                groupId=iid,
                mimetype=MIMETYPE_PAGE,
                basename=basename(pair[1]),
                content=to_xml(pcgts),
            )

    def _clear(self, pcgts):
        for region in pcgts.get_Page().get_TextRegion():
            region.TextEquiv = []
            for line in region.get_TextLine():
                line.Word = []
