from ocrd_models.constants import NAMESPACES as NS
from pathlib import Path
from os.path import join


def find_image_url(workspace, pcgts, input_file, prefixes=['OCR-D-IMG-BIN', 'OCR-D-IMG']):
    """Search for the assosiated image file for any given page XML file.
    Checks if the imageFilename of the page XML exists and returns
    this if it does exist.  If not, it checks the mets file for an
    associated image file and returns this in the order of file groups
    given with the prefixes array."""

    path = find_image_file_path(workspace, pcgts)
    if path:
        return path

    xpath = './/mets:fptr[@FILEID="%s"]' % input_file.ID
    # print("xpath =", str(xpath))
    fptr = workspace.mets._tree.getroot().find(xpath, NS)
    # print("fptr =", fptr)
    if fptr is None:
        return None

    for fptr in list(fptr.getparent()):#.getchildren():
        file_id = fptr.attrib['FILEID']
        #print("file_id =", file_id)
        for prefix in prefixes:
            if not file_id.startswith(prefix):
                continue
            tmp = workspace.mets.find_files(ID=file_id)
            if tmp is None or len(tmp) == 0:
                continue
            return tmp[0].url
    return None

def find_image_file_path(workspace, pcgts):
    """Checks the imageFilename attribute and returns this path, if the
    filename points to a valid file."""
    if pcgts.get_Page():
        path = Path(join(workspace.directory, pcgts.get_Page().imageFilename))
        if path.is_file():
            # return the relative path name for workspace.resolve_image_as_pil
            return pcgts.get_Page().imageFilename
    return None
