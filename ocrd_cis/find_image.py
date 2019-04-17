from ocrd_models.constants import NAMESPACES as NS
#.constants
def find_image(mets, input_file, prefixes=['OCR-D-IMG-BIN', 'OCR-D-IMG']):
    xpath = './/mets:fptr[@FILEID="%s"]' % input_file.ID
    # print("xpath =", str(xpath))
    fptr = mets._tree.getroot().find(xpath, NS)
    # print("fptr =", fptr)
    if fptr is None:
        return None

    for fptr in list(fptr.getparent()):#.getchildren():
        file_id = fptr.attrib['FILEID']
        #print("file_id =", file_id)
        for prefix in prefixes:
            if not file_id.startswith(prefix):
                continue
            tmp = mets.find_files(ID=file_id)
            if tmp is None or len(tmp) == 0:
                continue
            return tmp[0]
    return None
