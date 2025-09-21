#!/usr/bin/env python3
"""
CSV → Selected Person Folders with Interactive PDFs
Processes CSV contacts, filters by inclusion/exclusion lists, and creates organized output folders.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from slugify import slugify
from unidecode import unidecode

try:
    import usaddress
    HAS_USADDRESS = True
except ImportError:
    HAS_USADDRESS = False
    print("Warning: usaddress not available, using fallback address parsing", file=sys.stderr)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfform
from reportlab.lib.colors import black


class PersonProcessor:
    """Processes person records from CSV and generates output artifacts."""

    # Column aliases for normalization
    COLUMN_ALIASES = {
        'full_name': ['name', 'full_name', 'system_name'],  # Added 'system_name' for this CSV
        'first_name': ['first_name', 'first', 'given_name'],
        'last_name': ['last_name', 'last', 'surname', 'family_name'],
        'middle_name': ['middle_name', 'middle'],
        'suffix': ['suffix'],
        'address': ['address', 'street_address', 'mailing_address'],
        'street': ['street', 'street_address'],
        'city': ['city', 'town'],
        'state': ['state', 'province', 'state/prov'],  # Added 'state/prov' for this CSV
        'postal_code': ['zip', 'zip_code', 'postal', 'postal_code'],
        'country': ['country'],
        'email': ['email', 'e-mail', 'e_mail'],
        'phone': ['phone', 'telephone', 'tel'],
        'company': ['company', 'organization', 'org'],
        'system_id': ['system_id', 'systemid', 'id', 'record_id']
    }

    # US state abbreviations
    US_STATES = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY'
    }

    def __init__(self, csv_path: str, names_file: str, output_dir: str):
        self.csv_path = Path(csv_path)
        self.names_file = Path(names_file)
        self.output_dir = Path(output_dir)
        self.selected_people_dir = self.output_dir / "selected_people"

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.selected_people_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.log_file = self.output_dir / "run.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, mode='w'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Statistics
        self.stats = {
            'total_rows': 0,
            'matched_inclusion': 0,
            'excluded_denylist': 0,
            'exported': 0,
            'skipped_no_name': 0,
            'address_parse_warnings': 0
        }

        # Load filters
        self.inclusion_names = self._load_inclusion_names()
        self.exclusion_names = self._load_exclusion_names()

        # Index data
        self.index_data = []

    def _load_inclusion_names(self) -> List[str]:
        """Load and parse inclusion names from filter file."""
        names = []
        if not self.names_file.exists():
            self.logger.warning(f"Names filter file not found: {self.names_file}")
            return names

        with open(self.names_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    names.append(line.lower())

        self.logger.info(f"Loaded {len(names)} inclusion names")
        return names

    def _load_exclusion_names(self) -> List[str]:
        """Load exclusion names from denylist file."""
        exclude_file = Path("config/exclude_names.txt")
        names = []

        if not exclude_file.exists():
            # Create with default Claudette
            exclude_file.parent.mkdir(parents=True, exist_ok=True)
            with open(exclude_file, 'w', encoding='utf-8') as f:
                f.write("# Names containing these tokens are always excluded (case-insensitive).\n")
                f.write("Claudette\n")

        with open(exclude_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    names.append(line.lower())

        self.logger.info(f"Loaded {len(names)} exclusion tokens")
        return names

    def _normalize_column_name(self, col: str) -> str:
        """Convert column name to snake_case and apply aliases."""
        # Convert to snake_case
        col = re.sub(r'[^\w\s]', '', col)
        col = re.sub(r'\s+', '_', col)
        col = col.lower().strip('_')

        # Apply aliases
        for canonical, aliases in self.COLUMN_ALIASES.items():
            if col in aliases or col == canonical:
                return canonical

        return col

    def _parse_name(self, row: Dict) -> Dict[str, str]:
        """Parse name components from row data."""
        name_parts = {
            'first': '',
            'middle': '',
            'last': '',
            'suffix': ''
        }

        # Try explicit first/last columns first
        if row.get('first_name'):
            name_parts['first'] = self._title_case(row['first_name'])
        if row.get('last_name'):
            name_parts['last'] = self._title_case(row['last_name'])
        if row.get('middle_name'):
            name_parts['middle'] = self._title_case(row['middle_name'])
        if row.get('suffix'):
            name_parts['suffix'] = row['suffix']

        # If no explicit first/last, try to parse full_name
        if not (name_parts['first'] or name_parts['last']) and row.get('full_name'):
            full = row['full_name'].strip()

            # Check for "Last, First [Middle]" format
            if ',' in full:
                parts = full.split(',', 1)
                name_parts['last'] = self._title_case(parts[0].strip())
                rest = parts[1].strip().split()
                if rest:
                    name_parts['first'] = self._title_case(rest[0])
                    if len(rest) > 1:
                        # Check for suffix
                        if rest[-1].lower() in ['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv']:
                            name_parts['suffix'] = rest[-1]
                            if len(rest) > 2:
                                name_parts['middle'] = ' '.join(rest[1:-1])
                        else:
                            name_parts['middle'] = ' '.join(rest[1:])
            else:
                # "First [Middle] Last" format
                parts = full.split()
                if len(parts) >= 2:
                    name_parts['first'] = self._title_case(parts[0])
                    # Check for suffix
                    if parts[-1].lower() in ['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv']:
                        name_parts['suffix'] = parts[-1]
                        name_parts['last'] = self._title_case(parts[-2]) if len(parts) > 2 else ''
                        if len(parts) > 3:
                            name_parts['middle'] = ' '.join(parts[1:-2])
                    else:
                        name_parts['last'] = self._title_case(parts[-1])
                        if len(parts) > 2:
                            name_parts['middle'] = ' '.join(parts[1:-1])
                elif len(parts) == 1:
                    name_parts['last'] = self._title_case(parts[0])

        return name_parts

    def _title_case(self, name: str) -> str:
        """Convert name to title case, handling special cases."""
        if not name:
            return ''

        name = name.strip()

        # Handle particles
        particles = ['de', 'van', 'von', 'der', 'den', 'del', 'la', 'le']
        words = name.split()
        result = []

        for i, word in enumerate(words):
            lower_word = word.lower()

            # Keep particles lowercase unless at start
            if i > 0 and lower_word in particles:
                result.append(lower_word)
            # Handle Mc/Mac
            elif lower_word.startswith('mc') and len(word) > 2:
                result.append('Mc' + word[2:].capitalize())
            elif lower_word.startswith('mac') and len(word) > 3:
                result.append('Mac' + word[3:].capitalize())
            # Handle O'
            elif "'" in word and word.lower().startswith("o'"):
                result.append("O'" + word[2:].capitalize())
            else:
                result.append(word.capitalize())

        return ' '.join(result)

    def _parse_address(self, row: Dict) -> Dict[str, str]:
        """Parse address components from row data."""
        address = {
            'street': '',
            'city': '',
            'state': '',
            'postal_code': '',
            'country': 'US'
        }

        # Try explicit components first
        if row.get('street'):
            address['street'] = row['street'].strip()
        if row.get('city'):
            address['city'] = self._title_case(row['city'])
        if row.get('state'):
            address['state'] = self._normalize_state(row['state'])
        if row.get('postal_code'):
            address['postal_code'] = row['postal_code'].strip()
        if row.get('country'):
            address['country'] = row['country'].strip().upper()

        # If no components but have single address field
        if not any([address['street'], address['city']]) and row.get('address'):
            parsed = self._parse_single_address(row['address'])
            if parsed:
                address.update(parsed)

        return address

    def _parse_single_address(self, addr_str: str) -> Optional[Dict[str, str]]:
        """Parse single address string into components."""
        if not addr_str:
            return None

        addr_str = addr_str.strip()

        # Try usaddress first if available
        if HAS_USADDRESS:
            try:
                tagged, addr_type = usaddress.tag(addr_str)

                result = {
                    'street': '',
                    'city': '',
                    'state': '',
                    'postal_code': '',
                    'country': 'US'
                }

                # Build street address
                street_parts = []
                for key in ['AddressNumber', 'StreetNamePreDirectional', 'StreetName',
                           'StreetNamePostType', 'StreetNamePostDirectional']:
                    if key in tagged:
                        street_parts.append(tagged[key])
                if 'OccupancyType' in tagged and 'OccupancyIdentifier' in tagged:
                    street_parts.append(f"{tagged['OccupancyType']} {tagged['OccupancyIdentifier']}")

                result['street'] = ' '.join(street_parts)
                result['city'] = self._title_case(tagged.get('PlaceName', ''))
                result['state'] = self._normalize_state(tagged.get('StateName', ''))
                result['postal_code'] = tagged.get('ZipCode', '')

                return result
            except Exception as e:
                self.logger.debug(f"usaddress parsing failed: {e}")
                self.stats['address_parse_warnings'] += 1

        # Fallback regex parsing
        # Pattern: Street, City, State ZIP
        pattern = r'^(.+?),\s*([^,]+),\s*([A-Z]{2}|\w+)\s+(\d{5}(?:-\d{4})?|\w+)$'
        match = re.match(pattern, addr_str, re.IGNORECASE)

        if match:
            return {
                'street': match.group(1).strip(),
                'city': self._title_case(match.group(2).strip()),
                'state': self._normalize_state(match.group(3).strip()),
                'postal_code': match.group(4).strip(),
                'country': 'US'
            }

        # Try simpler pattern without commas
        pattern2 = r'^(.+?)\s+([A-Z]{2}|\w+)\s+(\d{5}(?:-\d{4})?|\w+)$'
        match = re.match(pattern2, addr_str, re.IGNORECASE)

        if match:
            # Split the first part to guess street vs city
            parts = match.group(1).rsplit(None, 1)
            if len(parts) == 2:
                return {
                    'street': parts[0].strip(),
                    'city': self._title_case(parts[1].strip()),
                    'state': self._normalize_state(match.group(2).strip()),
                    'postal_code': match.group(3).strip(),
                    'country': 'US'
                }

        self.stats['address_parse_warnings'] += 1
        return None

    def _normalize_state(self, state: str) -> str:
        """Normalize state to 2-letter code if US state."""
        if not state:
            return ''

        state = state.strip().upper()

        # Already 2-letter code
        if len(state) == 2:
            return state

        # Try to convert full name to abbreviation
        state_lower = state.lower()
        if state_lower in self.US_STATES:
            return self.US_STATES[state_lower]

        # Return as-is if not recognized
        return state

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number."""
        if not phone:
            return ''

        # Keep digits and common phone symbols
        phone = re.sub(r'[^\d\+\-\(\)\s\.]', '', phone)
        # Collapse multiple spaces
        phone = re.sub(r'\s+', ' ', phone)
        return phone.strip()

    def _check_inclusion(self, full_name: str, last_name: str) -> bool:
        """Check if name matches inclusion filter."""
        if not self.inclusion_names:
            return True  # No filter means include all

        full_lower = full_name.lower()
        last_lower = last_name.lower()

        for filter_name in self.inclusion_names:
            # Check exact full name match
            if full_lower == filter_name:
                return True

            # Check "Last, First" format
            if ',' in filter_name:
                parts = filter_name.split(',', 1)
                filter_last = parts[0].strip()
                filter_first = parts[1].strip() if len(parts) > 1 else ''

                if last_lower == filter_last:
                    if not filter_first:  # Just last name
                        return True
                    if filter_first in full_lower:
                        return True

            # Check if filter is just a last name
            if ' ' not in filter_name and last_lower == filter_name:
                return True

            # Check "First Last" format
            if filter_name == full_lower:
                return True

        return False

    def _check_exclusion(self, full_name: str) -> bool:
        """Check if name contains excluded tokens."""
        if not full_name:
            return False

        name_lower = full_name.lower()

        for token in self.exclusion_names:
            if token in name_lower:
                return True

        return False

    def _create_pdf(self, person_data: Dict, output_path: Path):
        """Create interactive fillable PDF with person data."""
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Contact Packet — {person_data['full_name']}")

        # Create form
        form = c.acroForm

        # Define fields with labels and positions
        y_pos = height - 100
        field_height = 20
        field_spacing = 35
        label_x = 50
        field_x = 180
        field_width = 300

        fields = [
            ('Full Name:', 'full_name', person_data['full_name']),
            ('First Name:', 'first_name', person_data['name']['first']),
            ('Middle Name:', 'middle_name', person_data['name']['middle']),
            ('Last Name:', 'last_name', person_data['name']['last']),
            ('Suffix:', 'suffix', person_data['name']['suffix']),
            ('Company:', 'company', person_data['company']),
            ('Email:', 'email', person_data['email']),
            ('Phone:', 'phone', person_data['phone']),
            ('System ID:', 'system_id', person_data['system_id']),
            ('Street:', 'street', person_data['address']['street']),
            ('City:', 'city', person_data['address']['city']),
            ('State:', 'state', person_data['address']['state']),
            ('Postal Code:', 'postal_code', person_data['address']['postal_code']),
            ('Country:', 'country', person_data['address']['country'])
        ]

        # Add text fields
        c.setFont("Helvetica", 10)
        for label, field_name, value in fields:
            c.drawString(label_x, y_pos, label)

            form.textfield(
                name=field_name,
                tooltip=field_name,
                x=field_x,
                y=y_pos - 15,
                borderStyle='inset',
                width=field_width,
                height=field_height,
                textColor=black,
                fillColor=None,
                borderColor=black,
                forceBorder=True,
                relative=False,
                value=value or ''
            )

            y_pos -= field_spacing

        # Add checkboxes
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(label_x, y_pos, "Status:")

        y_pos -= 30
        c.setFont("Helvetica", 10)

        checkboxes = [
            ('Verified Contact', 'verified_contact'),
            ('Mailed Packet', 'mailed_packet'),
            ('Follow-up Done', 'followup_done')
        ]

        for label, field_name in checkboxes:
            c.drawString(label_x + 30, y_pos, label)

            form.checkbox(
                name=field_name,
                tooltip=field_name,
                x=label_x,
                y=y_pos - 3,
                size=15,
                checked=False,
                borderColor=black,
                fillColor=None,
                textColor=black,
                forceBorder=True
            )

            y_pos -= 25

        # Add notes field
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(label_x, y_pos, "Notes:")

        y_pos -= 20
        # Using textfield without multiline parameter (not supported in this version)
        form.textfield(
            name='notes',
            tooltip='Additional notes',
            x=label_x,
            y=y_pos - 80,
            borderStyle='inset',
            width=width - 100,
            height=80,
            textColor=black,
            fillColor=None,
            borderColor=black,
            forceBorder=True,
            relative=False,
            value=''
        )

        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(label_x, 30, f"Generated: {datetime.now().isoformat()}")

        c.save()

    def process_row(self, row_num: int, row: pd.Series, original_row: Dict) -> Optional[Dict]:
        """Process a single CSV row."""
        # Normalize column names and create working dict
        working = {}
        for col, val in row.items():
            if pd.notna(val):
                normalized = self._normalize_column_name(str(col))
                working[normalized] = str(val).strip()

        # Parse name
        name_parts = self._parse_name(working)

        # Build full name
        full_name_parts = []
        if name_parts['first']:
            full_name_parts.append(name_parts['first'])
        if name_parts['middle']:
            full_name_parts.append(name_parts['middle'])
        if name_parts['last']:
            full_name_parts.append(name_parts['last'])
        if name_parts['suffix']:
            full_name_parts.append(name_parts['suffix'])

        full_name = ' '.join(full_name_parts)

        if not full_name:
            self.logger.warning(f"Row {row_num}: No name found, skipping")
            self.stats['skipped_no_name'] += 1
            return None

        # Check exclusion first
        if self._check_exclusion(full_name):
            self.logger.info(f"Row {row_num}: {full_name} - Excluded by denylist")
            self.stats['excluded_denylist'] += 1
            return None

        # Check inclusion
        if not self._check_inclusion(full_name, name_parts['last']):
            self.logger.debug(f"Row {row_num}: {full_name} - Not in inclusion list")
            return None

        self.stats['matched_inclusion'] += 1

        # Parse address
        address = self._parse_address(working)

        # Build normalized record
        person_data = {
            'full_name': full_name,
            'name': name_parts,
            'company': working.get('company', ''),
            'email': working.get('email', '').lower(),
            'phone': self._normalize_phone(working.get('phone', '')),
            'system_id': working.get('system_id', ''),
            'address': address,
            'source': {
                'csv_path': str(self.csv_path),
                'row_number': row_num,
                'raw': original_row
            }
        }

        return person_data

    def write_person_artifacts(self, person_data: Dict, original_row: pd.DataFrame):
        """Write all artifacts for a person."""
        slug = slugify(person_data['full_name'], lowercase=True)
        person_dir = self.selected_people_dir / slug
        person_dir.mkdir(parents=True, exist_ok=True)

        # Write data.json
        json_path = person_dir / 'data.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(person_data, f, indent=2, ensure_ascii=False)

        # Write source_row.csv
        csv_path = person_dir / 'source_row.csv'
        original_row.to_csv(csv_path, index=False)

        # Write address.txt
        addr_path = person_dir / 'address.txt'
        addr_lines = []
        addr_lines.append(person_data['full_name'])
        if person_data['company']:
            addr_lines.append(person_data['company'])
        if person_data['address']['street']:
            addr_lines.append(person_data['address']['street'])
        city_state_zip = []
        if person_data['address']['city']:
            city_state_zip.append(person_data['address']['city'])
        if person_data['address']['state']:
            city_state_zip.append(person_data['address']['state'])
        if person_data['address']['postal_code']:
            city_state_zip.append(person_data['address']['postal_code'])
        if city_state_zip:
            addr_lines.append(' '.join(city_state_zip))
        if person_data['address']['country'] and person_data['address']['country'] != 'US':
            addr_lines.append(person_data['address']['country'])
        addr_lines.append(f"System ID: {person_data['system_id']}")

        with open(addr_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(addr_lines))

        # Write contact.vcf
        vcf_path = person_dir / 'contact.vcf'
        vcf_lines = []
        vcf_lines.append('BEGIN:VCARD')
        vcf_lines.append('VERSION:3.0')

        # Name
        name_parts = [
            person_data['name']['last'],
            person_data['name']['first'],
            person_data['name']['middle'],
            '',  # Additional names
            person_data['name']['suffix']
        ]
        vcf_lines.append(f"N:{';'.join(name_parts)}")
        vcf_lines.append(f"FN:{person_data['full_name']}")

        # Organization
        if person_data['company']:
            vcf_lines.append(f"ORG:{person_data['company']}")

        # Email
        if person_data['email']:
            vcf_lines.append(f"EMAIL:{person_data['email']}")

        # Phone
        if person_data['phone']:
            vcf_lines.append(f"TEL:{person_data['phone']}")

        # Address
        addr_parts = [
            '',  # PO Box
            '',  # Extended address
            person_data['address']['street'],
            person_data['address']['city'],
            person_data['address']['state'],
            person_data['address']['postal_code'],
            person_data['address']['country']
        ]
        vcf_lines.append(f"ADR:;;{';'.join(addr_parts)}")

        # Note with System ID
        vcf_lines.append(f"NOTE:System ID: {person_data['system_id']}")

        vcf_lines.append('END:VCARD')

        with open(vcf_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(vcf_lines))

        # Write README.md
        readme_path = person_dir / 'README.md'
        readme_lines = []
        readme_lines.append(f"# {person_data['full_name']}")
        readme_lines.append('')
        readme_lines.append('## Summary')
        readme_lines.append('')
        if person_data['company']:
            readme_lines.append(f"- **Company:** {person_data['company']}")
        if person_data['email']:
            readme_lines.append(f"- **Email:** {person_data['email']}")
        if person_data['phone']:
            readme_lines.append(f"- **Phone:** {person_data['phone']}")
        if person_data['system_id']:
            readme_lines.append(f"- **System ID:** {person_data['system_id']}")

        readme_lines.append('')
        readme_lines.append('## Address')
        readme_lines.append('')
        readme_lines.append('```')
        if person_data['address']['street']:
            readme_lines.append(person_data['address']['street'])
        city_state = []
        if person_data['address']['city']:
            city_state.append(person_data['address']['city'])
        if person_data['address']['state']:
            city_state.append(person_data['address']['state'])
        if person_data['address']['postal_code']:
            city_state.append(person_data['address']['postal_code'])
        if city_state:
            readme_lines.append(' '.join(city_state))
        if person_data['address']['country'] and person_data['address']['country'] != 'US':
            readme_lines.append(person_data['address']['country'])
        readme_lines.append('```')

        readme_lines.append('')
        readme_lines.append('## Details')
        readme_lines.append('')
        readme_lines.append('| Field | Value |')
        readme_lines.append('|-------|-------|')
        readme_lines.append(f"| Full Name | {person_data['full_name']} |")
        readme_lines.append(f"| First Name | {person_data['name']['first']} |")
        readme_lines.append(f"| Middle Name | {person_data['name']['middle']} |")
        readme_lines.append(f"| Last Name | {person_data['name']['last']} |")
        readme_lines.append(f"| Suffix | {person_data['name']['suffix']} |")
        readme_lines.append(f"| Company | {person_data['company']} |")
        readme_lines.append(f"| Email | {person_data['email']} |")
        readme_lines.append(f"| Phone | {person_data['phone']} |")
        readme_lines.append(f"| System ID | {person_data['system_id']} |")
        readme_lines.append(f"| Street | {person_data['address']['street']} |")
        readme_lines.append(f"| City | {person_data['address']['city']} |")
        readme_lines.append(f"| State | {person_data['address']['state']} |")
        readme_lines.append(f"| Postal Code | {person_data['address']['postal_code']} |")
        readme_lines.append(f"| Country | {person_data['address']['country']} |")

        readme_lines.append('')
        readme_lines.append(f"*Generated: {datetime.now().isoformat()}*")

        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(readme_lines))

        # Create interactive PDF
        pdf_path = person_dir / 'person.pdf'
        self._create_pdf(person_data, pdf_path)

        # Add to index
        index_entry = {
            'slug': slug,
            'full_name': person_data['full_name'],
            'system_id': person_data['system_id'],
            'email': person_data['email'],
            'phone': person_data['phone'],
            'city': person_data['address']['city'],
            'state': person_data['address']['state'],
            'postal_code': person_data['address']['postal_code'],
            'path': str(person_dir.relative_to(self.output_dir)),
            'timestamp': datetime.now().isoformat()
        }
        self.index_data.append(index_entry)

        self.stats['exported'] += 1
        self.logger.info(f"Exported: {person_data['full_name']} -> {person_dir}")

    def write_indexes(self):
        """Write index files."""
        # Write JSON index
        json_index = self.output_dir / 'index.json'
        with open(json_index, 'w', encoding='utf-8') as f:
            json.dump(self.index_data, f, indent=2, ensure_ascii=False)

        # Write CSV index
        csv_index = self.output_dir / 'index.csv'
        if self.index_data:
            df = pd.DataFrame(self.index_data)
            df.to_csv(csv_index, index=False)
        else:
            # Write empty CSV with headers
            with open(csv_index, 'w') as f:
                f.write('slug,full_name,system_id,email,phone,city,state,postal_code,path,timestamp\n')

    def process(self):
        """Main processing function."""
        if not self.csv_path.exists():
            self.logger.error(f"CSV file not found: {self.csv_path}")
            return False

        # Read CSV
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8', dtype=str, keep_default_na=False)
        except Exception as e:
            self.logger.error(f"Failed to read CSV: {e}")
            return False

        self.stats['total_rows'] = len(df)
        self.logger.info(f"Processing {self.stats['total_rows']} rows from {self.csv_path}")

        # Process each row
        for idx, row in df.iterrows():
            row_num = idx + 2  # CSV row number (1-based, plus header)
            original_row = row.to_dict()

            person_data = self.process_row(row_num, row, original_row)
            if person_data:
                # Create single-row DataFrame for source_row.csv
                row_df = pd.DataFrame([original_row])
                self.write_person_artifacts(person_data, row_df)

        # Write indexes
        self.write_indexes()

        # Write summary to log
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING COMPLETE")
        self.logger.info(f"Total rows: {self.stats['total_rows']}")
        self.logger.info(f"Matched inclusion filter: {self.stats['matched_inclusion']}")
        self.logger.info(f"Excluded by denylist: {self.stats['excluded_denylist']}")
        self.logger.info(f"Exported: {self.stats['exported']}")
        self.logger.info(f"Skipped (no name): {self.stats['skipped_no_name']}")
        self.logger.info(f"Address parse warnings: {self.stats['address_parse_warnings']}")
        self.logger.info(f"Index files: {self.output_dir}/index.json, {self.output_dir}/index.csv")
        self.logger.info("=" * 60)

        # Print console summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total rows processed: {self.stats['total_rows']}")
        print(f"Matched inclusion filter: {self.stats['matched_inclusion']}")
        print(f"Excluded by denylist: {self.stats['excluded_denylist']}")
        print(f"Successfully exported: {self.stats['exported']}")
        print(f"Skipped (no name): {self.stats['skipped_no_name']}")
        print(f"Address parse warnings: {self.stats['address_parse_warnings']}")
        print(f"\nOutput index: {self.output_dir}/index.json")
        print(f"Output index: {self.output_dir}/index.csv")
        print(f"Log file: {self.log_file}")
        print("=" * 60)

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Process CSV contacts and create organized person folders with interactive PDFs'
    )
    parser.add_argument('--csv', required=True, help='Path to input CSV file')
    parser.add_argument('--names', required=True, help='Path to names filter file')
    parser.add_argument('--out', default='output', help='Output directory (default: output)')

    args = parser.parse_args()

    processor = PersonProcessor(args.csv, args.names, args.out)
    success = processor.process()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()