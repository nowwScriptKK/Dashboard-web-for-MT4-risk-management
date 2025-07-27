// === Variables globales ===
let inPercent = false;
let rawData = null;
let tradesCache = [];
let commentsCache = {};
let isEditing = false;
let configCache = null;
let capitalReference = 0;
let capitalChart = null;
let symbolsColors = {};
let initialCapital = 0;
let closedTrades = [];
let currentPage = 0;
const pageSize = 10;

// === Fonctions utilitaires ===
function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/[&<>"]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[m]);
}

function showConfigMessage(message, isError = false) {
  const configStatus = document.getElementById("configStatus");
  configStatus.textContent = message;
  configStatus.classList.toggle("status-error", isError);
  configStatus.classList.toggle("status-success", !isError);
  if (!message) configStatus.classList.remove("status-error", "status-success");
}

function fmt(val, capital) {
  return inPercent ? `${((val / capital) * 100).toFixed(1)}%` : `${val.toFixed(2)} €`;
}

function calcRR(trade) {
  const { open_price: open, sl, tp, type } = trade;
  if (sl == null || tp == null || open == null || open === sl) return null;
  return type === 1 ? ((tp - open) / (open - sl)).toFixed(2) : ((open - tp) / (sl - open)).toFixed(2);
}

// === Affichage des infos du compte ===
function updateDisplay(data) {
  rawData = data;
  const acc = data.data.account;
  const { balance, equity, free_margin, margin, leverage, number, currency } = acc;

  const base = capitalReference || balance || 1;
  document.getElementById("balance").textContent = inPercent ? `${((balance / base) * 100).toFixed(1)}%` : `${balance.toFixed(2)} ${currency}`;
  document.getElementById("equity").textContent = inPercent ? `${((equity / balance) * 100).toFixed(1)}%` : `${equity} ${currency}`;
  document.getElementById("freeMargin").textContent = inPercent ? `${((free_margin / balance) * 100).toFixed(1)}%` : `${free_margin} ${currency}`;
  document.getElementById("margin").textContent = inPercent ? `${((margin / balance) * 100).toFixed(1)}%` : `${margin} ${currency}`;
  document.getElementById("leverage").textContent = leverage;
  document.getElementById("accountNumber").textContent = number;
  document.getElementById("currency").textContent = currency;
  document.getElementById("accountName").textContent = acc.name || "Nom inconnu";
}

// === Récupération des données ===
async function fetchData() {
  try {
    const res = await fetch('http://localhost:80/api/tradesDB');
    if (!res.ok) throw new Error('Erreur réseau');
    const data = await res.json();

    updateDisplay(data);
    tradesCache = (data.data.open_trades || []).filter(t => t.symbol);
    renderTrades();

    if (!configCache) {
      await loadConfig();
    }
  } catch (err) {
    console.error("Erreur API:", err);
    document.getElementById("accountName").textContent = "Erreur API";
  }
}

async function fetchComments() {
  try {
    const res = await fetch('http://localhost:80/api/commentsDB');
    if (!res.ok) throw new Error('Erreur réseau (comments)');
    const data = await res.json();
    
    if (data.status !== 'success') {
      throw new Error(data.message || 'Erreur inconnue');
    }
    
    // Formatage des données pour correspondre à votre structure
    commentsCache = {};
    Object.entries(data.data).forEach(([ticket, comment]) => {
      commentsCache[ticket] = {
        text: comment.text || '',
        satisfaction: comment.satisfaction || 0,
        confiance: comment.confiance || 0,
        attente: comment.attente || '',
        date: comment.date || '',
        status: comment.status || 'unread',
        printer: comment.printer || '',
        created_at: comment.created_at || '',
        updated_at: comment.updated_at || ''
      };
    });
    
    renderTrades();
    renderClosedTradesPage();
    return true;
  } catch (e) {
    console.error("Erreur fetch comments:", e);
    commentsCache = {};
    return false;
  }
}
async function fetchStats() {
  try {
    const capRes = await fetch('http://localhost:80/api/capitalDB');
    if (!capRes.ok) throw new Error('Erreur réseau (capital)');
    const capData = await capRes.json();
    const capital = capData.capital || 1;
    capitalReference = capital;
    document.getElementById('stat-capital').textContent = inPercent ? "100%" : capital.toFixed(2) + " €";

    let tradesData;
    const tradesRes = await fetch('http://localhost:80/api/tradesDB');
    if (!tradesRes.ok) throw new Error('Erreur réseau (trades pour stats)');
    tradesData = await tradesRes.json();
    rawData = tradesData;

    const closed = (tradesData.data.closed_trades || []).filter(t => t.symbol);
    tradesCache = (tradesData.data.open_trades || []).filter(t => t.symbol);

    renderTrades();
    updateDisplay(tradesData);


    let rrTotal = 0, rrCount = 0, gainTotal = 0, lossTotal = 0, gainCount = 0, lossCount = 0;
    let best = -Infinity, worst = Infinity;
    let balance = 0;

    closed.forEach(trade => {
      const p = trade.profit ?? 0;
      balance += p;
      best = Math.max(best, p);
      worst = Math.min(worst, p);
      if (p >= 0) { gainTotal += p; gainCount++; }
      else { lossTotal += p; lossCount++; }

      const { open_price, sl, tp, type } = trade;
      if (sl !== null && tp !== null && sl !== open_price) {
        let rr = type === 1 ? (tp - open_price) / (open_price - sl) : (open_price - tp) / (sl - open_price);
        if (isFinite(rr)) { rrTotal += rr; rrCount++; }
      }
    });

    const drawdown = calculateDrawdown(closed);

    document.getElementById('stat-rr').textContent = (rrTotal / rrCount || 0).toFixed(2);
    document.getElementById('stat-gain').textContent = fmt(gainTotal / gainCount || 0, capital);
    document.getElementById('stat-loss').textContent = fmt(lossTotal / lossCount || 0, capital);
    document.getElementById('stat-best').textContent = fmt(best, capital);
    document.getElementById('stat-worst').textContent = fmt(worst, capital);
    document.getElementById('stat-dd').textContent = drawdown.toFixed(2) + '%';

  } catch (e) {
    console.error("Erreur stats:", e);
  }
}

function calculateDrawdown(trades) {
  let peak = 0, balance = 0, maxDD = 0;
  for (const t of trades) {
    balance += t.profit ?? 0;
    peak = Math.max(peak, balance);
    maxDD = Math.max(maxDD, peak > 0 ? ((peak - balance) / peak) * 100 : 0);
  }
  return maxDD;
}

// === Rendu des trades ouverts ===
function renderTrades() {
  const container = document.getElementById('openTradesList');
  container.innerHTML = '';
  if (!tradesCache.length) return container.innerHTML = '<p style="text-align:center">Aucun trade en cours.</p>';

  const header = document.createElement('div');
  header.className = 'trade-item trade-header';
  header.innerHTML = `
    <div>Ticket</div><div>Symbole</div><div>Type</div><div>Lots</div>
    <div>Prix</div><div>SL</div><div>TP</div><div>Profit</div>
    <div>RR</div><div>Attente</div><div>Confiance</div><div>Satisfaction</div>
    <div>Commentaire</div><div>Actions</div>`;
  container.appendChild(header);

  for (const trade of tradesCache) {
    const rr = calcRR(trade);
    const comment = commentsCache[String(trade.ticket)] || {};
    const typeStr = trade.type === 1 ? "Achat" : "Vente";
    const div = document.createElement('div');
    div.className = 'trade-item';
    div.dataset.ticket = trade.ticket;
    div.innerHTML = `
      <div>${trade.ticket}</div><div>${trade.symbol}</div><div>${typeStr}</div>
      <div>${trade.lots}</div><div>${trade.open_price}</div><div>${trade.sl}</div><div>${trade.tp}</div>
      <div>${trade.profit != null ? fmt(trade.profit, capitalReference || 1) : '-'}</div><div>${rr ?? '-'}</div>
      <div>${comment.attente ?? '-'}</div><div>${comment.confiance ?? '-'}</div><div>${comment.satisfaction ?? '-'}</div>
      
      <div>${escapeHtml(comment.text || '')}</div>
      <div>
        <button class="edit-comment-btn" data-ticket="${trade.ticket}">✏️</button>
        <button class="delete-comment-btn" data-ticket="${trade.ticket}">🗑️</button>
         <button class="add-st-btn" data-ticket="${trade.ticket}">✨</button>
        <button class="delete-trade-btn" data-ticket="${trade.ticket}">❌</button>
      </div>`;
    container.appendChild(div);
  }
}

// === Gestion des évènements UI ===
document.getElementById("darkModeToggle").onclick = () => document.body.classList.toggle("dark-mode");
document.getElementById("toggleCurrency").onclick = () => {
  inPercent = !inPercent;
  fetchStats();
  if (rawData) {
    updateDisplay(rawData);
    renderTrades();
    renderClosedTradesPage();
  }
};
document.getElementById("toggleFloat").onclick = () => {
  const box = document.getElementById("accountInfo");
  box.classList.toggle("visible");
  box.classList.toggle("hidden");
};



// Listeners sur inputs config
document.getElementById("closeBloc_allTrade").addEventListener("change", (e) => {
  sendConfigUpdate({ closeBloc_allTrade: e.target.checked });
});
document.getElementById("autoStopLoss_enabled").addEventListener("change", (e) => {
  sendConfigUpdate({ section: "auto_stop_loss", enabled: e.target.checked });
});
document.getElementById("autoStopLoss_distance").addEventListener("change", (e) => {
  const val = parseInt(e.target.value, 10);
  if (!isNaN(val) && val >= 0) {
    sendConfigUpdate({ section: "auto_stop_loss", distance_pips: val });
  }
});
document.getElementById("trailingStop_enabled").addEventListener("change", (e) => {
  sendConfigUpdate({ section: "trailing_stop", enabled: e.target.checked });
});
document.getElementById("trailingStop_distance").addEventListener("change", (e) => {
  const val = parseInt(e.target.value, 10);
  if (!isNaN(val) && val >= 0) {
    sendConfigUpdate({ section: "trailing_stop", distance_pips: val });
  }
});

// === Gestion commentaires ===
function createModal(attente = '') {
  if (document.getElementById('commentModal')) return;

  const modal = document.createElement('div');
  modal.id = 'commentModal';
  modal.style.position = 'fixed';
  modal.style.top = '50%';
  modal.style.left = '50%';
  modal.style.transform = 'translate(-50%, -50%)';
  modal.style.background = '#fff';
  modal.style.border = '1px solid #ccc';
  modal.style.boxShadow = '0 3px 10px rgba(0,0,0,0.2)';
  modal.style.padding = '1.5rem';
  modal.style.zIndex = 10000;
  modal.style.width = '400px';
  modal.style.maxHeight = '80vh';
  modal.style.overflowY = 'auto';
  modal.style.borderRadius = '8px';

  modal.innerHTML = `
    <h3>Editer Commentaire</h3>
    <form id="commentForm">
      <input type="hidden" id="commentId" />
      <label>Attente:<br><input type="text" id="commentAttente" style="width: 100%;" value="" /></label><br><br>
      <label>Confiance (0-5):<br><input type="number" id="commentConfiance" min="0" max="5" style="width: 100%;" /></label><br><br>
      <label>Satisfaction (0-5):<br><input type="number" id="commentSatisfaction" min="0" max="5" style="width: 100%;" /></label><br><br>
      <label>Texte:<br><textarea id="commentText" rows="5" style="width: 100%;"></textarea></label><br><br>
      <button type="submit">Enregistrer</button>
      <button type="button" id="closeModalBtn" style="margin-left: 1rem;">Annuler</button>
    </form>
  `;

  document.body.appendChild(modal);

  // Ajouter la valeur d'attente après la création du modal
  document.getElementById('commentAttente').value = attente;

  document.getElementById('closeModalBtn').onclick = () => closeEditPopup();

  document.getElementById('commentForm').onsubmit = async (e) => {
    e.preventDefault();
    await saveComment();
  };
}

function openEditPopup(ticket) {
  if (isEditing) return;
  isEditing = true;

  createModal();

  const comment = commentsCache[ticket] || {};

  document.getElementById('commentId').value = ticket;
  document.getElementById('commentAttente').value = comment.attente || '';
  document.getElementById('commentConfiance').value = comment.confiance ?? 0;
  document.getElementById('commentSatisfaction').value = comment.satisfaction ?? 0;
  document.getElementById('commentText').value = comment.text || '';

  document.getElementById('commentModal').style.display = 'block';
}

function closeEditPopup() {
  isEditing = false;
  const modal = document.getElementById('commentModal');
  if (modal) modal.style.display = 'none';
}

async function saveComment() {
  const id = document.getElementById('commentId').value;
  const attente = document.getElementById('commentAttente').value.trim();
  const confiance = parseInt(document.getElementById('commentConfiance').value);
  const satisfaction = parseInt(document.getElementById('commentSatisfaction').value);
  const text = document.getElementById('commentText').value.trim();

  // Validation comme dans le backend
  if (!attente && !text) {
    alert("Texte ou attente requis!");
    return;
  }

  if (confiance < 0 || confiance > 5 || satisfaction < 0 || satisfaction > 5) {
    alert("Confiance et satisfaction doivent être entre 0 et 5");
    return;
  }

  const payload = {
    id: id,
    text: text,
    satisfaction: satisfaction,
    confiance: confiance,
    attente: attente
  };

  try {
    // Détermine si c'est une nouvelle entrée ou une modification
    const isNew = !commentsCache[id];
    const endpoint = isNew ? 'addDB' : 'editDB';
    
    const res = await fetch(`http://localhost:80/api/comments/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    
    if (data.status !== 'success') {
      throw new Error(data.message || 'Erreur inconnue');
    }

    // Mise à jour du cache local
    commentsCache[id] = {
      text: text,
      satisfaction: satisfaction,
      confiance: confiance,
      attente: attente,
      // On conserve les autres champs s'ils existent déjà
      ...(commentsCache[id] || {})
    };

    // Mise à jour de l'UI
    updateCommentInUI(id);
    closeEditPopup();
    renderTrades();
    renderClosedTradesPage();
    
  } catch (err) {
    console.error("Erreur sauvegarde commentaire:", err);
    alert(`Erreur: ${err.message}`);
  }
}

function updateCommentInUI(ticket) {
  const tradeDiv = document.querySelector(`.trade-item[data-ticket="${ticket}"]`);
  if (!tradeDiv) return;
  const comment = commentsCache[ticket];

  const cols = tradeDiv.children;
  // Ajustement des index:
  cols[9].textContent = comment.attente ?? '-';
  cols[10].textContent = comment.confiance ?? '-';
  cols[11].textContent = comment.satisfaction ?? '-';
  cols[12].textContent = escapeHtml(comment.text || '');
}

async function deleteComment(ticket) {
  if (!confirm(`Supprimer le commentaire pour le trade ${ticket} ?`)) return;
  
  try {
    const res = await fetch('http://localhost:80/api/comments/deleteDB', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: ticket })
    });

    const data = await res.json();
    
    if (data.status !== 'success') {
      throw new Error(data.message || 'Erreur inconnue');
    }

    delete commentsCache[ticket];
    await fetchComments(); // Recharge les données fraîches
    renderClosedTradesPage();
    renderTrades();
    
  } catch (err) {
    console.error("Erreur suppression commentaire:", err);
    alert(`Erreur: ${err.message}`);
  }
}
async function tradeComment(ticket) {
  if (!confirm("Ajouter un TP et un SL au trade : " + ticket + " ?")) return;
  try {
    const res = await fetch('http://localhost:80/api/commentsDB', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: ticket})
    });
    if (!res.ok) throw new Error('Erreur réseau');
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message || 'Erreur inconnue');

    delete commentsCache[ticket];
    
    // Recharge les commentaires du serveur (optionnel, mais recommandé pour synchro)
    await fetchComments();

    // Re-render la liste pour afficher la suppression
    renderClosedTradesPage();

  } catch (err) {
    console.error(err);
  }
}
async function closeTrade(ticket) {
  if (!confirm("Supprimer le trade " + ticket + " ?")) return;
  try {
    const res = await fetch('http://localhost:80/api/trades/closesDB', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: ticket })
    });
    if (!res.ok) throw new Error('Erreur réseau');
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message || 'Erreur inconnue');

    delete commentsCache[ticket];
    
    // Recharge les commentaires du serveur (optionnel, mais recommandé pour synchro)
    await fetchComments();

    // Re-render la liste pour afficher la suppression
    renderClosedTradesPage();

  } catch (err) {
    console.error(err);
  }
}

// === Gestion des clics boutons ===
document.addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const ticket = btn.dataset.ticket;

  if (btn.classList.contains("edit-comment-btn")) {
    openEditPopup(ticket);
  } else if (btn.classList.contains("delete-comment-btn")) {
    deleteComment(ticket);
  }else if (btn.classList.contains("delete-trade-btn")) {
    closeTrade(ticket);
  }else if (btn.classList.contains("add-st-btn")) {
    tradeComment(ticket);
  }
});

// === Graphique capital ===
async function loadSymbolsColors() {
  try {
    const response = await fetch('http://127.0.0.1:80/static/allSymbolsToColor.json');
    symbolsColors = await response.json();
  } catch (error) {
    console.error("Erreur chargement couleurs:", error);
    symbolsColors = {
      ".DE40Cash": [225,83,222],
      ".JP225Cash": [12,195,203],
      ".US30Cash": [91,32,33],
      ".US500Cash": [31,82,161],
      ".USTECHCash": [174,137,37],
      "AUDCAD": [55,1,144],
      "AUDCHF": [79,65,142],
      "AUDJPY": [43,247,25],
      "AUDNZD": [213,41,196]
    };
  }
}

async function getInitialCapital() {
  try {
    const response = await fetch('http://127.0.0.1:80/api/tradesDB');
    const data = await response.json();
    initialCapital = data.data.account.balance || 1000;
  } catch (error) {
    console.error("Erreur récupération capital:", error);
    initialCapital = 1000;
  }
}

function calculateCapitalEvolution(trades) {
  trades.sort((a, b) => new Date(a.close_time) - new Date(b.close_time));
  const dataPoints = [];
  let currentCapital = initialCapital;
  
  dataPoints.push({
    x: new Date(trades[0].open_time),
    y: currentCapital,
    trade: null
  });
  
  trades.forEach(trade => {
    currentCapital += trade.profit;
    dataPoints.push({
      x: new Date(trade.close_time),
      y: currentCapital,
      trade: trade
    });
  });
  
  return { dataPoints, finalCapital: currentCapital };
}

function createSegmentDataset(symbol, points, color) {
  const colorStr = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
  return {
    label: symbol || 'Départ',
    data: points,
    borderColor: colorStr,
    backgroundColor: `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.5)`,
    borderWidth: 2,
    tension: 0.1,
    fill: false,
    pointRadius: (context) => context.raw.trade ? 4 : 0,
    pointBackgroundColor: (context) => 
      !context.raw.trade ? colorStr : (context.raw.trade.profit >= 0 ? 'rgb(0, 200, 0)' : 'rgb(255, 0, 0)')
  };
}

function updateChartDatasets(capitalData) {
  const datasets = [];
  let currentSymbol = null;
  let currentColor = [75, 192, 192];
  let segmentPoints = [];
  
  capitalData.dataPoints.forEach((point, index) => {
    if (!point.trade && index === 0) {
      segmentPoints.push(point);
      return;
    }
    
    const trade = point.trade;
    if (!trade) return;
    
    if (trade.symbol !== currentSymbol) {
      if (segmentPoints.length > 0) {
        datasets.push(createSegmentDataset(currentSymbol, segmentPoints, currentColor));
      }
      
      currentSymbol = trade.symbol;
      currentColor = symbolsColors[currentSymbol] || [255, 99, 132];
      segmentPoints = [capitalData.dataPoints[index - 1]];
    }
    
    segmentPoints.push(point);
  });
  
  if (segmentPoints.length > 0) {
    datasets.push(createSegmentDataset(currentSymbol, segmentPoints, currentColor));
  }
  
  capitalChart.data.datasets = datasets;
  capitalChart.update();
}

async function updateCapitalChart() {
  if (!capitalChart) return;
  
  try {
    const response = await fetch('http://127.0.0.1:80/api/tradesDB');
    const data = await response.json();
    const closedTrades = data.data.closed_trades || [];
    
    if (closedTrades.length === 0) {
      document.getElementById('CLoseTradesGraph').innerHTML = '<p>Aucun trade fermé disponible.</p>';
      return;
    }
    
    const capitalData = calculateCapitalEvolution(closedTrades);
    updateChartDatasets(capitalData);
    
  } catch (error) {
    console.error("Erreur mise à jour graphique:", error);
  }
}

async function initCapitalChart() {
  await loadSymbolsColors();
  
  const container = document.getElementById('CLoseTradesGraph');
  container.innerHTML = '<canvas id="capitalChartCanvas" style="width:100%; height:400px;"></canvas>';
  
  const ctx = document.getElementById('capitalChartCanvas').getContext('2d');
  
  capitalChart = new Chart(ctx, {
    type: 'line',
    data: { datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: {
            parser: 'yyyy.MM.dd HH:mm',
            tooltipFormat: 'dd/MM/yyyy HH:mm',
            unit: 'day'
          },
          title: { display: true, text: 'Date' }
        },
        y: { title: { display: true, text: 'Capital' } }
      },
      plugins: {
        zoom: {
          pan: { enabled: true, mode: 'x', modifierKey: 'ctrl' },
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: 'x',
            drag: { enabled: true }
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`,
            afterLabel: (context) => {
              const trade = context.raw.trade;
              return trade ? [
                `Symbole: ${trade.symbol}`,
                `Profit: ${trade.profit.toFixed(2)}`,
                `Type: ${trade.type === 0 ? 'Vente' : 'Achat'}`,
                `Lots: ${trade.lots}`
              ] : '';
            }
          }
        },
        legend: { position: 'top' }
      }
    }
  });
  
  await updateCapitalChart();
}

// === Gestion des trades fermés ===
function renderPaginationControls() {
  const totalPages = Math.ceil(closedTrades.length / pageSize);
  const pagination = document.createElement('div');
  pagination.className = 'pagination-controls';
  pagination.style.textAlign = 'center';
  pagination.style.marginTop = '1em';

  if (currentPage > 0) {
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '⬅️ Page précédente';
    prevBtn.onclick = () => {
      currentPage--;
      renderClosedTradesPage();
    };
    pagination.appendChild(prevBtn);
  }

  if ((currentPage + 1) * pageSize < closedTrades.length) {
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Page suivante ➡️';
    nextBtn.style.marginLeft = '1em';
    nextBtn.onclick = () => {
      currentPage++;
      renderClosedTradesPage();
    };
    pagination.appendChild(nextBtn);
  }

  document.getElementById('CLoseTradesList').appendChild(pagination);
}

function renderClosedTradesPage() {
  const container = document.getElementById('CLoseTradesList');
  container.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'trade-item trade-header';
  header.innerHTML = `
    <div>Ticket</div><div>Symbole</div><div>Type</div><div>Lots</div>
    <div>Prix</div><div>SL</div><div>TP</div><div>Profit</div>
    <div>RR</div><div>Attente</div><div>Confiance</div><div>Satisfaction</div>
    <div>Commentaire</div><div>Actions</div>`;
  container.appendChild(header);

  const start = currentPage * pageSize;
  const end = start + pageSize;
  const tradesToRender = closedTrades.slice(start, end);

  for (const trade of tradesToRender) {
    const rr = calcRR(trade);
    const comment = commentsCache[trade.ticket] || {};
    const typeStr = trade.type === 1 ? "Achat" : "Vente";
    const div = document.createElement('div');
    div.className = 'trade-item';
    div.dataset.ticket = trade.ticket;
    div.innerHTML = `
      <div>${trade.ticket}</div><div>${trade.symbol}</div><div>${typeStr}</div>
      <div>${trade.lots}</div><div>${trade.open_price}</div><div>${trade.sl}</div><div>${trade.tp}</div>
      <div>${trade.profit != null ? fmt(trade.profit, capitalReference || initialCapital || 1) : '-'}</div><div>${rr ?? '-'}</div>
      <div>${comment.attente ?? '-'}</div><div>${comment.confiance ?? '-'}</div><div>${comment.satisfaction ?? '-'}</div>
      <div>${escapeHtml(comment.text || '')}</div>
      <div>
        <button class="edit-comment-btn" data-ticket="${trade.ticket}">✏️</button>
        <button class="delete-comment-btn" data-ticket="${trade.ticket}">🗑️</button>
      </div>`;
    container.appendChild(div);
  }

  renderPaginationControls();
}

async function loadClosedTrades() {
  try {
    const res = await fetch('http://localhost:80/api/tradesDB');
    if (!res.ok) throw new Error("Erreur fetch closed trades");
    const data = await res.json();

    closedTrades = (data.data.closed_trades || []).filter(t => t.symbol).sort((a, b) => new Date(b.close_time) - new Date(a.close_time));
    currentPage = 0;
    renderClosedTradesPage();
  } catch (e) {
    console.error("Erreur loadClosedTrades:", e);
    document.getElementById('CLoseTradesList').innerHTML = `<p>Erreur chargement: ${e.message}</p>`;
  }
}

// === Initialisation complète ===
async function initApp() {
  await getInitialCapital();
  await fetchComments(); // Chargement initial des commentaires
  await loadClosedTrades();
  await initCapitalChart();

  // Rafraîchissements automatiques
  setInterval(() => { if (!isEditing) fetchData(); }, 2000);
  setInterval(() => { if (!isEditing) fetchStats(); }, 2000);
  setInterval(() => { if (!isEditing) fetchComments(); }, 2000);
  setInterval(() => { if (!isEditing) updateCapitalChart(); }, 60000);
}

window.addEventListener('DOMContentLoaded', initApp);
window.renderClosedTradesPage = renderClosedTradesPage;

// Ouvrir/fermer popup et affichage des données + graphiques

const btnOpen = document.getElementById("openStatsBtn");
const popup = document.getElementById("statsPopup");
const btnClose = popup.querySelector(".closeBtn");

const accountInfoDiv = document.getElementById("accountInfo");
const statsInfoDiv = document.getElementById("statsInfo");

let charts = [];

btnOpen.addEventListener("click", () => {
  // Remplir les blocs infos avec les valeurs récupérées
  fillAccountInfo();
  fillStatsInfo();

  // Afficher la popup
  popup.style.display = "block";

  // Rendre le focus accessible pour accessibilité
  btnClose.focus();

  // Rendu des graphiques
  renderCharts();
});

btnClose.addEventListener("click", () => {
  popup.style.display = "none";
  // Détruire les charts pour éviter doublons
  charts.forEach(c => c.destroy());
  charts = [];
});

// Récupérer les valeurs depuis les spans de la page (hors popup)
function getValue(id, fallback = "-") {
  const el = document.getElementById(id);
  if (!el) return fallback;
  return el.textContent.trim() || fallback;
}

function fillAccountInfo() {
  // Construire HTML dynamique pour compte
  const balance = getValue("balance");
  const equity = getValue("equity");
  const freeMargin = getValue("freeMargin");
  const margin = getValue("margin");
  const leverage = getValue("leverage");
  const accountNumber = getValue("accountNumber");
  const currency = getValue("currency");

  accountInfoDiv.innerHTML = `
    <p><strong>Balance :</strong> <span>${balance}</span></p>
    <p><strong>Equity :</strong> <span>${equity}</span></p>
    <p><strong>Free Margin :</strong> <span>${freeMargin}</span></p>
    <p><strong>Margin :</strong> <span>${margin}</span></p>
    <p><strong>Leverage :</strong> <span>${leverage}x</span></p>
    <p><strong>Account Number :</strong> <span>${accountNumber}</span></p>
    <p><strong>Devise :</strong> <span>${currency}</span></p>
  `;
}

function fillStatsInfo() {
  // Construire HTML dynamique pour stats
  const capital = getValue("stat-capital");
  const rr = getValue("stat-rr");
  const best = getValue("stat-best");
  const worst = getValue("stat-worst");
  const gain = getValue("stat-gain");
  const loss = getValue("stat-loss");
  const dd = getValue("stat-dd");

  statsInfoDiv.innerHTML = `
    <p><strong>Capital :</strong> <span>${capital}</span></p>
    <p><strong>RR moyen :</strong> <span>${rr}</span></p>
    <p><strong>Best trade :</strong> <span>${best}</span></p>
    <p><strong>Burk trade :</strong> <span>${worst}</span></p>
    <p><strong>Moyenne gain :</strong> <span>${gain}</span></p>
    <p><strong>Moyenne perte :</strong> <span>${loss}</span></p>
    <p><strong>Drowdawn actuelle :</strong> <span>${dd}</span></p>
  `;
}

function renderCharts() {
  // Récupérer les données numériques pour les graphiques
  const freeMargin = parseFloat(getValue("freeMargin").replace(/[^\d.-]/g, "")) || 0;
  const margin = parseFloat(getValue("margin").replace(/[^\d.-]/g, "")) || 0;
  const avgGain = parseFloat(getValue("stat-gain").replace(/[^\d.-]/g, "")) || 0;
  const avgLoss = Math.abs(parseFloat(getValue("stat-loss").replace(/[^\d.-]/g, ""))) || 0;
  const bestTrade = parseFloat(getValue("stat-best").replace(/[^\d.-]/g, "")) || 0;
  const worstTrade = Math.abs(parseFloat(getValue("stat-worst").replace(/[^\d.-]/g, ""))) || 0;

  // Margin chart (doughnut)
  charts.push(new Chart(document.getElementById("marginChart"), {
    type: 'doughnut',
    data: {
      labels: ['Free Margin', 'Margin utilisée'],
      datasets: [{
        data: [freeMargin, margin],
        backgroundColor: ['#4CAF50', '#F44336'],
        borderWidth: 1,
        borderColor: '#fff'
      }]
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: 'Répartition de la Marge',
          font: { size: 16, weight: '600' }
        },
        legend: { position: 'bottom' }
      },
      cutout: '70%'
    }
  }));

  // Moyenne gain/perte (bar chart)
  charts.push(new Chart(document.getElementById("gainLossChart"), {
    type: 'bar',
    data: {
      labels: ['Moyenne Gain', 'Moyenne Perte'],
      datasets: [{
        label: '€',
        data: [avgGain, avgLoss],
        backgroundColor: ['#2196F3', '#E91E63']
      }]
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: 'Moyenne des Trades',
          font: { size: 16, weight: '600' }
        },
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  }));

  // Best vs Worst trade (bar chart)
  charts.push(new Chart(document.getElementById("bestWorstChart"), {
    type: 'bar',
    data: {
      labels: ['Best Trade', 'Worst Trade'],
      datasets: [{
        label: '€',
        data: [bestTrade, worstTrade],
        backgroundColor: ['#8BC34A', '#FF5722']
      }]
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: 'Meilleur vs Pire Trade',
          font: { size: 16, weight: '600' }
        },
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  }));
}
