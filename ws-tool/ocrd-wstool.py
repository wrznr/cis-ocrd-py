import os
import sys
import shutil
import subprocess
from zipfile import ZipFile

'''
#add files to workspace
python3.6 ocrd-wstool.py /path/to/workspace/ /path/to/folder containing zip files/
'''


def unpack(fromdir, todir):
    # extract all zips into temp dir

    path, dirs, files = os.walk(fromdir).__next__()
    for file in files:
        zipfile = os.path.join(fromdir, file)
        print("unzipping: {} to {}".format(zipfile, todir))
        with ZipFile(zipfile, 'r') as myzip:
            myzip.extractall(todir)


def subprocess_cmd(command):
    print("calling command {}".format(command.replace("\\s+", " ")))
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    out, err = process.communicate(command.encode('utf-8'))
    ret = process.wait()
    if ret != 0 or err is not None:
        raise Exception("error calling command: {} (returned {})"
                        .format(err, ret))
    print(out.decode('utf-8'))


def main(argv):

    # path to workspace
    wsdir = argv[1]
    if not os.path.exists(wsdir):
        os.makedirs(wsdir)

    # path to ground truth zip files
    gtdir = argv[2]

    # workspace id (optional)
    # wsid = argv[3]

    tempdir = gtdir + 'temp'
    fileprefix = 'file://'

    # unpack zip files into temp file
    unpack(gtdir, tempdir)

    # actualfolder = os.getcwd()

    os.chdir(wsdir)

    initcmd = 'ocrd workspace init {}'.format(wsdir)
    subprocess_cmd(initcmd)

    # setidcmd = 'ocrd workspace set-id {}'.format(wsid)
    # subprocess_cmd(setidcmd)

    # walk through unpacked zipfiles and add tifs and xmls to workspace
    path, dirs, files = os.walk(tempdir).__next__()
    for d in dirs:
        filedir = os.path.join(tempdir, d, d)
        for path2, dirs2, tiffiles in os.walk(filedir):
            for tif in tiffiles:
                if tif[-4:] == '.tif':
                    filename = tif[:-4]

                    tifdir = os.path.join(filedir, tif)
                    xmldir = os.path.join(filedir, 'page', filename + '.xml')

                    # add tif image to workspace
                    filegrp = 'OCR-D-IMG'
                    mimetype = 'image/tif'
                    fileid = filegrp + '-' + filename
                    grpid = fileid
                    imgcmd = '''ocrd workspace add \
                    --file-grp {filegrp} \
                    --file-id {fileid} \
                    --group-id {grpid} \
                    --mimetype {mimetype} \
                    {fdir}'''.format(filegrp=filegrp, fileid=fileid, grpid=grpid,
                                     mimetype=mimetype, fdir=tifdir)
                    subprocess_cmd(imgcmd)

                    # add xml to workspace
                    filegrp = 'OCR-D-XML'
                    mimetype = 'application/vnd.prima.page+xml'
                    fileid = filegrp + '-' + filename
                    grpid = fileid
                    xmlcmd = '''ocrd workspace add \
                    --file-grp {filegrp} \
                    --file-id {fileid} \
                    --group-id {grpid} \
                    --mimetype {mimetype} \
                    {fdir}'''.format(filegrp=filegrp, fileid=fileid, grpid=grpid,
                                     mimetype=mimetype, fdir=xmldir)
                    subprocess_cmd(xmlcmd)

                    # rename filepaths in xml into file-urls
                    print("tif:{}, path2:{}, dirs2:{}".format(tif, path2, dirs2))
                    sedcmd = '''
                    sed -i {fname} -e 's#imageFilename="{tif}"#imageFilename="{fdir}"#'
                    '''.format(fname=xmldir, tif=tif,
                               fdir=fileprefix+wsdir+'OCR-D-IMG/'+tif)

                    subprocess_cmd(sedcmd)
    shutil.rmtree(tempdir)


if __name__ == '__main__':
    main(sys.argv)
