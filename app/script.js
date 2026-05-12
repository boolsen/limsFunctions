const statusElement = document.getElementById('status');
const resultsElement = document.getElementById('results');
const form = document.getElementById('search-form');
const queryInput = document.getElementById('query');

let functions = [];
let functionMap = new Map();

function formatSection(title, text) {
  if (!text) return '';
  return `<section><h3>${title}</h3><pre>${escapeHtml(text)}</pre></section>`;
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderFunction(func) {
  const meta = func.group_name ? `Group: ${escapeHtml(func.group_name)}` : '';
  return `
    <article class="result-card">
      <h2>${escapeHtml(func.name)}</h2>
      <div class="meta">${meta}</div>
      ${formatSection('Purpose', func.purpose)}
      ${formatSection('Syntax', func.syntax)}
      ${formatSection('Comments', func.comments)}
      ${formatSection('Example', func.example)}
      ${formatSection('Returns', func.returns)}
    </article>
  `;
}

function setStatus(text) {
  statusElement.textContent = text;
}

function showResults(items) {
  if (!items.length) {
    resultsElement.innerHTML = '<div class="no-results">No functions found. Try a different name or keyword.</div>';
    return;
  }

  resultsElement.innerHTML = items.map(renderFunction).join('');
}

function searchFunctions(query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    setStatus('Enter a function name or keyword above to search.');
    resultsElement.innerHTML = '';
    return;
  }

  // Exact name search first
  if (functionMap.has(normalized)) {
    setStatus(`Exact match found for "${query}".`);
    showResults([functionMap.get(normalized)]);
    return;
  }

  const matches = functions.filter((func) => {
    const haystack = [
      func.name,
      func.group_name || '',
      func.purpose || '',
      func.syntax || '',
      func.comments || '',
      func.example || '',
      func.returns || '',
    ]
      .join(' ')
      .toLowerCase();
    return haystack.includes(normalized);
  });

  setStatus(`${matches.length} function${matches.length === 1 ? '' : 's'} found for "${query}".`);
  showResults(matches);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  searchFunctions(queryInput.value);
});

window.addEventListener('load', async () => {
  try {
    const response = await fetch('functions.json');
    if (!response.ok) {
      throw new Error(`Failed to load data: ${response.statusText}`);
    }

    functions = await response.json();
    functions.forEach((func) => {
      functionMap.set(func.name.toLowerCase(), func);
    });

    setStatus('Loaded function definitions. Search by name or keyword.');
  } catch (error) {
    setStatus('Unable to load function data.');
    resultsElement.innerHTML = `<div class="no-results">${escapeHtml(error.message)}</div>`;
  }
});
