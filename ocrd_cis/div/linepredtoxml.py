from __future__ import absolute_import
from ocrd_cis import get_ocrd_tool

import sys
import os.path
from PIL import Image

from ocrd.utils import getLogger
from ocrd.model.ocrd_page import from_file, to_xml, TextEquivType, TextRegionType, TextLineType
from ocrd import Processor, MIMETYPE_PAGE

sys.path.append(os.path.dirname(os.path.abspath(__file__)))



class LptXML(Processor):

    def __init__(self, *args, **kwargs):
        self.ocrd_tool = get_ocrd_tool()
        kwargs['ocrd_tool'] = self.ocrd_tool['tools']['ocrd-cis-linepredtoxml']
        kwargs['version'] = self.ocrd_tool['version']
        super(LptXML, self).__init__(*args, **kwargs)
        self.log = getLogger('LptXML')

    def process(self):
        """
        Performs the (text) recognition.
        """

        predpath = self.parameter['predpath']

        if '/' == predpath[-1]:
            predpath = predpath[:-1]
        mainfolder = predpath[predpath.rfind('/')+1:]

        _, dirs, _ = os.walk(predpath).__next__()

        for dir in dirs:
            root, _, files = os.walk(os.path.join(predpath, dir)).__next__()
            png_ocr_dict = {}

            for file in files:
                if '.png' in file[-4:]:

                    image = Image.open(root + '/' + file)
                    w, _ = image.size

                    # (h, w = image.shape)
                    if w > 5000:
                        print("final image too long: %d", w)
                        continue
                    png_ocr_dict[file] = {}


            for png in png_ocr_dict.keys():
                with open(root + '/' + png[:-8]+'.gt.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['GT'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--ocropy-fraktur.pyrnn.gz.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['OCROPY-FRAKTUR'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--ocropy-incunabula-00184000.pyrnn.gz.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['OCROPY-INCUNABULA'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--ocropy-latin1-00081000.pyrnn.gz.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['OCROPY-LATIN1'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--ocropy-latin2-00069000.pyrnn.gz.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['OCROPY-LATIN2'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--ocropy-ridges1-00085000.pyrnn.gz.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['OCROPY-RIDGES1'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--ocropy-ridges2-00062000.pyrnn.gz.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['OCROPY-RIDGES2'] = infile.readline().rstrip("\n\f")
                with open(root + '/' + png[:-4]+'--tess-deu_frak.txt', 'r', encoding="utf-8-sig") as infile:
                    png_ocr_dict[png]['TESSERACT-DEUFRAK'] = infile.readline().rstrip("\n\f")


            input_file = self.input_files[0]
            pcgts = from_file(self.workspace.download_file(input_file))

            #creating one big dummy Region for all snippet ocrs
            dummyRegion = TextRegionType()
            pcgts.get_Page().add_TextRegion(dummyRegion)


            #List to sort elements in the appropriate order
            orderlist = ['TESSERACT-DEUFRAK', 'OCROPY-FRAKTUR', 'OCROPY-INCUNABULA', 'OCROPY-LATIN1', 'OCROPY-LATIN2', 'OCROPY-RIDGES1', 'OCROPY-RIDGES2', 'GT']
            
            #adding OCR-Predictions to textline with png-dir as id
            for png, ocrs in png_ocr_dict.items():
                textline = TextLineType(id=mainfolder+'/'+dir+'/'+png)
                for i in range(0,8):
                    textline.add_TextEquiv(TextEquivType(index=i,Unicode=ocrs[orderlist[i]], dataType=orderlist[i]))
                dummyRegion.add_TextLine(textline)


            output_file_grp = '-'.join(['OCR-D',mainfolder,dir])
            ID = output_file_grp

            self.log.info('creating file id: %s, name: %s, file_grp: %s', 
            ID, input_file.basename, self.output_file_grp)

            # Use the input file's basename for the new file
            # this way the files retain the same basenames.


            out = self.workspace.add_file(
                ID=ID,
                file_grp=output_file_grp,
                basename=output_file_grp + '.xml',
                mimetype=MIMETYPE_PAGE,
                local_filename="%s/%s.xml" % (self.output_file_grp, ID),
                content=to_xml(pcgts).encode('utf-8')
                )
