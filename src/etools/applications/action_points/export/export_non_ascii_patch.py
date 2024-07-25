import types

from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import IllegalCharacterError
from tablib.formats._xlsx import XLSXFormat


def dset_sheet(cls, dataset, ws, freeze_panes=True, escape=False):
    """Completes given worksheet from given Dataset."""
    _package = dataset._package(dicts=False)

    for i, sep in enumerate(dataset._separators):
        _offset = i
        _package.insert((sep[0] + _offset), (sep[1],))

    bold = Font(bold=True)
    wrap_text = Alignment(wrap_text=True)

    for i, row in enumerate(_package):
        row_number = i + 1
        for j, col in enumerate(row):
            col_idx = get_column_letter(j + 1)
            cell = ws[f'{col_idx}{row_number}']

            # bold headers
            if (row_number == 1) and dataset.headers:
                cell.font = bold
                if freeze_panes:
                    #  Export Freeze only after first Line
                    ws.freeze_panes = 'A2'

            # bold separators
            elif len(row) < dataset.width:
                cell.font = bold

            # wrap the rest
            else:
                if '\n' in str(col):
                    cell.alignment = wrap_text

            try:
                cell.value = col
            except (ValueError, IllegalCharacterError):
                from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
                cell.value = str(ILLEGAL_CHARACTERS_RE.sub(r'', col))

            if escape and cell.data_type == 'f' and cell.value.startswith('='):
                cell.value = cell.value.replace("=", "")


XLSXFormat.dset_sheet = types.MethodType(dset_sheet, XLSXFormat)
