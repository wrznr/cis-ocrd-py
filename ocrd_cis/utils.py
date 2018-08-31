import json
from pkg_resources import resource_string


def get_ocrd_tool():
    """Load the json-formatted config file."""
    return json.loads(
        resource_string(__name__, 'ocrd-tool.json').decode('utf8'))


def get_file_group_id(step, processor="CIS", gt=False, suffix=""):
    """Construct an OCR-D compatible group id string."""
    gtstr = ""
    if gt:
        gtstr = "-GT"
    return "OCR-D{gt}-{step}-{processor}{suffix}".format(
        gt=gtstr,
        step=step,
        processor=processor,
        suffix=suffix
    ).replace('_', '-')


def get_file_id(_id, step, processor="CIS", gt=False, suffix=""):
    """Construct an OCR-D compatible file id string."""
    return get_file_group_id(
        step,
        processor=processor,
        gt=gt,
        suffix=suffix
    ) + "_{:04d}".format(_id)
