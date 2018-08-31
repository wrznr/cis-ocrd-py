import click

from ocrd.decorators import ocrd_cli_options
from ocrd.decorators import ocrd_cli_wrap_processor
from ocrd_cis.tools.prepare_with_gt import PrepareWithGT

@click.command()
@click.argument('zips', nargs=-1)
@ocrd_cli_options
def prepare_with_gt(zips, *args, **kwargs):
    PrepareWithGT.ZIPS = zips
    return ocrd_cli_wrap_processor(PrepareWithGT, *args, **kwargs)
