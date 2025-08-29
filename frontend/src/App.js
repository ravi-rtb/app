import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [locoNo, setLocoNo] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Search for loco suggestions
  const handleLocoSearch = async (value) => {
    if (value.length >= 3) {
      try {
        const response = await axios.get(`${API}/search/${value}`);
        setSuggestions(response.data.suggestions);
        setShowSuggestions(true);
      } catch (err) {
        setSuggestions([]);
      }
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  // Handle input change
  const handleInputChange = (e) => {
    const value = e.target.value;
    setLocoNo(value);
    handleLocoSearch(value);
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion) => {
    setLocoNo(suggestion);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  // Fetch loco summary
  const fetchLocoSummary = async () => {
    if (!locoNo.trim()) {
      setError('Please enter a loco number');
      return;
    }

    setLoading(true);
    setError('');
    setSearchResults(null);

    try {
      const response = await axios.get(`${API}/loco/${locoNo.trim()}`);
      setSearchResults(response.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`No data found for loco number: ${locoNo}`);
      } else {
        setError('Failed to fetch loco data. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      setShowSuggestions(false);
      fetchLocoSummary();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Locomotive Data Summary
          </h1>
          <p className="text-gray-600">
            Search for locomotive details, schedules, and failure reports
          </p>
        </div>

        {/* Search Section */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <input
                type="text"
                value={locoNo}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder="Enter Loco Number (e.g., 27865)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                autoComplete="off"
              />
              
              {/* Suggestions dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-10 w-full bg-white border border-gray-300 rounded-lg mt-1 max-h-48 overflow-y-auto shadow-lg">
                  {suggestions.map((suggestion, index) => (
                    <div
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="px-4 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                    >
                      {suggestion}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <button
              onClick={fetchLocoSummary}
              disabled={loading}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600">{error}</p>
            </div>
          )}
        </div>

        {/* Results Section */}
        {searchResults && (
          <div className="space-y-8">
            {/* Loco Details Table */}
            {searchResults.details && searchResults.details.length > 0 && (
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="bg-gray-50 px-6 py-4 border-b">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Loco Details - {searchResults.loco_no}
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <tbody>
                      {searchResults.details.map((detail, index) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-6 py-4 font-medium text-gray-700 border-r border-gray-200 w-1/3">
                            {detail.field}
                          </td>
                          <td className="px-6 py-4 text-gray-900">
                            {detail.value}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Loco Schedules */}
            {searchResults.schedules && searchResults.schedules.length > 0 && (
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="bg-gray-50 px-6 py-4 border-b">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Loco Schedules
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Incoming Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Schedule
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Outgoing Date
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {searchResults.schedules.map((schedule, index) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {schedule.incoming_date || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {schedule.sch || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {schedule.outgoing_date || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Traction Failures */}
            {searchResults.failures && searchResults.failures.length > 0 && (
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="bg-gray-50 px-6 py-4 border-b">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Traction Failures
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date Failed
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          ICMS/Message
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Loco No.
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          MU with
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Division
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Railway
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Brief Message
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Cause of Failure
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Component
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          System
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {searchResults.failures.map((failure, index) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                            {failure.date_failed || '-'}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={failure.icms_message}>
                            {failure.icms_message || '-'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                            {failure.loco_no || '-'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                            {failure.mu_with || '-'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                            {failure.div || '-'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                            {failure.rly || '-'}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={failure.brief_message}>
                            {failure.brief_message || '-'}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={failure.cause_of_failure}>
                            {failure.cause_of_failure || '-'}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={failure.component}>
                            {failure.component || '-'}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title={failure.system}>
                            {failure.system || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* No Data Message */}
            {(!searchResults.details || searchResults.details.length === 0) &&
             (!searchResults.schedules || searchResults.schedules.length === 0) &&
             (!searchResults.failures || searchResults.failures.length === 0) && (
              <div className="bg-white rounded-lg shadow-md p-8 text-center">
                <p className="text-gray-500">No data available for this loco number.</p>
              </div>
            )}

            {/* Last Updated Info */}
            <div className="text-center text-sm text-gray-500">
              Last updated: {new Date(searchResults.last_updated).toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;