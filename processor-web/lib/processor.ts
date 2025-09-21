import slugify from 'slugify';
import jsPDF from 'jspdf';

export interface PersonData {
  full_name: string;
  name: {
    first: string;
    middle: string;
    last: string;
    suffix: string;
  };
  company: string;
  email: string;
  phone: string;
  system_id: string;
  address: {
    street: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  source: {
    csv_path: string;
    row_number: number;
    raw: any;
  };
}

export interface ProcessingResult {
  person: PersonData;
  files: {
    pdf: Blob;
    json: string;
    vcf: string;
    address: string;
    readme: string;
  };
}

const US_STATES: Record<string, string> = {
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
};

export function titleCase(name: string): string {
  if (!name) return '';

  const particles = ['de', 'van', 'von', 'der', 'den', 'del', 'la', 'le'];
  const words = name.split(' ');

  return words.map((word, i) => {
    const lower = word.toLowerCase();

    if (i > 0 && particles.includes(lower)) {
      return lower;
    }

    if (lower.startsWith('mc') && word.length > 2) {
      return 'Mc' + word.slice(2).charAt(0).toUpperCase() + word.slice(3).toLowerCase();
    }

    if (lower.startsWith('mac') && word.length > 3) {
      return 'Mac' + word.slice(3).charAt(0).toUpperCase() + word.slice(4).toLowerCase();
    }

    if (word.includes("'") && lower.startsWith("o'")) {
      return "O'" + word.slice(2).charAt(0).toUpperCase() + word.slice(3).toLowerCase();
    }

    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  }).join(' ');
}

export function normalizeState(state: string): string {
  if (!state) return '';

  const trimmed = state.trim().toUpperCase();

  if (trimmed.length === 2) return trimmed;

  const lower = state.toLowerCase().trim();
  return US_STATES[lower] || state.trim();
}

export function parseName(fullName: string): PersonData['name'] {
  const parts = {
    first: '',
    middle: '',
    last: '',
    suffix: ''
  };

  if (!fullName) return parts;

  const suffixes = ['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv'];

  // Check for "Last, First [Middle]" format
  if (fullName.includes(',')) {
    const [lastName, rest] = fullName.split(',', 2);
    parts.last = titleCase(lastName.trim());

    if (rest) {
      const restParts = rest.trim().split(' ');
      if (restParts.length > 0) {
        parts.first = titleCase(restParts[0]);

        if (restParts.length > 1) {
          const lastPart = restParts[restParts.length - 1].toLowerCase();

          if (suffixes.includes(lastPart)) {
            parts.suffix = restParts[restParts.length - 1];
            if (restParts.length > 2) {
              parts.middle = restParts.slice(1, -1).map(p => titleCase(p)).join(' ');
            }
          } else {
            parts.middle = restParts.slice(1).map(p => titleCase(p)).join(' ');
          }
        }
      }
    }
  } else {
    // "First [Middle] Last" format
    const nameParts = fullName.split(' ');

    if (nameParts.length >= 2) {
      parts.first = titleCase(nameParts[0]);

      const lastPart = nameParts[nameParts.length - 1].toLowerCase();

      if (suffixes.includes(lastPart) && nameParts.length > 2) {
        parts.suffix = nameParts[nameParts.length - 1];
        parts.last = titleCase(nameParts[nameParts.length - 2]);

        if (nameParts.length > 3) {
          parts.middle = nameParts.slice(1, -2).map(p => titleCase(p)).join(' ');
        }
      } else {
        parts.last = titleCase(nameParts[nameParts.length - 1]);

        if (nameParts.length > 2) {
          parts.middle = nameParts.slice(1, -1).map(p => titleCase(p)).join(' ');
        }
      }
    } else if (nameParts.length === 1) {
      parts.last = titleCase(nameParts[0]);
    }
  }

  return parts;
}

export function checkInclusion(fullName: string, lastName: string, inclusionNames: string[]): boolean {
  if (inclusionNames.length === 0) return true;

  const fullLower = fullName.toLowerCase();
  const lastLower = lastName.toLowerCase();

  for (const filterName of inclusionNames) {
    const filter = filterName.toLowerCase();

    if (fullLower === filter) return true;

    if (filter.includes(',')) {
      const [filterLast, filterFirst] = filter.split(',', 2).map(s => s.trim());

      if (lastLower === filterLast) {
        if (!filterFirst || fullLower.includes(filterFirst)) {
          return true;
        }
      }
    } else if (!filter.includes(' ') && lastLower === filter) {
      return true;
    }
  }

  return false;
}

export function checkExclusion(fullName: string, exclusionNames: string[]): boolean {
  if (!fullName || exclusionNames.length === 0) return false;

  const nameLower = fullName.toLowerCase();

  for (const token of exclusionNames) {
    if (nameLower.includes(token.toLowerCase())) {
      return true;
    }
  }

  return false;
}

export function createPDF(person: PersonData): Blob {
  const pdf = new jsPDF();

  // Title
  pdf.setFontSize(16);
  pdf.text(`Contact Packet — ${person.full_name}`, 20, 20);

  // Personal Information
  pdf.setFontSize(12);
  let y = 40;

  const fields = [
    ['Full Name:', person.full_name],
    ['First Name:', person.name.first],
    ['Middle Name:', person.name.middle],
    ['Last Name:', person.name.last],
    ['Suffix:', person.name.suffix],
    ['Company:', person.company],
    ['Email:', person.email],
    ['Phone:', person.phone],
    ['System ID:', person.system_id],
    ['Street:', person.address.street],
    ['City:', person.address.city],
    ['State:', person.address.state],
    ['Postal Code:', person.address.postal_code],
    ['Country:', person.address.country]
  ];

  fields.forEach(([label, value]) => {
    pdf.setFont(undefined, 'bold');
    pdf.text(label, 20, y);
    pdf.setFont(undefined, 'normal');
    pdf.text(value || '', 60, y);
    y += 10;
  });

  // Footer
  pdf.setFontSize(8);
  pdf.text(`Generated: ${new Date().toISOString()}`, 20, 280);

  return pdf.output('blob');
}

export function createVCard(person: PersonData): string {
  const lines = [
    'BEGIN:VCARD',
    'VERSION:3.0',
    `N:${person.name.last};${person.name.first};${person.name.middle};;${person.name.suffix}`,
    `FN:${person.full_name}`
  ];

  if (person.company) {
    lines.push(`ORG:${person.company}`);
  }

  if (person.email) {
    lines.push(`EMAIL:${person.email}`);
  }

  if (person.phone) {
    lines.push(`TEL:${person.phone}`);
  }

  const addr = `;;${person.address.street};${person.address.city};${person.address.state};${person.address.postal_code};${person.address.country}`;
  lines.push(`ADR:${addr}`);

  lines.push(`NOTE:System ID: ${person.system_id}`);
  lines.push('END:VCARD');

  return lines.join('\n');
}

export function createAddressLabel(person: PersonData): string {
  const lines = [person.full_name];

  if (person.company) {
    lines.push(person.company);
  }

  if (person.address.street) {
    lines.push(person.address.street);
  }

  const cityStateParts = [];
  if (person.address.city) cityStateParts.push(person.address.city);
  if (person.address.state) cityStateParts.push(person.address.state);
  if (person.address.postal_code) cityStateParts.push(person.address.postal_code);

  if (cityStateParts.length > 0) {
    lines.push(cityStateParts.join(' '));
  }

  if (person.address.country && person.address.country !== 'US') {
    lines.push(person.address.country);
  }

  lines.push(`System ID: ${person.system_id}`);

  return lines.join('\n');
}

export function createReadme(person: PersonData): string {
  const lines = [
    `# ${person.full_name}`,
    '',
    '## Summary',
    ''
  ];

  if (person.company) lines.push(`- **Company:** ${person.company}`);
  if (person.email) lines.push(`- **Email:** ${person.email}`);
  if (person.phone) lines.push(`- **Phone:** ${person.phone}`);
  if (person.system_id) lines.push(`- **System ID:** ${person.system_id}`);

  lines.push('', '## Address', '', '```');

  if (person.address.street) lines.push(person.address.street);

  const cityStateParts = [];
  if (person.address.city) cityStateParts.push(person.address.city);
  if (person.address.state) cityStateParts.push(person.address.state);
  if (person.address.postal_code) cityStateParts.push(person.address.postal_code);

  if (cityStateParts.length > 0) {
    lines.push(cityStateParts.join(' '));
  }

  if (person.address.country && person.address.country !== 'US') {
    lines.push(person.address.country);
  }

  lines.push('```', '', '## Details', '', '| Field | Value |', '|-------|-------|');

  const fields = [
    ['Full Name', person.full_name],
    ['First Name', person.name.first],
    ['Middle Name', person.name.middle],
    ['Last Name', person.name.last],
    ['Suffix', person.name.suffix],
    ['Company', person.company],
    ['Email', person.email],
    ['Phone', person.phone],
    ['System ID', person.system_id],
    ['Street', person.address.street],
    ['City', person.address.city],
    ['State', person.address.state],
    ['Postal Code', person.address.postal_code],
    ['Country', person.address.country]
  ];

  fields.forEach(([label, value]) => {
    lines.push(`| ${label} | ${value} |`);
  });

  lines.push('', `*Generated: ${new Date().toISOString()}*`);

  return lines.join('\n');
}

export function processRow(row: any, rowNum: number): PersonData | null {
  // Map column names
  const fullName = row['System Name'] || row['name'] || row['full_name'] || '';

  if (!fullName) return null;

  const nameParts = parseName(fullName);

  const person: PersonData = {
    full_name: fullName,
    name: nameParts,
    company: row['company'] || row['organization'] || '',
    email: (row['email'] || '').toLowerCase(),
    phone: row['phone'] || '',
    system_id: row['system_id'] || row['id'] || '',
    address: {
      street: row['street'] || row['address'] || '',
      city: titleCase(row['City'] || row['city'] || ''),
      state: normalizeState(row['State/Prov'] || row['state'] || ''),
      postal_code: row['postal_code'] || row['zip'] || '',
      country: (row['country'] || 'US').toUpperCase()
    },
    source: {
      csv_path: 'uploaded.csv',
      row_number: rowNum,
      raw: row
    }
  };

  return person;
}

export async function processPersonData(person: PersonData): Promise<ProcessingResult> {
  const pdf = createPDF(person);
  const json = JSON.stringify(person, null, 2);
  const vcf = createVCard(person);
  const address = createAddressLabel(person);
  const readme = createReadme(person);

  return {
    person,
    files: {
      pdf,
      json,
      vcf,
      address,
      readme
    }
  };
}