(function () {
  const STORAGE_KEY = "pfv_vault_password";
  let vaultPassword = sessionStorage.getItem(STORAGE_KEY) || "";

  let appState = {
    config: {},
    stats: { channels: 0, files: 0, users: 0, downloads: 0 },
    channels: [],
    files: [],
    users: [],
  };

  let joinedChannelIds = new Set();
  let selectedSimFileId = null;

  const els = {
    // Auth Gate
    vaultAuthGate: document.getElementById("vaultAuthGate"),
    vaultAppShell: document.getElementById("vaultAppShell"),
    vaultLoginForm: document.getElementById("vaultLoginForm"),
    vaultPasswordInput: document.getElementById("vaultPasswordInput"),
    togglePwVisibilityBtn: document.getElementById("togglePwVisibilityBtn"),
    authFeedback: document.getElementById("authFeedback"),
    lockVaultBtn: document.getElementById("lockVaultBtn"),

    // Header
    headerBotName: document.getElementById("headerBotName"),
    simBotTitle: document.getElementById("simBotTitle"),
    dbPathLabel: document.getElementById("dbPathLabel"),
    botModeDot: document.getElementById("botModeDot"),
    botModeText: document.getElementById("botModeText"),
    statChannels: document.getElementById("statChannels"),
    statFiles: document.getElementById("statFiles"),
    statUsers: document.getElementById("statUsers"),
    statDownloads: document.getElementById("statDownloads"),

    // Tabs
    tabBtns: document.querySelectorAll(".tab-btn"),
    tabPanelConfig: document.getElementById("tabPanelConfig"),
    tabPanelChannels: document.getElementById("tabPanelChannels"),
    tabPanelFiles: document.getElementById("tabPanelFiles"),

    // Config Form
    configForm: document.getElementById("configForm"),
    inputBotToken: document.getElementById("inputBotToken"),
    currentTokenHint: document.getElementById("currentTokenHint"),
    inputAdminIds: document.getElementById("inputAdminIds"),
    inputBotName: document.getElementById("inputBotName"),
    inputDbPath: document.getElementById("inputDbPath"),
    configFeedback: document.getElementById("configFeedback"),
    copyEnvBtn: document.getElementById("copyEnvBtn"),

    // Channels
    addChannelForm: document.getElementById("addChannelForm"),
    channelTitle: document.getElementById("channelTitle"),
    channelChatId: document.getElementById("channelChatId"),
    channelUsername: document.getElementById("channelUsername"),
    channelInviteLink: document.getElementById("channelInviteLink"),
    channelFeedback: document.getElementById("channelFeedback"),
    channelsTableBody: document.getElementById("channelsTableBody"),

    // Files
    addFileForm: document.getElementById("addFileForm"),
    fileName: document.getElementById("fileName"),
    fileType: document.getElementById("fileType"),
    fileCaption: document.getElementById("fileCaption"),
    fileTgId: document.getElementById("fileTgId"),
    fileFeedback: document.getElementById("fileFeedback"),
    filesTableBody: document.getElementById("filesTableBody"),

    // Simulator
    simFileSelect: document.getElementById("simFileSelect"),
    simMembershipChips: document.getElementById("simMembershipChips"),
    tgBubbleContent: document.getElementById("tgBubbleContent"),
    tgDeliveredBox: document.getElementById("tgDeliveredBox"),
    tgInlineKeyboard: document.getElementById("tgInlineKeyboard"),
    simBtnStart: document.getElementById("simBtnStart"),
    simBtnDeepLink: document.getElementById("simBtnDeepLink"),
    simBtnVerify: document.getElementById("simBtnVerify"),
    simBtnStats: document.getElementById("simBtnStats"),
  };

  function apiFetch(url, options) {
    const opts = Object.assign({}, options || {});
    opts.headers = Object.assign({}, opts.headers || {}, {
      "X-Vault-Password": vaultPassword,
    });
    return fetch(url, opts);
  }

  function showLockGate(message) {
    els.vaultAuthGate.classList.remove("hidden");
    els.vaultAppShell.classList.add("hidden");
    if (message) {
      setFeedback(els.authFeedback, message, true);
    }
  }

  function showUnlockedApp(stateData) {
    els.vaultAuthGate.classList.add("hidden");
    els.vaultAppShell.classList.remove("hidden");
    setFeedback(els.authFeedback, "", false);
    if (stateData) {
      renderAll(stateData);
      runSimulation("deep_link");
    }
  }

  els.togglePwVisibilityBtn.addEventListener("click", () => {
    const isPw = els.vaultPasswordInput.type === "password";
    els.vaultPasswordInput.type = isPw ? "text" : "password";
  });

  els.vaultLoginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const entered = els.vaultPasswordInput.value.trim();
    if (!entered) {
      setFeedback(els.authFeedback, "❌ Password daalna zaroori hai.", true);
      return;
    }

    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: entered }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setFeedback(
        els.authFeedback,
        err.detail || "❌ Galat password! Sahi Vault Password daalein.",
        true
      );
      return;
    }

    const data = await res.json();
    vaultPassword = entered;
    sessionStorage.setItem(STORAGE_KEY, vaultPassword);
    els.vaultPasswordInput.value = "";
    showUnlockedApp(data.state);
  });

  els.lockVaultBtn.addEventListener("click", () => {
    vaultPassword = "";
    sessionStorage.removeItem(STORAGE_KEY);
    showLockGate("🔒 Vault locked.");
  });

  function switchTab(tabName) {
    els.tabBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
    els.tabPanelConfig.classList.toggle("hidden", tabName !== "config");
    els.tabPanelChannels.classList.toggle("hidden", tabName !== "channels");
    els.tabPanelFiles.classList.toggle("hidden", tabName !== "files");
  }

  els.tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  function setFeedback(el, text, isError) {
    if (!el) return;
    el.textContent = text;
    el.className = "form-feedback " + (isError ? "err" : "ok");
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderAll(data) {
    appState = data;
    const cfg = data.config || {};
    const stats = data.stats || {};

    els.headerBotName.textContent = cfg.bot_name || "Premium File Vault";
    els.simBotTitle.textContent = cfg.bot_name || "Premium File Vault";
    els.dbPathLabel.textContent = "DB: " + (cfg.db_path || "bot_data.db");

    if (cfg.runtime && cfg.runtime.mode === "webhook_live") {
      els.botModeDot.className = "dot dot-ok";
      els.botModeText.textContent = "Webhook Mode: Live (Zero Conflict)";
    } else if (cfg.runtime && cfg.runtime.bot_running) {
      els.botModeDot.className = "dot dot-ok";
      els.botModeText.textContent = "Telegram Polling: Live";
    } else if (cfg.token_valid) {
      els.botModeDot.className = "dot";
      els.botModeText.textContent = "Bot Token Ready";
    } else {
      els.botModeDot.className = "dot";
      els.botModeText.textContent = "Simulator Mode (Set BOT_TOKEN for Live)";
    }

    els.statChannels.textContent = String(stats.channels ?? 0);
    els.statFiles.textContent = String(stats.files ?? 0);
    els.statUsers.textContent = String(stats.users ?? 0);
    els.statDownloads.textContent = String(stats.downloads ?? 0);

    els.currentTokenHint.textContent =
      "Active Token: " + (cfg.bot_token_masked || "Not Set");
    if (!els.inputAdminIds.dataset.dirty) {
      els.inputAdminIds.value = (cfg.admin_ids || [123456789]).join(",");
    }
    if (!els.inputBotName.dataset.dirty) {
      els.inputBotName.value = cfg.bot_name || "Premium File Vault";
    }
    if (!els.inputDbPath.dataset.dirty) {
      els.inputDbPath.value = cfg.db_path || "bot_data.db";
    }

    renderChannelsTable();
    renderFilesTable();
    renderSimulatorControls();
  }

  function renderChannelsTable() {
    const channels = appState.channels || [];
    if (channels.length === 0) {
      els.channelsTableBody.innerHTML =
        '<tr><td colspan="5">No force-join channels added yet. Add one above.</td></tr>';
      return;
    }
    els.channelsTableBody.innerHTML = channels
      .map(
        (ch) => `
        <tr>
          <td><strong>#${ch.id}</strong></td>
          <td>
            <strong>${escapeHtml(ch.title)}</strong>
            ${ch.username ? `<div class="field-hint">@${escapeHtml(ch.username)}</div>` : ""}
          </td>
          <td><code>${ch.chat_id}</code></td>
          <td><a href="${escapeHtml(ch.invite_link)}" target="_blank" rel="noopener" style="color:#38bdf8">${escapeHtml(ch.invite_link)}</a></td>
          <td>
            <button type="button" class="btn-danger-sm" data-del-channel="${ch.id}" aria-label="Delete channel ${escapeHtml(ch.title)}">
              🗑 Delete
            </button>
          </td>
        </tr>
      `
      )
      .join("");

    els.channelsTableBody.querySelectorAll("[data-del-channel]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-del-channel");
        const res = await apiFetch(`/api/channels/${id}`, { method: "DELETE" });
        if (res.ok) {
          joinedChannelIds.delete(Number(id));
          renderAll(await res.json());
          runSimulation("deep_link");
        }
      });
    });
  }

  function renderFilesTable() {
    const files = appState.files || [];
    if (files.length === 0) {
      els.filesTableBody.innerHTML =
        '<tr><td colspan="5">No files uploaded yet. Register a file above.</td></tr>';
      return;
    }
    if (!selectedSimFileId || !files.some((f) => f.id === selectedSimFileId)) {
      selectedSimFileId = files[0].id;
    }

    els.filesTableBody.innerHTML = files
      .map(
        (f) => `
        <tr>
          <td><strong>#${f.id}</strong></td>
          <td>
            <strong>${escapeHtml(f.icon)} ${escapeHtml(f.file_name || "file_" + f.id)}</strong>
            ${f.caption ? `<div class="field-hint">${escapeHtml(f.caption)}</div>` : ""}
          </td>
          <td><code>${escapeHtml(f.share_link)}</code></td>
          <td><strong>⬇️ ${f.downloads}</strong></td>
          <td>
            <div class="action-cell">
              <button type="button" class="btn-action-sm" data-test-file="${f.id}" aria-label="Test file ${escapeHtml(f.file_name)} in simulator">
                ▶️ Test Link
              </button>
              <button type="button" class="btn-danger-sm" data-del-file="${f.id}" aria-label="Delete file ${escapeHtml(f.file_name)}">
                🗑 Delete
              </button>
            </div>
          </td>
        </tr>
      `
      )
      .join("");

    els.filesTableBody.querySelectorAll("[data-test-file]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedSimFileId = Number(btn.getAttribute("data-test-file"));
        els.simFileSelect.value = String(selectedSimFileId);
        runSimulation("deep_link", selectedSimFileId);
      });
    });

    els.filesTableBody.querySelectorAll("[data-del-file]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-del-file");
        const res = await apiFetch(`/api/files/${id}`, { method: "DELETE" });
        if (res.ok) {
          renderAll(await res.json());
        }
      });
    });
  }

  function renderSimulatorControls() {
    const files = appState.files || [];
    els.simFileSelect.innerHTML = files
      .map(
        (f) =>
          `<option value="${f.id}" ${f.id === selectedSimFileId ? "selected" : ""}>File #${f.id}: ${escapeHtml(f.file_name)}</option>`
      )
      .join("");

    const channels = appState.channels || [];
    if (channels.length === 0) {
      els.simMembershipChips.innerHTML =
        '<span class="field-hint">No force-join channels active (files unlock immediately)</span>';
    } else {
      els.simMembershipChips.innerHTML = channels
        .map((ch) => {
          const isJoined = joinedChannelIds.has(ch.id);
          return `
            <button
              type="button"
              class="chip-toggle ${isJoined ? "joined" : ""}"
              data-toggle-ch="${ch.id}"
              aria-label="Toggle membership for ${escapeHtml(ch.title)}"
            >
              ${isJoined ? "✅ Joined:" : "❌ Not Joined:"} ${escapeHtml(ch.title)}
            </button>
          `;
        })
        .join("");

      els.simMembershipChips.querySelectorAll("[data-toggle-ch]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const cid = Number(btn.getAttribute("data-toggle-ch"));
          if (joinedChannelIds.has(cid)) {
            joinedChannelIds.delete(cid);
          } else {
            joinedChannelIds.add(cid);
          }
          renderSimulatorControls();
          runSimulation("deep_link", selectedSimFileId);
        });
      });
    }
  }

  async function runSimulation(action, fileIdOverride) {
    const targetFileId =
      fileIdOverride || Number(els.simFileSelect.value) || selectedSimFileId || 1;
    const res = await apiFetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        file_id: targetFileId,
        user_id:
          (appState.config.admin_ids && appState.config.admin_ids[0]) || 123456789,
        first_name: "Admin",
        joined_channel_ids: Array.from(joinedChannelIds),
      }),
    });
    if (!res.ok) return;
    const payload = await res.json();
    if (payload.state) {
      renderAll(payload.state);
    }

    els.tgBubbleContent.innerHTML = payload.message_html || "";

    if (payload.delivered_file) {
      const df = payload.delivered_file;
      els.tgDeliveredBox.classList.remove("hidden");
      els.tgDeliveredBox.innerHTML = `
        <div><strong>📄 ${escapeHtml(df.file_name)}</strong></div>
        <div style="margin-top:4px">${df.caption_html || ""}</div>
        <div style="margin-top:6px;font-size:0.75rem;color:#6ee7b7">
          ⬇️ Total Downloads Now: <strong>${df.downloads}</strong>
        </div>
      `;
    } else {
      els.tgDeliveredBox.classList.add("hidden");
      els.tgDeliveredBox.innerHTML = "";
    }

    const rows = payload.buttons || [];
    els.tgInlineKeyboard.innerHTML = rows
      .map(
        (row) => `
        <div class="tg-kb-row" style="grid-template-columns: repeat(${row.length}, 1fr)">
          ${row
            .map(
              (b) =>
                `<button type="button" class="tg-kb-btn" data-sim-kb="${escapeHtml(b.action)}">${escapeHtml(b.text)}</button>`
            )
            .join("")}
        </div>
      `
      )
      .join("");

    els.tgInlineKeyboard.querySelectorAll("[data-sim-kb]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const act = btn.getAttribute("data-sim-kb") || "";
        if (act.startsWith("join:")) {
          const chId = Number(act.split(":")[1]);
          joinedChannelIds.add(chId);
          renderSimulatorControls();
          runSimulation("deep_link", targetFileId);
        } else if (act.startsWith("verify:")) {
          const fId = Number(act.split(":")[1]);
          runSimulation("verify", fId);
        } else if (act.startsWith("tab:")) {
          switchTab(act.split(":")[1]);
        } else if (act === "sim:stats") {
          runSimulation("stats");
        } else if (act === "sim:start") {
          runSimulation("start");
        } else if (act === "sim:broadcast") {
          runSimulation("broadcast");
        }
      });
    });
  }

  els.configForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const adminIds = els.inputAdminIds.value.trim();
    const botName = els.inputBotName.value.trim();
    const dbPath = els.inputDbPath.value.trim();
    const botToken = els.inputBotToken.value.trim();

    if (!adminIds || !botName || !dbPath) {
      setFeedback(
        els.configFeedback,
        "Please fill ADMIN_IDS, BOT_NAME, and DB_PATH.",
        true
      );
      return;
    }

    const body = {
      admin_ids: adminIds,
      bot_name: botName,
      db_path: dbPath,
    };
    if (botToken) {
      body.bot_token = botToken;
    }

    const res = await apiFetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setFeedback(
        els.configFeedback,
        err.detail || "Failed to save config",
        true
      );
      return;
    }
    const updated = await res.json();
    els.inputBotToken.value = "";
    renderAll(updated);
    setFeedback(
      els.configFeedback,
      "✅ Saved to .env & synced with bot_data.db!",
      false
    );
  });

  els.copyEnvBtn.addEventListener("click", () => {
    const envText = [
      `BOT_TOKEN=${els.inputBotToken.value.trim() || "YOUR_BOT_TOKEN_HERE"}`,
      `ADMIN_IDS=${els.inputAdminIds.value.trim() || "123456789"}`,
      `BOT_NAME=${els.inputBotName.value.trim() || "Premium File Vault"}`,
      `DB_PATH=${els.inputDbPath.value.trim() || "bot_data.db"}`,
    ].join("\n");
    if (navigator.clipboard) {
      navigator.clipboard.writeText(envText).catch(() => {});
    }
    setFeedback(
      els.configFeedback,
      "📋 Copied .env configuration to clipboard!",
      false
    );
  });

  els.addChannelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = els.channelTitle.value.trim();
    const chatId = Number(els.channelChatId.value.trim());
    const username = els.channelUsername.value.trim();
    const inviteLink = els.channelInviteLink.value.trim();

    if (!title || !chatId || !inviteLink) {
      setFeedback(
        els.channelFeedback,
        "Channel Title, Chat ID, and Invite Link are required.",
        true
      );
      return;
    }

    const res = await apiFetch("/api/channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        title,
        username,
        invite_link: inviteLink,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setFeedback(
        els.channelFeedback,
        err.detail || "Could not add channel.",
        true
      );
      return;
    }
    els.channelTitle.value = "";
    els.channelChatId.value = "";
    els.channelUsername.value = "";
    els.channelInviteLink.value = "";
    renderAll(await res.json());
    setFeedback(els.channelFeedback, "✅ Channel saved to bot_data.db!", false);
    runSimulation("deep_link", selectedSimFileId);
  });

  els.addFileForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileName = els.fileName.value.trim();
    const fileType = els.fileType.value;
    const caption = els.fileCaption.value.trim();
    const tgFileId = els.fileTgId.value.trim();

    if (!fileName) {
      setFeedback(els.fileFeedback, "File Name is required.", true);
      return;
    }

    const res = await apiFetch("/api/files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: fileName,
        file_type: fileType,
        caption,
        tg_file_id: tgFileId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setFeedback(
        els.fileFeedback,
        err.detail || "Could not register file.",
        true
      );
      return;
    }
    const payload = await res.json();
    els.fileName.value = "";
    els.fileCaption.value = "";
    els.fileTgId.value = "";
    selectedSimFileId = payload.created_file_id || selectedSimFileId;
    renderAll(payload);
    setFeedback(
      els.fileFeedback,
      `✅ File #${payload.created_file_id} saved to bot_data.db!`,
      false
    );
    runSimulation("deep_link", selectedSimFileId);
  });

  els.simFileSelect.addEventListener("change", () => {
    selectedSimFileId = Number(els.simFileSelect.value);
    runSimulation("deep_link", selectedSimFileId);
  });

  els.simBtnStart.addEventListener("click", () => runSimulation("start"));
  els.simBtnDeepLink.addEventListener("click", () =>
    runSimulation("deep_link", selectedSimFileId)
  );
  els.simBtnVerify.addEventListener("click", () =>
    runSimulation("verify", selectedSimFileId)
  );
  els.simBtnStats.addEventListener("click", () => runSimulation("stats"));

  // Check if already unlocked in sessionStorage
  if (vaultPassword) {
    apiFetch("/api/state")
      .then((r) => {
        if (!r.ok) throw new Error("Unauthorized");
        return r.json();
      })
      .then((data) => showUnlockedApp(data))
      .catch(() => {
        vaultPassword = "";
        sessionStorage.removeItem(STORAGE_KEY);
        showLockGate();
      });
  } else {
    showLockGate();
  }
})();
