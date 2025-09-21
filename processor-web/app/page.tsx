'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import Papa from 'papaparse';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import slugify from 'slugify';
import {
  processRow,
  checkInclusion,
  checkExclusion,
  processPersonData,
  PersonData
} from '@/lib/processor';

interface ProcessingStats {
  totalRows: number;
  matchedInclusion: number;
  excludedDenylist: number;
  exported: number;
  skippedNoName: number;
}

export default function Home() {
  const [csvData, setCsvData] = useState<any[]>([]);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [inclusionNames, setInclusionNames] = useState<string>('Tom Whatley\nNick Mueller\nJerome Mitchell\nKim Munie\nLinda Daniels');
  const [exclusionNames, setExclusionNames] = useState<string>('Claudette');
  const [processing, setProcessing] = useState(false);
  const [stats, setStats] = useState<ProcessingStats | null>(null);
  const [processedPeople, setProcessedPeople] = useState<PersonData[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      Papa.parse(file, {
        complete: (results) => {
          setCsvData(results.data as any[]);
          if (results.data.length > 0) {
            setCsvHeaders(Object.keys(results.data[0]));
          }
        },
        header: true,
        skipEmptyLines: true
      });
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv']
    },
    maxFiles: 1
  });

  const processCSV = async () => {
    if (csvData.length === 0) return;

    setProcessing(true);
    setStats(null);
    setProcessedPeople([]);

    const inclusionList = inclusionNames
      .split('\n')
      .map(n => n.trim())
      .filter(n => n && !n.startsWith('#'));

    const exclusionList = exclusionNames
      .split('\n')
      .map(n => n.trim())
      .filter(n => n && !n.startsWith('#'));

    const newStats: ProcessingStats = {
      totalRows: csvData.length,
      matchedInclusion: 0,
      excludedDenylist: 0,
      exported: 0,
      skippedNoName: 0
    };

    const processed: PersonData[] = [];

    for (let i = 0; i < csvData.length; i++) {
      const row = csvData[i];
      const person = processRow(row, i + 2);

      if (!person) {
        newStats.skippedNoName++;
        continue;
      }

      // Check exclusion
      if (checkExclusion(person.full_name, exclusionList)) {
        newStats.excludedDenylist++;
        continue;
      }

      // Check inclusion
      if (!checkInclusion(person.full_name, person.name.last, inclusionList)) {
        continue;
      }

      newStats.matchedInclusion++;
      newStats.exported++;
      processed.push(person);
    }

    setStats(newStats);
    setProcessedPeople(processed);
    setProcessing(false);
  };

  const downloadAll = async () => {
    if (processedPeople.length === 0) return;

    const zip = new JSZip();

    for (const person of processedPeople) {
      const slug = slugify(person.full_name, { lower: true });
      const folder = zip.folder(`selected_people/${slug}`);

      if (folder) {
        const result = await processPersonData(person);

        // Add files to folder
        folder.file('data.json', result.files.json);
        folder.file('contact.vcf', result.files.vcf);
        folder.file('address.txt', result.files.address);
        folder.file('README.md', result.files.readme);
        folder.file('person.pdf', result.files.pdf);

        // Add source row as CSV
        const csvRow = Papa.unparse([person.source.raw]);
        folder.file('source_row.csv', csvRow);
      }
    }

    // Add index files
    const indexJson = JSON.stringify(
      processedPeople.map(p => ({
        slug: slugify(p.full_name, { lower: true }),
        full_name: p.full_name,
        system_id: p.system_id,
        email: p.email,
        phone: p.phone,
        city: p.address.city,
        state: p.address.state,
        postal_code: p.address.postal_code,
        timestamp: new Date().toISOString()
      })),
      null,
      2
    );
    zip.file('index.json', indexJson);

    const indexCsv = Papa.unparse(
      processedPeople.map(p => ({
        slug: slugify(p.full_name, { lower: true }),
        full_name: p.full_name,
        system_id: p.system_id,
        email: p.email,
        phone: p.phone,
        city: p.address.city,
        state: p.address.state,
        postal_code: p.address.postal_code,
        timestamp: new Date().toISOString()
      }))
    );
    zip.file('index.csv', indexCsv);

    // Generate and download zip
    const blob = await zip.generateAsync({ type: 'blob' });
    saveAs(blob, 'processed_people.zip');
  };

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">CSV Person Processor</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* CSV Upload */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold mb-4">1. Upload CSV</h2>

            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              {csvData.length === 0 ? (
                <div>
                  <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-gray-600">Drop your CSV file here, or click to select</p>
                </div>
              ) : (
                <div className="text-green-600">
                  <svg className="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="font-semibold">CSV Loaded!</p>
                  <p className="text-sm text-gray-600 mt-2">{csvData.length} rows found</p>
                  <p className="text-xs text-gray-500 mt-1">Headers: {csvHeaders.slice(0, 3).join(', ')}{csvHeaders.length > 3 && '...'}</p>
                </div>
              )}
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold mb-4">2. Configure Filters</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Inclusion Names (one per line)
                </label>
                <textarea
                  value={inclusionNames}
                  onChange={(e) => setInclusionNames(e.target.value)}
                  className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Jane Doe&#10;Doe, John&#10;Rodriguez"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Exclusion Names (substring match)
                </label>
                <textarea
                  value={exclusionNames}
                  onChange={(e) => setExclusionNames(e.target.value)}
                  className="w-full h-20 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Claudette"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Process Button */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">3. Process Data</h2>

          <button
            onClick={processCSV}
            disabled={csvData.length === 0 || processing}
            className="w-full sm:w-auto px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {processing ? 'Processing...' : 'Process CSV'}
          </button>

          {/* Stats */}
          {stats && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold text-lg mb-2">Processing Summary</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Total Rows:</span>
                  <span className="ml-2 font-semibold">{stats.totalRows}</span>
                </div>
                <div>
                  <span className="text-gray-600">Matched:</span>
                  <span className="ml-2 font-semibold text-green-600">{stats.matchedInclusion}</span>
                </div>
                <div>
                  <span className="text-gray-600">Excluded:</span>
                  <span className="ml-2 font-semibold text-red-600">{stats.excludedDenylist}</span>
                </div>
                <div>
                  <span className="text-gray-600">Exported:</span>
                  <span className="ml-2 font-semibold text-blue-600">{stats.exported}</span>
                </div>
                <div>
                  <span className="text-gray-600">No Name:</span>
                  <span className="ml-2 font-semibold text-yellow-600">{stats.skippedNoName}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Download Section */}
        {processedPeople.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold mb-4">4. Download Results</h2>

            <div className="space-y-4">
              <button
                onClick={downloadAll}
                className="w-full sm:w-auto px-6 py-3 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 transition-colors"
              >
                Download All ({processedPeople.length} people)
              </button>

              <div className="mt-4">
                <h3 className="font-semibold mb-2">Processed People:</h3>
                <div className="max-h-64 overflow-y-auto border rounded-md">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">City</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">State</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {processedPeople.map((person, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 text-sm text-gray-900">{person.full_name}</td>
                          <td className="px-4 py-2 text-sm text-gray-500">{person.address.city}</td>
                          <td className="px-4 py-2 text-sm text-gray-500">{person.address.state}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}