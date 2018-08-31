from mimetypes import guess_type
from ocrd import MIMETYPE_PAGE
from ocrd import Processor
from ocrd.model.ocrd_page import to_xml
from ocrd.model.ocrd_page_generateds import parseString
from ocrd.utils import getLogger
from ocrd_cis import get_file_id
from ocrd_cis import get_file_group_id
from ocrd_cis import get_ocrd_tool
from ocrd_tesserocr import TesserocrRecognize
from pathlib import Path
from zipfile import ZipFile
import os
import re
import shutil
import urllib.parse
import urllib.request

# from ocrd.model.ocrd_page import to_xml
# from ocrd.model.ocrd_page_generateds import parse


class OCR(Processor):
    def __init__(self, *args, **kwargs):
        ocrd_tool = get_ocrd_tool()
        kwargs['ocrd_tool'] = ocrd_tool['tools']['ocrd-cis-ocr']
        kwargs['version'] = ocrd_tool['version']
        super(OCR, self).__init__(*args, **kwargs)
        self.log = getLogger('cis.Processor.OCR')
        self.cache_dir = self.parameter['cacheDir']
        self.setup_cache_dir()
        self.log.debug("using tmp dir: {}".format(self.cache_dir))

    def process(self):
        for zip in self.download_all_archives():
            self.ocr(zip)

    def ocr(self, zip):
        self.log.info("ocring {}".format(zip))
        self.add_triples_to_workspace(zip)
        for ocr in self.parameter['ocrs']:
            for model in ocr['models']:
                self.recognize(zip, ocr['engine'], model)

    def recognize(self, zip, engine, model):
        """Recognize a set of empty SEG files
        with the given OCR-engine and model"""
        # at this point only works for tesseract
        if engine not in ['tesseract']:
            raise Exception('invalid OCR-engine: {}'.format(engine))

        self.workspace.save_mets()
        grpid = self.get_ids_from_zip(0, zip, _type="SEG")[0]
        self.log.debug("recognizing file group: {}".format(grpid))
        ocrgrpid = grpid.replace(
            'CIS', 'TESSERACT-'+model.replace('_', '-')
        ).replace('-SEG', '')
        self.log.debug("output file group: {}".format(ocrgrpid))
        tess = TesserocrRecognize(
            workspace=self.workspace,
            parameter=self.parameter,
            input_file_grp=grpid,
            output_file_grp=ocrgrpid,
            group_id=None,
        )
        self.log.debug("input_files: {}".format(tess.input_files))
        tess.parameter['model'] = model
        tess.parameter['textequiv_level'] = 'glyph'
        tess.process()

    def add_triples_to_workspace(self, zip):
        imgs = list()
        xmls = list()
        with ZipFile(zip, 'r') as ar:
            for f in ar.namelist():
                if f.endswith('.xml') and os.path.dirname(f).endswith("page"):
                    xmls.append(f)
                elif os.path.splitext(f)[1] in [
                        '.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                    imgs.append(f)
            if len(imgs) != len(xmls):
                raise Exception("invalid archive contents: {} and {}"
                                .format(imgs, xmls))
            imgs.sort()
            xmls.sort()
            for i in range(len(imgs)):
                self.add_triple_to_workspace(
                    ar, i+1, zip, imgs[i], xmls[i])

    def add_triple_to_workspace(self, ar, _id, zip, img, xml):
        # image
        grp, idstr = self.get_ids_from_zip(_id, zip, _type="IMG")
        self.log.debug("adding {}".format(img))
        imgfilepath = ""
        with ar.open(img) as stream:
            imgfilepath = self.workspace.add_file(
                ID=idstr,
                mimetype=guess_type(img)[0],
                content=stream.read(),
                basename=os.path.basename(img),
                file_grp=grp,
            )

        # ground truth
        grp, idstr = self.get_ids_from_zip(_id, zip)
        self.log.debug("adding {}".format(xml))
        with ar.open(xml) as stream:
            # update image file name in raw buffer
            content = stream.read()
            content = re.sub(
                b'imageFilename\\s*=\\s*"[^"]*"',
                b'imageFilename="' + bytes(imgfilepath.url, 'utf-8') + b'"',
                content
            )
            self.workspace.add_file(
                ID=idstr,
                mimetype=MIMETYPE_PAGE,
                content=content,
                basename=os.path.basename(xml),
                file_grp=grp,
            )

            # segments (parse xml and remove all TextEquivs)
            grp, idstr = self.get_ids_from_zip(_id, zip, _type="SEG")
            pcgts = parseString(content, silence=True)
            for region in pcgts.get_Page().get_TextRegion():
                region.TextEquiv = []
                for line in region.get_TextLine():
                    line.TextEquiv = []
                    for word in line.get_Word():
                        word.TextEquiv = []
                        for glyph in word.get_Glyph():
                            glyph.TextEquiv = []
            self.workspace.add_file(
                ID=idstr,
                mimetype=MIMETYPE_PAGE,
                content=to_xml(pcgts),
                basename=os.path.basename(xml),
                file_grp=grp,
            )

    def get_ids_from_zip(self, _id, zip, _type="GT"):
        """Return a pair of the group and file id for a given zip archive"""
        suffix = os.path.splitext(os.path.basename(zip))[0]
        if _type == "IMG":
            return (get_file_group_id("IMG", suffix=suffix),
                    get_file_id(_id, "IMG", suffix=suffix))
        elif _type == "SEG":
            return (get_file_group_id("SEG", suffix=suffix),
                    get_file_id(_id, "SEG", suffix=suffix))
        return (get_file_group_id("COR", gt=True, suffix=suffix),
                get_file_id(_id, "COR", gt=True, suffix=suffix))

    def download_all_archives(self):
        zips = list()
        for url in self.parameter['urls']:
            zips.append(self.download(url))
        return zips

    def download(self, url):
        self.log.debug("downloading {}". format(url))
        path = self.chached_path(url)
        if Path(path).is_file():
            self.log.debug("using cached archive: {}".format(path))
            return path

        self.log.debug("downloading {} to {}". format(url, path))
        with urllib.request.urlopen(url) as web, open(path, 'wb') as out:
            shutil.copyfileobj(web, out)

    def setup_cache_dir(self):
        try:
            os.makedirs(self.cache_dir)
        except FileExistsError:
            pass  # we do not care if cache dir already exists

    def chached_path(self, url):
        zip = os.path.basename(url)
        return os.path.join(self.cache_dir, zip)
