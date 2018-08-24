from mimetypes import guess_type
from ocrd import MIMETYPE_PAGE
from ocrd import Processor
# from ocrd.model.ocrd_page import to_xml
# from ocrd.model.ocrd_page_generateds import parse
from ocrd.utils import getLogger
from ocrd_cis import get_file_id
from ocrd_cis import get_group_id
from ocrd_cis import get_ocrd_tool
from pathlib import Path
from zipfile import ZipFile
import os
import shutil
import urllib.parse
import urllib.request


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
        self.write_xml_and_images(zip)


    def write_xml_and_images(self, zip):
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
            suffix = os.path.splitext(os.path.basename(zip))[0]
            for i in range(len(imgs)):
                self.write_xml_and_image_pair(
                    ar, i+1, suffix, imgs[i], xmls[i])

    def write_xml_and_image_pair(self, ar, _id, suffix, img, xml):
        imggrp = get_group_id("IMG", suffix=suffix)
        imgid = get_file_id(_id, "IMG", suffix=suffix)
        self.log.debug("writing {}".format(img))
        with ar.open(img) as stream:
            self.workspace.add_file(
                ID=imgid,
                mimetype=guess_type(img)[0],
                content=stream.read(),
                basename=os.path.basename(img),
                file_grp=imggrp,
            )

        xmlgrp = get_group_id("COR", gt=True, suffix=suffix)
        xmlid = get_file_id(_id, "COR", gt=True, suffix=suffix)
        self.log.debug("writing {}".format(xml))
        with ar.open(xml) as stream:
            # pcgts = parse(ar.open(xml))
            self.workspace.add_file(
                ID=xmlid,
                mimetype=MIMETYPE_PAGE,
                content=stream.read(),
                basename=os.path.basename(xml),
                file_grp=xmlgrp,
            )

    def download_all_archives(self):
        zips = list()
        for zip in self.parameter['zips']:
            zips.append(self.download(zip))
        return zips

    def download(self, zip):
        path = self.chached_path(zip)
        if Path(path).is_file():
            self.log.debug("using cached archive: {}".format(path))
            return path

        url = urllib.parse.urljoin(self.parameter['baseURL'], zip)
        self.log.debug("downloading {} to {}". format(url, path))
        with urllib.request.urlopen(url) as web, open(path, 'wb') as out:
            shutil.copyfileobj(web, out)

    def setup_cache_dir(self):
        try:
            os.makedirs(self.cache_dir)
        except FileExistsError:
            pass  # we do not care if cache dir already exists

    def chached_path(self, zip):
        return os.path.join(self.cache_dir, zip)
