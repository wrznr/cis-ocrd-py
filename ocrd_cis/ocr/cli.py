import click

from ocrd.decorators import ocrd_cli_options
from ocrd.decorators import ocrd_cli_wrap_processor
from .ocr import OCR


@click.command()
@ocrd_cli_options
def ocr(*args, **kwargs):
    return ocrd_cli_wrap_processor(OCR, *args, **kwargs)
