"""
Location import from Excel/CSV.

Required headers: Name, Admin Level, Admin Level Name, P Code, Active, Parent
- Upsert by P Code (create if new, update if exists).
- Parent resolved by Parent P Code (from file or existing locations).
- Active normalized: TRUE/FALSE, 1/0, Yes/No.
"""
import csv
import io
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import openpyxl
from unicef_locations.utils import get_location_model

logger = logging.getLogger(__name__)

LOCATION_IMPORT_SESSION_KEY = 'location_import_validated_rows'
REQUIRED_HEADERS = ['Name', 'Admin Level', 'Admin Level Name', 'P Code', 'Active', 'Parent']
HEADER_TO_KEY = {
    'Name': 'name',
    'Admin Level': 'admin_level',
    'Admin Level Name': 'admin_level_name',
    'P Code': 'p_code',
    'Active': 'is_active',
    'Parent': 'parent_p_code',
}


def _normalize_active(value: Any) -> bool:
    """Normalize Active to boolean. Accepts TRUE/FALSE, 1/0, Yes/No."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return True
    s = str(value).strip().upper()
    if s in ('TRUE', '1', 'YES', 'Y'):
        return True
    if s in ('FALSE', '0', 'NO', 'N'):
        return False
    raise ValueError(f"Active must be TRUE/FALSE, 1/0, or Yes/No; got: {value!r}")


def _parse_admin_level(value: Any) -> Optional[int]:
    """Parse Admin Level to small integer."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"Admin Level must be a number- got: {value!r}")


def validate_row(row_idx: int, raw: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate and normalize a row. Returns (validated_dict, error_message).
    If error_message is set, validated_dict is None.
    """
    try:
        name = (raw.get('Name') or raw.get('name') or '').strip()
        if not name:
            return None, f"Row {row_idx}: Name is required"
        admin_level = _parse_admin_level(raw.get('Admin Level') or raw.get('admin_level'))
        admin_level_name = (raw.get('Admin Level Name') or raw.get('admin_level_name') or '').strip()
        p_code = (raw.get('P Code') or raw.get('p_code') or '').strip()
        if not p_code:
            return None, f"Row {row_idx}: P Code is required"
        if len(p_code) > 32:
            return None, f"Row {row_idx}: P Code must be at most 32 characters"
        is_active = _normalize_active(raw.get('Active') or raw.get('active'))
        parent_p_code = (raw.get('Parent') or raw.get('parent') or '').strip() or None
        return {
            'name': name,
            'admin_level': admin_level,
            'admin_level_name': admin_level_name or None,
            'p_code': p_code,
            'is_active': is_active,
            'parent_p_code': parent_p_code,
        }, None
    except ValueError as e:
        return None, f"Row {row_idx}: {e}"


def parse_csv(content: bytes) -> List[Dict[str, Any]]:
    """Parse CSV bytes; first row = headers. Returns list of raw row dicts."""
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def parse_xlsx(content: bytes) -> List[Dict[str, Any]]:
    """Parse Excel bytes; first row = headers. Returns list of raw row dicts."""
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return []
    headers = [str(c).strip() if c is not None else '' for c in rows[0]]
    result = []
    for row in rows[1:]:
        result.append(dict(zip(headers, (c if c is not None else '' for c in row))))
    return result


def parse_file(content: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parse file by extension. Returns list of raw row dicts."""
    lower = filename.lower()
    if lower.endswith('.csv'):
        return parse_csv(content)
    if lower.endswith(('.xlsx', '.xls')):
        return parse_xlsx(content)
    raise ValueError("File must be .csv or .xlsx")


def validate_and_preview(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate all rows and return (validated_rows, errors).
    validated_rows have keys: name, admin_level, admin_level_name, p_code, is_active, parent_p_code.
    """
    validated = []
    errors = []
    for i, raw in enumerate(rows, start=2):
        v, err = validate_row(i, raw)
        if err:
            errors.append(err)
        elif v:
            validated.append(v)
    return validated, errors


def process_uploaded_file(content: bytes, filename: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse and validate an uploaded file. Returns (validated_rows, errors)."""
    raw_rows = parse_file(content, filename)
    return validate_and_preview(raw_rows)


def can_import_locations(user) -> bool:
    """Return True if user may use the Location admin import."""
    return user.is_staff and user.has_perm('locations.change_location')


def handle_import_upload(request, form, app_label: str, model_name: str) -> Tuple[Optional[HttpResponseRedirect], Any]:
    """
    Process uploaded file form. Returns (redirect_response_or_none, form_with_errors).
    If redirect is returned, form is valid and data is stored in session.
    """
    if request.method == 'POST' and form.is_valid():
        try:
            content = form.cleaned_data['import_file'].read()
            validated_rows, errors = process_uploaded_file(content, form.cleaned_data['import_file'].name)
        except Exception as e:
            form.add_error('import_file', str(e))
        else:
            if errors:
                for err in errors[:20]:
                    form.add_error(None, err)
                if len(errors) > 20:
                    form.add_error(None, _('… and %(count)s more errors.') % {'count': len(errors) - 20})
            else:
                request.session[LOCATION_IMPORT_SESSION_KEY] = validated_rows
                request.session.modified = True
                return HttpResponseRedirect(reverse('admin:%s_%s_import_preview' % (app_label, model_name))), form
    return None, form


def handle_import_preview(request, app_label: str, model_name: str) -> Tuple[Optional[HttpResponseRedirect], Optional[List[Dict[str, Any]]]]:
    """
    Handle preview view: check session, process confirmation if POST.
    Returns (redirect_response_or_none, validated_rows_or_none).
    """
    validated_rows = request.session.get(LOCATION_IMPORT_SESSION_KEY)
    if validated_rows is None:
        messages.warning(request, _('No import data in session. Please upload a file again.'))
        return HttpResponseRedirect(reverse('admin:%s_%s_import' % (app_label, model_name))), None
    if request.method == 'POST' and request.POST.get('confirm') == '1':
        created, updated, errors = run_import(validated_rows)
        del request.session[LOCATION_IMPORT_SESSION_KEY]
        request.session.modified = True
        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            messages.success(request, _('Import complete: %(created)s created, %(updated)s updated.') % {
                'created': created, 'updated': updated})
        return HttpResponseRedirect(reverse('admin:%s_%s_changelist' % (app_label, model_name))), None
    return None, validated_rows


def get_import_upload_context(admin_site, request, form, opts) -> Dict[str, Any]:
    """Build context dict for import upload template."""
    return {
        **admin_site.each_context(request),
        'title': _('Import Locations'),
        'form': form,
        'opts': opts,
        'required_headers': REQUIRED_HEADERS,
    }


def get_import_preview_context(admin_site, request, opts, validated_rows, app_label: str, model_name: str) -> Dict[str, Any]:
    """Build context dict for import preview template."""
    return {
        **admin_site.each_context(request),
        'title': _('Preview Import'),
        'opts': opts,
        'rows': validated_rows,
        'import_url': reverse('admin:%s_%s_import' % (app_label, model_name)),
    }


def run_import(validated_rows: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
    """
    Upsert locations by P Code. Resolve parent by Parent P Code (existing or from same batch).
    Returns (created_count, updated_count, errors).
    After bulk ops, rebuilds MPTT tree.
    """
    Location = get_location_model()
    if not validated_rows:
        return 0, 0, []

    p_codes_in_file = {r['p_code'] for r in validated_rows}
    existing = {loc.p_code: loc for loc in Location.objects.filter(p_code__in=p_codes_in_file)}
    parent_p_codes = {r['parent_p_code'] for r in validated_rows if r.get('parent_p_code')}
    parents_from_db = dict(
        Location.objects.filter(p_code__in=parent_p_codes).values_list('p_code', 'pk')
    )
    for parent_p_code in parent_p_codes:
        if parent_p_code not in parents_from_db and parent_p_code not in p_codes_in_file:
            return 0, 0, [f"Parent P Code not found: {parent_p_code!r} (must exist in DB or in file)"]

    to_create = []
    to_update = []
    created_count = 0
    updated_count = 0

    for row in validated_rows:
        p_code = row['p_code']
        parent_p_code = row.get('parent_p_code')
        parent_id = parents_from_db.get(parent_p_code) if parent_p_code else None
        if parent_p_code and parent_id is None and parent_p_code in p_codes_in_file:
            parent_id = None

        if p_code in existing:
            loc = existing[p_code]
            loc.name = row['name']
            loc.admin_level = row['admin_level']
            loc.admin_level_name = row['admin_level_name']
            loc.is_active = row['is_active']
            loc.parent_id = parent_id
            to_update.append(loc)
            updated_count += 1
        else:
            loc = Location(
                name=row['name'],
                admin_level=row['admin_level'],
                admin_level_name=row['admin_level_name'],
                p_code=p_code,
                is_active=row['is_active'],
                parent_id=parent_id,
            )
            for key in ['lft', 'rght', 'level', 'tree_id']:
                setattr(loc, key, 0)
            to_create.append(loc)
            created_count += 1

    if to_update:
        Location.objects.bulk_update(
            to_update,
            fields=['name', 'admin_level', 'admin_level_name', 'is_active', 'parent_id'],
        )
    if to_create:
        Location.objects.bulk_create(to_create)

    pcode_to_pk = dict(Location.objects.filter(p_code__in=p_codes_in_file).values_list('p_code', 'pk'))
    to_fix_parent = []
    for row in validated_rows:
        parent_p_code = row.get('parent_p_code')
        if not parent_p_code or parent_p_code not in pcode_to_pk:
            continue
        child_pk = pcode_to_pk.get(row['p_code'])
        if not child_pk:
            continue
        parent_pk = pcode_to_pk[parent_p_code]
        to_fix_parent.append((child_pk, parent_pk))
    if to_fix_parent:
        for child_pk, parent_pk in to_fix_parent:
            Location.objects.filter(pk=child_pk).update(parent_id=parent_pk)

    errors = []
    try:
        Location.objects.rebuild()
    except Exception as e:
        logger.exception("Location tree rebuild failed: %s", e)
        errors.append(f"Tree rebuild failed: {e}")

    return created_count, updated_count, errors
