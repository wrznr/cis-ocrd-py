from __future__ import absolute_import

import sys
import os.path
import io
import numpy as np
from skimage import measure, draw
import cv2
from scipy.ndimage import filters

from ocrd_utils import getLogger
from ocrd_modelfactory import page_from_file
from ocrd_models.ocrd_page import to_xml, AlternativeImageType
from ocrd import Processor
from ocrd_utils import MIMETYPE_PAGE

from .. import get_ocrd_tool
from . import common
from .ocrolib import midrange
from .common import (
    coordinates_of_segment,
    coordinates_for_segment,
    image_from_page,
    image_from_segment,
    pil2array, array2pil,
    check_line, check_page,
    # binarize,
    compute_line_labels,
    borderclean_bin,
    points_from_polygon,
    xywh_from_points,
    save_image_file
)

#sys.path.append(os.path.dirname(os.path.abspath(__file__)))

TOOL = 'ocrd-cis-ocropy-resegment'
LOG = getLogger('processor.OcropyResegment')
FILEGRP_IMG = 'OCR-D-IMG-RESEG'

def resegment(line_polygon, region_labels, region_bin, line_id,
              extend_margins=3,
              threshold_relative=0.8, threshold_absolute=50):
    """Reduce polygon in a labelled region to the largest intersection.
    
    Given a Numpy array `line_polygon` of relative coordinates
    in a region given by a Numpy array `region_labels` of numbered
    segments and a Numpy array `region_bin` of foreground pixels,
    find the label of the largest segment that intersects the polygon.
    If the number of foreground pixels within that segment is larger
    than `threshold_absolute` and if the share of foreground pixels
    within the whole polygon is larger than `threshold_relative`,
    then compute the contour of that intersection and return it
    as a new polygon. Otherwise, return None.
    
    If `extend_margins` is larger than zero, then extend `line_polygon`
    by that amount of pixels horizontally and vertically before.
    """
    height, width = region_labels.shape
    # mask from line polygon:
    line_mask = np.zeros_like(region_labels)
    line_mask[draw.polygon(line_polygon[:,1], line_polygon[:,0], line_mask.shape)] = 1
    # pad line polygon (extend the mask):
    line_mask = filters.maximum_filter(line_mask, 1 + 2 * extend_margins)
    # intersect with region labels
    line_labels = region_labels * line_mask
    if not np.count_nonzero(line_labels):
        LOG.warning('Label mask is empty for line "%s"', line_id)
        return None
    # find the mask of the largest label (in the foreground):
    total_count = np.sum(region_bin * line_mask)
    line_labels_fg = region_bin * line_labels
    if not np.count_nonzero(line_labels_fg):
        LOG.warning('No foreground pixels within line mask for line "%s"', line_id)
        return None
    label_counts = np.bincount(line_labels_fg.flat)
    max_label = np.argmax(label_counts[1:]) + 1
    max_count = label_counts[max_label]
    if (max_count < threshold_absolute and
        max_count / total_count < threshold_relative):
        LOG.info('Largest label (%d) is too small (%d/%d) in line "%s"',
                 max_label, max_count, total_count, line_id)
        return None
    LOG.debug('Black pixels before/after resegment of line "%s" (nlabels=%d): %d/%d',
              line_id, len(label_counts.nonzero()[0]), total_count, max_count)
    line_mask = np.array(line_labels == max_label, np.uint8)
    # measure.find_contours() produces open paths when touching boundaries...
    # ...how about measure.centroid(line_mask) vs measure.centroid(line_bin)?
    # convert to polygon outline:
    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # concatenate contour parts (happens with non-contiguous masks due to large hspace):
    line_polygon = np.vstack(path for path in [
        # simplify shape:
        measure.approximate_polygon(contour[:, 0, ::], 2) # already ordered x,y
        # filter parts with less than 4 points:
        for contour in contours] if len(path) >= 4)
    if len(line_polygon) < 4:
        LOG.warning('found no contour of >=4 points for line "%s"', line_id)
        return None
    return line_polygon

class OcropyResegment(Processor):

    def __init__(self, *args, **kwargs):
        self.ocrd_tool = get_ocrd_tool()
        kwargs['ocrd_tool'] = self.ocrd_tool['tools'][TOOL]
        kwargs['version'] = self.ocrd_tool['version']
        super(OcropyResegment, self).__init__(*args, **kwargs)

    def process(self):
        """Resegment lines of the workspace.
        
        Open and deserialise PAGE input files and their respective images,
        then iterate over the element hierarchy down to the line level.
        
        Next, get each region image according to the layout annotation (from
        the alternative image of the region, or by cropping via coordinates
        into the higher-level image), binarize it (without deskewing), and
        compute a new line segmentation from that (as a label mask).
        
        Then for each line within the region, find the label with the largest
        foreground area in the binarized image within the annotated polygon
        (or rectangle) of the line. Unless its relative area is too small,
        or its center is far off, convert that label's mask into a polygon
        outline, intersect with the old polygon, and find the contour of that
        segment. Annotate the result as new coordinates of the line.
        
        Produce a new output file by serialising the resulting hierarchy.
        """
        # This makes best sense for bad/coarse segmentation, like current GT.
        # Most notably, it can convert rectangles to polygons. It depends on
        # a decent line segmentation from ocropy though. So it _should_ ideally
        # be run after deskewing (on the page or region level), and preferably
        # after binarization (on page or region level), because segmentation of
        # both a skewed image or of implicit binarization could be suboptimal,
        # and the explicit binarization after resegmentation could be, too.
        threshold = self.parameter['min_fraction']
        margin = self.parameter['extend_margins']
        
        for (n, input_file) in enumerate(self.input_files):
            LOG.info("INPUT FILE %i / %s", n, input_file.pageId or input_file.ID)
            file_id = input_file.ID.replace(self.input_file_grp, FILEGRP_IMG)
            if file_id == input_file.ID:
                file_id = concat_padded(FILEGRP_IMG, n)
            
            pcgts = page_from_file(self.workspace.download_file(input_file))
            page_id = pcgts.pcGtsId or input_file.pageId or input_file.ID # (PageType has no id)
            page = pcgts.get_Page()
            page_image, page_xywh, page_image_info = image_from_page(
                self.workspace, page, page_id)
            if page_image_info.xResolution != 1:
                dpi = page_image_info.xResolution
                if page_image_info.resolutionUnit == 'cm':
                    dpi = round(dpi * 2.54)
                LOG.info('Page "%s" uses %d DPI', page_id, dpi)
                zoom = 300.0/dpi
            else:
                zoom = 1
            
            regions = page.get_TextRegion()
            if not regions:
                LOG.warning('Page "%s" contains no text regions', page_id)
            for region in regions:
                lines = region.get_TextLine()
                if not lines:
                    LOG.warning('Page "%s" region "%s" contains no text lines', page_id, region.id)
                    continue
                region_image, region_xywh = image_from_segment(
                    self.workspace, region, page_image, page_xywh)
                # ad-hoc binarization:
                region_array = pil2array(region_image)
                region_array, _ = common.binarize(region_array, maxskew=0) # just in case still raw
                region_bin = np.array(region_array <= midrange(region_array), np.uint8)
                try:
                    region_labels = compute_line_labels(region_array, zoom=zoom)
                except Exception as err:
                    LOG.warning('Cannot line-segment page "%s" region "%s": %s',
                                page_id, region.id, err)
                    # fallback option 1: borderclean
                    # label margins vs interior, but with the interior
                    # extended into the margin by its connected components
                    # to remove noise from neighbouring regions:
                    #region_labels = borderclean_bin(region_bin, margin=round(4/zoom)) + 1
                    # too dangerous, because we risk loosing dots from i or punctuation;
                    # fallback option2: only extend_margins
                    # instead, just provide a uniform label, so at least we get
                    # to extend the polygon margins:
                    #region_labels = np.ones_like(region_bin)
                    # fallback option3: keep unchanged
                    continue
                for line in lines:
                    alternative_image = line.get_AlternativeImage()
                    if alternative_image:
                        LOG.debug("Using AlternativeImage %d (%s) for line '%s'",
                                  len(alternative_image), alternative_image[-1].get_comments(),
                                  line.id)
                        line_image = workspace.resolve_image_as_pil(
                            alternative_image[-1].get_filename())
                        # crop region_labels accordingly:
                        line_xywh = xywh_from_points(line.get_Coords().points)
                        line_labels = region_labels[line_xywh['y']-region_xywh['y']:
                                                    line_xywh['y']-region_xywh['y']+line_xywh['h'],
                                                    line_xywh['x']-region_xywh['x']:
                                                    line_xywh['x']-region_xywh['x']+line_xywh['w']]
                        line_bin = region_bin[line_xywh['y']-region_xywh['y']:
                                              line_xywh['y']-region_xywh['y']+line_xywh['h'],
                                              line_xywh['x']-region_xywh['x']:
                                              line_xywh['x']-region_xywh['x']+line_xywh['w']]
                        # get polygon in relative (line) coordinates:
                        line_polygon = coordinates_of_segment(line, line_image, line_xywh)
                        line_polygon = resegment(line_polygon, line_labels, line_bin, line.id,
                                                 extend_margins=margin, threshold_relative=threshold)
                        if line_polygon is None:
                            continue # not good enough – keep
                        # convert back to absolute (page) coordinates:
                        line_polygon = coordinates_for_segment(line_polygon, line_image, line_xywh)
                    else:
                        # get polygon in relative (region) coordinates:
                        line_polygon = coordinates_of_segment(line, region_image, region_xywh)
                        line_polygon = resegment(line_polygon, region_labels, region_bin, line.id,
                                                 extend_margins=margin, threshold_relative=threshold)
                        if line_polygon is None:
                            continue # not good enough – keep
                        # convert back to absolute (page) coordinates:
                        line_polygon = coordinates_for_segment(line_polygon, region_image, region_xywh)
                    # annotate result:
                    line.get_Coords().points = points_from_polygon(line_polygon)
                    # create new image:
                    line_image, line_xywh = image_from_segment(
                        self.workspace, line, region_image, region_xywh)
                    # update METS (add the image file):
                    file_path = save_image_file(
                        self.workspace,
                        line_image,
                        file_id=file_id + '_' + region.id + '_' + line.id,
                        page_id=page_id,
                        file_grp=FILEGRP_IMG)
                    # update PAGE (reference the image file):
                    line.add_AlternativeImage(AlternativeImageType(
                        filename=file_path,
                        comments=('cropped,clipped')))
            
            # update METS (add the PAGE file):
            file_id = input_file.ID.replace(self.input_file_grp,
                                            self.output_file_grp)
            if file_id == input_file.ID:
                file_id = concat_padded(self.output_file_grp, n)
            file_path = os.path.join(self.output_file_grp,
                                     file_id + '.xml')
            out = self.workspace.add_file(
                ID=file_id,
                file_grp=self.output_file_grp,
                pageId=input_file.pageId,
                local_filename=file_path,
                mimetype=MIMETYPE_PAGE,
                content=to_xml(pcgts))
            LOG.info('created file ID: %s, file_grp: %s, path: %s',
                     file_id, self.output_file_grp, out.local_filename)
    
