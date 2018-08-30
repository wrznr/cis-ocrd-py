import json
from pkg_resources import resource_string


def get_ocrd_tool():
    """Load the json-formatted config file."""
    return json.loads(
        resource_string(__name__, 'ocrd-tool.json').decode('utf8'))


def get_group_id(step, processor="CIS", gt=False, suffix=""):
    """Construct an OCR-D compatible group id string."""
    if suffix != "":
        suffix = "-" + suffix.replace('_', '-')
    gtstr = ""
    if gt:
        gtstr = "-GT"
    return "OCR-D{gt}-{step}-{processor}{suffix}".format(
        gt=gtstr,
        step=step,
        processor=processor,
        suffix=suffix
    )


def get_file_id(_id, step, processor="CIS", gt=False, suffix=""):
    """Construct an OCR-D compatible file id string."""
    return get_group_id(
        step,
        processor=processor,
        gt=gt,
        suffix=suffix
    ) + "-{:04d}".format(_id)
