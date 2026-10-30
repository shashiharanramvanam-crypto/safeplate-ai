/**
 * Main Controller for SafePlate AI
 */

const API_BASE = '';
let currentProfile = null;
let allProfiles = [];

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  await fetchStatus();
  await loadProfiles();
  await loadPantry();
  setupEventListeners();
}

async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    const data = await res.json();
    const modelPill = document.getElementById('engine-model');
    if (modelPill) modelPill.textContent = data.model;
  } catch (err) {
    console.warn('Status fetch error:', err);
  }
}

async function loadProfiles() {
  try {
    const res = await fetch(`${API_BASE}/api/profiles`);
    allProfiles = await res.json();
    populateProfileSelect();
    if (allProfiles.length > 0) {
      setActiveProfile(allProfiles[0]);
    }
  } catch (err) {
    console.error('Error loading profiles:', err);
  }
}

function populateProfileSelect() {
  const select = document.getElementById('select-friend');
  if (!select) return;
  select.innerHTML = '';
  allProfiles.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.name} (${p.relation})`;
    select.appendChild(opt);
  });
}

function setActiveProfile(profile) {
  currentProfile = profile;
  document.getElementById('select-friend').value = profile.id;
  document.getElementById('prof-avatar').textContent = profile.avatar || '🥑';
  document.getElementById('prof-name').textContent = profile.name;
  document.getElementById('prof-relation').textContent = profile.relation;
  document.getElementById('prof-severity').textContent = profile.severity;
  document.getElementById('prof-notes').textContent = profile.notes || '';

  // Render allergy tags
  const tagsContainer = document.getElementById('allergy-tags');
  tagsContainer.innerHTML = '';
  (profile.allergies || []).forEach(alg => {
    const chip = document.createElement('span');
    chip.className = 'tag-allergy';
    chip.textContent = alg.replace('_', ' ').toUpperCase();
    tagsContainer.appendChild(chip);
  });
}

async function loadPantry() {
  try {
    const res = await fetch(`${API_BASE}/api/pantry`);
    const items = await res.json();
    renderPantry(items);
  } catch (err) {
    console.error('Pantry load error:', err);
  }
}

function renderPantry(items) {
  const grid = document.getElementById('pantry-grid');
  if (!grid) return;
  grid.innerHTML = '';

  items.forEach(it => {
    const card = document.createElement('div');
    card.className = 'pantry-card';
    card.innerHTML = `
      <div>
        <strong>${it.name}</strong>
        <div style="font-size:0.75rem;color:#6b7280;">${it.notes || it.category}</div>
      </div>
      <button class="btn-del" data-id="${it.id}" style="background:none;border:none;color:#ef4444;cursor:pointer;">✕</button>
    `;
    card.querySelector('.btn-del').addEventListener('click', () => deletePantryItem(it.id));
    grid.appendChild(card);
  });
}

async function deletePantryItem(itemId) {
  try {
    await fetch(`${API_BASE}/api/pantry/${itemId}`, { method: 'DELETE' });
    loadPantry();
  } catch (err) {
    console.error('Error deleting item:', err);
  }
}

function setupEventListeners() {
  // Friend Profile Change
  document.getElementById('select-friend').addEventListener('change', (e) => {
    const found = allProfiles.find(p => p.id === e.target.value);
    if (found) setActiveProfile(found);
  });

  // Ingredient Scanner Form
  const scanForm = document.getElementById('form-scan');
  const scanResult = document.getElementById('scan-result');
  if (scanForm) {
    scanForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!currentProfile) return;
      const text = document.getElementById('in-scan-text').value.trim();
      if (!text) return;

      scanResult.style.display = 'block';
      scanResult.className = 'scan-result-card';
      scanResult.innerHTML = `<em>Scanning ingredients against ${currentProfile.name}'s allergy taxonomy...</em>`;

      try {
        const res = await fetch(`${API_BASE}/api/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ingredients: text,
            allergies: currentProfile.allergies || []
          })
        });
        const data = await res.json();

        if (data.safe) {
          scanResult.className = 'scan-result-card scan-result-safe';
          scanResult.innerHTML = `
            <strong>✅ 100% SAFE FOR ${currentProfile.name.toUpperCase()}</strong><br>
            No flagged allergens or hidden cross-reactive derivatives detected.
          `;
        } else {
          scanResult.className = 'scan-result-card scan-result-danger';
          let hazardsHtml = data.flagged_hazards.map(h => `
            <li style="margin-top:6px;">
              <strong>Trigger Found:</strong> '${h.matched_trigger}' (${h.allergen_group})<br>
              ${h.safe_substitutes ? `<span style="color:#047857;">↳ Safe Substitution: ${h.safe_substitutes.join(', ')}</span>` : ''}
            </li>
          `).join('');

          scanResult.innerHTML = `
            <strong>🚨 ALLERGEN HAZARD DETECTED (${data.hazard_count} trigger(s)):</strong>
            <ul style="padding-left:18px;margin-top:6px;">${hazardsHtml}</ul>
          `;
        }
      } catch (err) {
        scanResult.textContent = "Error scanning ingredients.";
      }
    });
  }

  // Safe Recipe Generator Button
  const btnGenRecipe = document.getElementById('btn-generate-recipe');
  const recipeBox = document.getElementById('recipe-box');
  if (btnGenRecipe) {
    btnGenRecipe.addEventListener('click', async () => {
      if (!currentProfile) return;
      btnGenRecipe.disabled = true;
      btnGenRecipe.innerHTML = `<em>🥑 Designing meal with local Gemma 2...</em>`;
      recipeBox.style.display = 'block';
      recipeBox.innerHTML = `<em>Consulting Gemma 2 for a certified safe recipe for ${currentProfile.name}...</em>`;

      try {
        const res = await fetch(`${API_BASE}/api/recipe/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile_id: currentProfile.id })
        });
        const data = await res.json();
        recipeBox.innerHTML = `
          <div style="font-weight:bold;color:#2d5a4c;margin-bottom:8px;">✦ SafePlate Recipe (${data.model})</div>
          <div>${formatMarkdown(data.recipe)}</div>
          <div style="font-size:0.75rem;color:#6b7280;margin-top:10px;">${data.guarantee}</div>
        `;
      } catch (err) {
        recipeBox.textContent = "Failed to generate recipe.";
      } finally {
        btnGenRecipe.disabled = false;
        btnGenRecipe.innerHTML = `🥑 Cook a Safe Meal with Gemma 2`;
      }
    });
  }

  // Dining Card Generator Button
  const btnDiningCard = document.getElementById('btn-dining-card');
  if (btnDiningCard) {
    btnDiningCard.addEventListener('click', async () => {
      if (!currentProfile) return;
      btnDiningCard.disabled = true;
      btnDiningCard.innerHTML = `<em>Writing server card...</em>`;

      try {
        const res = await fetch(`${API_BASE}/api/dining-card`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile_id: currentProfile.id })
        });
        const data = await res.json();
        recipeBox.style.display = 'block';
        recipeBox.innerHTML = `
          <div style="font-weight:bold;color:#b45309;margin-bottom:8px;">✦ Emergency Server Allergy Notice</div>
          <div>${formatMarkdown(data.card_text)}</div>
        `;
      } catch (err) {
        alert("Failed to author dining card.");
      } finally {
        btnDiningCard.disabled = false;
        btnDiningCard.innerHTML = `📋 Server Allergy Card`;
      }
    });
  }

  // 1-Click Export Fridge Guide
  const btnExport = document.getElementById('btn-export-card');
  if (btnExport) {
    btnExport.addEventListener('click', () => {
      if (!currentProfile) return;
      window.open(`/api/export/${currentProfile.id}`, '_blank');
    });
  }

  // New Pantry Item Modal
  const btnAddPantry = document.getElementById('btn-add-pantry');
  const modalPantry = document.getElementById('modal-pantry');
  const closePantry = document.getElementById('close-modal-pantry');
  const formPantry = document.getElementById('form-pantry');

  if (btnAddPantry && modalPantry) {
    btnAddPantry.addEventListener('click', () => modalPantry.style.display = 'flex');
    closePantry.addEventListener('click', () => modalPantry.style.display = 'none');

    formPantry.addEventListener('submit', async (e) => {
      e.preventDefault();
      const newItem = {
        name: document.getElementById('in-pantry-name').value,
        category: document.getElementById('in-pantry-cat').value,
        notes: document.getElementById('in-pantry-notes').value
      };
      await fetch(`${API_BASE}/api/pantry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newItem)
      });
      loadPantry();
      modalPantry.style.display = 'none';
      formPantry.reset();
    });
  }

  // Why Open AI Modal
  const btnWhy = document.getElementById('btn-why-open');
  const modalWhy = document.getElementById('modal-why-open');
  const closeWhy = document.getElementById('close-modal-why');

  if (btnWhy && modalWhy) {
    btnWhy.addEventListener('click', () => modalWhy.style.display = 'flex');
    closeWhy.addEventListener('click', () => modalWhy.style.display = 'none');
  }
}

function formatMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}
