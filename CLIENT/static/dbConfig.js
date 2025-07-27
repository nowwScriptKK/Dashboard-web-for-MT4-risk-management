// === Chargement / Edition Config ===
async function loadConfig() {
  try {
    const res = await fetch("http://localhost:80/api/configDB");
    if (!res.ok) throw new Error("Erreur réseau (config)");
    const data = await res.json();
    configCache = data.data.config;

    document.getElementById("closeBloc_allTrade").checked = !!configCache.closeBloc_allTrade;
    document.getElementById("autoStopLoss_enabled").checked = !!configCache.auto_stop_loss.enabled;
    document.getElementById("autoStopLoss_distance").value = configCache.auto_stop_loss.distance_pips ?? 0;
    document.getElementById("trailingStop_enabled").checked = !!configCache.trailing_stop.enabled;
    document.getElementById("trailingStop_distance").value = configCache.trailing_stop.distance_pips ?? 0;

    showConfigMessage("");
  } catch (err) {
    showConfigMessage("Erreur lors du chargement de la configuration", true);
    console.error(err);
  }
}

function sendConfigUpdate(payload) {
  showConfigMessage("Enregistrement...");
  fetch("http://localhost:80/api/config/editDB", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === "success") {
        showConfigMessage("Modification enregistrée", false);
        if (payload.section) {
          configCache[payload.section] = { ...configCache[payload.section], ...payload };
          delete configCache[payload.section].section;
        } else {
          Object.assign(configCache, payload);
        }
      } else {
        showConfigMessage("Erreur: " + (data.message || "Erreur inconnue"), true);
      }
    })
    .catch((err) => {
      showConfigMessage("Erreur réseau", true);
      console.error(err);
    });
}