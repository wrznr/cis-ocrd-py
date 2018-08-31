import click

from ocrd.decorators import ocrd_cli_options
from ocrd.decorators import ocrd_cli_wrap_processor
from ocrd_cis.tools.add_gt_to_workspace import AddGTToWorkspace

@click.command()
@click.argument('zips', nargs=-1)
@ocrd_cli_options
def cis_ocrd_add_gt_to_workspace(zips, *args, **kwargs):
    AddGTToWorkspace.ZIPS = zips
    return ocrd_cli_wrap_processor(AddGTToWorkspace, *args, **kwargs)
