"""
CSV import for student rosters.

A secondary school has hundreds of students; entering them through a modal one
at a time is not something anyone will do, so this is what stands between the
app and an actual pilot.

Parsing is kept out of the view so it can be tested directly, and so a preview
("dry run") and a real import share exactly one implementation — a preview that
validates differently from the import it precedes is worse than no preview.

Expected columns (header row required, case and surrounding spaces ignored):

    student_id,name,grade,section[,is_active]

Unknown columns are ignored rather than rejected: real registry exports carry
extra fields, and refusing the file over a column nobody asked about would just
push people back to manual entry.
"""
import csv
import io

REQUIRED_COLUMNS = ('student_id', 'name', 'grade', 'section')
OPTIONAL_COLUMNS = ('is_active',)

MAX_ROWS = 2000
MAX_BYTES = 2 * 1024 * 1024

TRUE_VALUES = {'1', 'true', 'yes', 'y', 'active'}
FALSE_VALUES = {'0', 'false', 'no', 'n', 'inactive'}

# Mirrors the model's max_length, so a too-long value is reported against its
# row rather than raising a database error mid-import.
MAX_LENGTHS = {'student_id': 50, 'name': 255, 'grade': 50, 'section': 20}


class ImportError_(Exception):
    """The file as a whole cannot be processed — as distinct from a bad row."""


def _decode(raw):
    """
    Decode uploaded bytes.

    utf-8-sig first: Excel writes a BOM when saving as CSV, and without this the
    first header reads '﻿student_id' and the file looks like it is missing
    its student_id column. cp1252 is the fallback because Windows Excel is the
    most likely source of a school roster.
    """
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportError_(
        'Could not read the file as text. Save it as CSV (UTF-8) and try again.'
    )


def _sniff_dialect(text):
    """Accept comma, semicolon or tab — locale settings decide which Excel writes."""
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=',;\t')
    except csv.Error:
        return csv.excel


def parse_students_csv(raw, existing_student_ids=()):
    """
    Validate a CSV of students.

    Returns (rows, errors). `rows` are dicts ready to create; `errors` are
    {'row': <1-based line in the file>, 'error': <message>} and never abort the
    rest of the file — a roster with three bad rows should import the other 497
    and say which three need attention.

    `existing_student_ids` are the ids already taken in this tenant.
    """
    if not raw:
        raise ImportError_('The file is empty.')
    if len(raw) > MAX_BYTES:
        raise ImportError_(
            f'File is too large ({len(raw) // 1024} KB). The limit is '
            f'{MAX_BYTES // 1024} KB — split the roster and import it in parts.'
        )

    text = _decode(raw)
    reader = csv.DictReader(io.StringIO(text), dialect=_sniff_dialect(text))

    if not reader.fieldnames:
        raise ImportError_('The file has no header row.')

    # Normalise headers so 'Student ID', 'student_id' and ' STUDENT_ID ' agree.
    normalised = {
        (name or '').strip().lower().replace(' ', '_'): (name or '')
        for name in reader.fieldnames
    }
    missing = [column for column in REQUIRED_COLUMNS if column not in normalised]
    if missing:
        raise ImportError_(
            f'Missing required column(s): {", ".join(missing)}. '
            f'Expected a header row of: {", ".join(REQUIRED_COLUMNS)}.'
        )

    taken = {str(value) for value in existing_student_ids}
    seen_in_file = {}
    rows, errors = [], []

    for index, raw_row in enumerate(reader, start=2):  # row 1 is the header
        if len(rows) + len(errors) >= MAX_ROWS:
            errors.append({
                'row': index,
                'error': f'Stopped after {MAX_ROWS} rows — import the rest separately.',
            })
            break

        values = {
            key: (raw_row.get(source) or '').strip()
            for key, source in normalised.items()
            if key in REQUIRED_COLUMNS + OPTIONAL_COLUMNS
        }

        if not any(values.get(column) for column in REQUIRED_COLUMNS):
            continue  # blank line — trailing newlines are not an error

        blank = [column for column in REQUIRED_COLUMNS if not values.get(column)]
        if blank:
            errors.append({'row': index, 'error': f'Missing {", ".join(blank)}.'})
            continue

        too_long = [
            f'{column} (max {limit})'
            for column, limit in MAX_LENGTHS.items()
            if len(values.get(column, '')) > limit
        ]
        if too_long:
            errors.append({'row': index, 'error': f'Value too long: {", ".join(too_long)}.'})
            continue

        student_id = values['student_id']

        if student_id in taken:
            errors.append({
                'row': index,
                'student_id': student_id,
                'error': f'{student_id} already exists — skipped.',
            })
            continue

        if student_id in seen_in_file:
            errors.append({
                'row': index,
                'student_id': student_id,
                'error': f'{student_id} appears twice in this file (first on row '
                         f'{seen_in_file[student_id]}) — skipped.',
            })
            continue

        is_active = True
        raw_active = values.get('is_active', '').lower()
        if raw_active:
            if raw_active in TRUE_VALUES:
                is_active = True
            elif raw_active in FALSE_VALUES:
                is_active = False
            else:
                errors.append({
                    'row': index,
                    'student_id': student_id,
                    'error': f'is_active must be true or false, got {raw_active!r}.',
                })
                continue

        seen_in_file[student_id] = index
        rows.append({
            'row': index,
            'student_id': student_id,
            'name': values['name'],
            'grade': values['grade'],
            'section': values['section'],
            'is_active': is_active,
        })

    if not rows and not errors:
        raise ImportError_('The file has a header but no student rows.')

    return rows, errors
