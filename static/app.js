(function () {
  const STORAGE_KEY = "pfv_vault_password";
  const DEFAULT_MASTER_PW = "SJEIDB@@@1272737SJWHSH2727";
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("autostart") === "1") {
    sessionStorage.setItem(STORAGE_KEY, DEFAULT_MASTER_PW);
  }
  let vaultPassword = sessionStorage.getItem(STORAGE_KEY) || "";

  let appState = {
    config: {},
    stats: { channels: 0, files: 0, users: 0, downloads: 0, groups: 0, links: 0 },
    channels: [],
    files: [],
    users: [],
    group_banner: {},
    managed_groups: [],
    bot_builder: {},
    user_bots: [],
  };

  let joinedChannelIds = new Set();
  let selectedSimFileId = null;
  let selectedFileIds = new Set();

  const els = {
    // Auth Gate
    vaultAuthGate: document.getElementById("vaultAuthGate"),
    vaultAppShell: document.getElementById("vaultAppShell"),
    vaultLoginForm: document.getElementById("vaultLoginForm"),
    vaultPasswordInput: document.getElementById("vaultPasswordInput"),
    togglePwVisibilityBtn: document.getElementById("togglePwVisibilityBtn"),
    authFeedback: document.getElementById("authFeedback"),
    lockVaultBtn: document.getElementById("lockVaultBtn"),

    // Header & Stats
    headerBotName: document.getElementById("headerBotName"),
    simBotTitle: document.getElementById("simBotTitle"),
    dbPathLabel: document.getElementById("dbPathLabel"),
    keepAliveText: document.getElementById("keepAliveText"),
    botModeDot: document.getElementById("botModeDot"),
    botModeText: document.getElementById("botModeText"),
    statChannels: document.getElementById("statChannels"),
    statFiles: document.getElementById("statFiles"),
    statLinksMeta: document.getElementById("statLinksMeta"),
    statGroups: document.getElementById("statGroups"),
    statUsers: document.getElementById("statUsers"),
    statDownloads: document.getElementById("statDownloads"),

    // Tabs
    tabBtns: document.querySelectorAll(".tab-btn"),
    tabPanelFiles: document.getElementById("tabPanelFiles"),
    tabPanelBotBuild: document.getElementById("tabPanelBotBuild"),
    tabPanelGroups: document.getElementById("tabPanelGroups"),
    tabPanelChannels: document.getElementById("tabPanelChannels"),
    tabPanelConfig: document.getElementById("tabPanelConfig"),

    // Files, Links, /group-upload, /user-upload & Bulk Delete
    addFileForm: document.getElementById("addFileForm"),
    fileType: document.getElementById("fileType"),
    fileCustomName: document.getElementById("fileCustomName"),
    fileGroupName: document.getElementById("fileGroupName"),
    fileUploaderRole: document.getElementById("fileUploaderRole"),
    fileRandomDigits: document.getElementById("fileRandomDigits"),
    fileExternalUrl: document.getElementById("fileExternalUrl"),
    fileCaption: document.getElementById("fileCaption"),
    fileFeedback: document.getElementById("fileFeedback"),
    filesTableBody: document.getElementById("filesTableBody"),
    selectAllFilesCheckbox: document.getElementById("selectAllFilesCheckbox"),
    selectedFilesCountLabel: document.getElementById("selectedFilesCountLabel"),
    bulkFileActionsSelect: document.getElementById("bulkFileActionsSelect"),
    applyBulkFileActionBtn: document.getElementById("applyBulkFileActionBtn"),

    // /BOT-build, /Pro-plan Single-Use Link & User Control
    proActivationLinkReadonly: document.getElementById("proActivationLinkReadonly"),
    proPlanSecretKeyInput: document.getElementById("proPlanSecretKeyInput"),
    proLinkSingleUseBadge: document.getElementById("proLinkSingleUseBadge"),
    copyProActivationLinkBtn: document.getElementById("copyProActivationLinkBtn"),
    generateProKeyBtn: document.getElementById("generateProKeyBtn"),
    resetProLinkBtn: document.getElementById("resetProLinkBtn"),
    simProLinkClickBtn: document.getElementById("simProLinkClickBtn"),
    proLinkActionFeedback: document.getElementById("proLinkActionFeedback"),
    botBuilderConfigForm: document.getElementById("botBuilderConfigForm"),
    botBuildDescInput: document.getElementById("botBuildDescInput"),
    allowBotBuildToggle: document.getElementById("allowBotBuildToggle"),
    allowUserUploadToggle: document.getElementById("allowUserUploadToggle"),
    allowProPlanToggle: document.getElementById("allowProPlanToggle"),
    allowUserTwoChannelsToggle: document.getElementById("allowUserTwoChannelsToggle"),
    showStartHelpToggle: document.getElementById("showStartHelpToggle"),
    botBuilderConfigFeedback: document.getElementById("botBuilderConfigFeedback"),
    createUserBotForm: document.getElementById("createUserBotForm"),
    userBotOwnerName: document.getElementById("userBotOwnerName"),
    userBotTokenInput: document.getElementById("userBotTokenInput"),
    userBotCh1Title: document.getElementById("userBotCh1Title"),
    userBotCh1Link: document.getElementById("userBotCh1Link"),
    userBotCh2Title: document.getElementById("userBotCh2Title"),
    userBotCh2Link: document.getElementById("userBotCh2Link"),
    userBotCh3Title: document.getElementById("userBotCh3Title"),
    userBotCh3Link: document.getElementById("userBotCh3Link"),
    userBotCh4Title: document.getElementById("userBotCh4Title"),
    userBotCh4Link: document.getElementById("userBotCh4Link"),
    userBotFeedback: document.getElementById("userBotFeedback"),
    userBotsTableBody: document.getElementById("userBotsTableBody"),
    usersActivityTableBody: document.getElementById("usersActivityTableBody"),

    // Group Banner (/Group-image-description) & (/ad-group)
    groupBannerForm: document.getElementById("groupBannerForm"),
    bannerFileId: document.getElementById("bannerFileId"),
    bannerDescription: document.getElementById("bannerDescription"),
    bannerVerifiedBadge: document.getElementById("bannerVerifiedBadge"),
    bannerFeedback: document.getElementById("bannerFeedback"),
    addGroupForm: document.getElementById("addGroupForm"),
    groupTitle: document.getElementById("groupTitle"),
    groupChatId: document.getElementById("groupChatId"),
    groupInviteLink: document.getElementById("groupInviteLink"),
    groupInterval: document.getElementById("groupInterval"),
    groupFeedback: document.getElementById("groupFeedback"),
    groupsTableBody: document.getElementById("groupsTableBody"),

    // Channels
    addChannelForm: document.getElementById("addChannelForm"),
    channelTitle: document.getElementById("channelTitle"),
    channelChatId: document.getElementById("channelChatId"),
    channelUsername: document.getElementById("channelUsername"),
    channelInviteLink: document.getElementById("channelInviteLink"),
    channelFeedback: document.getElementById("channelFeedback"),
    channelsTableBody: document.getElementById("channelsTableBody"),

    // Config & Keep-Alive
    configForm: document.getElementById("configForm"),
    inputBotToken: document.getElementById("inputBotToken"),
    currentTokenHint: document.getElementById("currentTokenHint"),
    inputAdminIds: document.getElementById("inputAdminIds"),
    inputBotName: document.getElementById("inputBotName"),
    inputWebhookUrl: document.getElementById("inputWebhookUrl"),
    inputDbPath: document.getElementById("inputDbPath"),
    configFeedback: document.getElementById("configFeedback"),
    copyEnvBtn: document.getElementById("copyEnvBtn"),
    triggerKeepAliveBtn: document.getElementById("triggerKeepAliveBtn"),
    kaStatusVal: document.getElementById("kaStatusVal"),
    kaPingsVal: document.getElementById("kaPingsVal"),

    // Simulator
    simFileSelect: document.getElementById("simFileSelect"),
    simMembershipChips: document.getElementById("simMembershipChips"),
    tgBubbleContent: document.getElementById("tgBubbleContent"),
    tgDeliveredBox: document.getElementById("tgDeliveredBox"),
    tgInlineKeyboard: document.getElementById("tgInlineKeyboard"),
    simBtnStart: document.getElementById("simBtnStart"),
    simBtnDeepLink: document.getElementById("simBtnDeepLink"),
    simBtnBotBuild: document.getElementById("simBtnBotBuild"),
    simBtnUserUpload: document.getElementById("simBtnUserUpload"),
    simBtnProPlan: document.getElementById("simBtnProPlan"),
    simBtnProLinkActivate: document.getElementById("simBtnProLinkActivate"),
    simBtnGroupUpload: document.getElementById("simBtnGroupUpload"),
    simBtnGroupBanner: document.getElementById("simBtnGroupBanner"),
    simBtnAdGroup: document.getElementById("simBtnAdGroup"),
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
      runSimulation("start");
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
    els.tabPanelFiles.classList.toggle("hidden", tabName !== "files");
    if (els.tabPanelBotBuild) {
      els.tabPanelBotBuild.classList.toggle("hidden", tabName !== "botbuild");
    }
    els.tabPanelGroups.classList.toggle("hidden", tabName !== "groups");
    els.tabPanelChannels.classList.toggle("hidden", tabName !== "channels");
    els.tabPanelConfig.classList.toggle("hidden", tabName !== "config");
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

  function updateBulkSelectedUI() {
    const files = appState.files || [];
    const validIds = new Set(files.map((f) => Number(f.id)));
    Array.from(selectedFileIds).forEach((id) => {
      if (!validIds.has(id)) selectedFileIds.delete(id);
    });
    const count = selectedFileIds.size;
    if (els.selectedFilesCountLabel) {
      els.selectedFilesCountLabel.textContent = `${count} item${count === 1 ? "" : "s"} selected`;
    }
    if (els.selectAllFilesCheckbox) {
      els.selectAllFilesCheckbox.checked =
        files.length > 0 && count === files.length;
    }
  }

  function renderAll(data) {
    appState = data;
    const cfg = data.config || {};
    const stats = data.stats || {};
    const rt = cfg.runtime || {};
    const gb = data.group_banner || {};
    const bb = data.bot_builder || {};

    els.headerBotName.textContent = cfg.bot_name || "Premium File Vault";
    els.simBotTitle.textContent = cfg.bot_name || "Premium File Vault";
    els.dbPathLabel.textContent = "♾️ Permanent: " + (cfg.db_path || "bot_data.db");

    const pings = rt.keep_alive_pings ?? 1;
    const whSyncs = rt.webhook_registrations ?? 0;
    els.keepAliveText.textContent = `5m Keep-Alive: Active (${pings} pings)`;
    if (els.kaStatusVal) {
      els.kaStatusVal.textContent = `🟢 Active (Every ${rt.keep_alive_interval_seconds || 300}s)`;
    }
    if (els.kaPingsVal) {
      els.kaPingsVal.textContent = `${pings} Pings · ${whSyncs} Webhook Syncs`;
    }

    if (rt.mode === "webhook_live") {
      els.botModeDot.className = "dot dot-ok";
      els.botModeText.textContent = "24/7 Webhook: Live (<1s)";
    } else if (rt.bot_running) {
      els.botModeDot.className = "dot dot-ok";
      els.botModeText.textContent = "24/7 Fast Polling: Live";
    } else {
      els.botModeDot.className = "dot dot-ok";
      els.botModeText.textContent = "24/7 Simulator + Keep-Alive Active";
    }

    els.statChannels.textContent = String(stats.channels ?? 0);
    els.statFiles.textContent = String(stats.files ?? 0);
    if (els.statLinksMeta) {
      els.statLinksMeta.textContent = `♾️ ${stats.links ?? 0} Links · 🦄 ${stats.user_bots ?? 0} User Bots`;
    }
    if (els.statGroups) {
      els.statGroups.textContent = String(stats.groups ?? 0);
    }
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
    if (els.inputWebhookUrl && !els.inputWebhookUrl.dataset.dirty && rt.webhook_url) {
      els.inputWebhookUrl.value = rt.webhook_url;
    }

    if (els.bannerFileId && !els.bannerFileId.dataset.dirty) {
      els.bannerFileId.value = gb.banner_file_id || "";
    }
    if (els.bannerDescription && !els.bannerDescription.dataset.dirty) {
      els.bannerDescription.value = gb.description || "";
    }
    if (els.bannerVerifiedBadge) {
      els.bannerVerifiedBadge.textContent = gb.verified
        ? "✅ Verified & Active"
        : "⚠️ Pending Verification";
    }

    if (els.botBuildDescInput && !els.botBuildDescInput.dataset.dirty) {
      els.botBuildDescInput.value = bb.description || "";
    }
    if (els.proActivationLinkReadonly) {
      els.proActivationLinkReadonly.value =
        bb.pro_activation_link ||
        "https://t.me/FILE_SHARE_00_bot?start=FILE-SHARE-YU6J-IEHU-828H";
    }
    if (els.proPlanSecretKeyInput && !els.proPlanSecretKeyInput.dataset.dirty) {
      els.proPlanSecretKeyInput.value =
        bb.pro_plan_secret_key || "FILE-SHARE-YU6J-IEHU-828H";
    }
    if (els.proLinkSingleUseBadge) {
      const usedBy = Number(bb.pro_key_used_by || 0);
      els.proLinkSingleUseBadge.textContent =
        usedBy === 0
          ? "🟢 Ready (Single-Use Available)"
          : `🔴 Used by User #${usedBy} (Click Re-Arm or Generate New)`;
    }
    if (els.allowBotBuildToggle) {
      els.allowBotBuildToggle.checked = bb.allow_bot_build !== false;
    }
    if (els.allowUserUploadToggle) {
      els.allowUserUploadToggle.checked = bb.allow_user_upload !== false;
    }
    if (els.allowProPlanToggle) {
      els.allowProPlanToggle.checked = bb.allow_pro_plan !== false;
    }
    if (els.allowUserTwoChannelsToggle) {
      els.allowUserTwoChannelsToggle.checked = bb.allow_user_two_channels !== false;
    }
    if (els.showStartHelpToggle) {
      els.showStartHelpToggle.checked = bb.show_start_help !== false;
    }

    renderChannelsTable();
    renderFilesTable();
    renderGroupsTable();
    renderBotBuildTables();
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
            <button type="button" class="btn-colorful btn-color-rose btn-sm" data-del-channel="${ch.id}" aria-label="Delete channel ${escapeHtml(ch.title)}">
              🔴 🗑 Delete
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
        }
      });
    });
  }

  function renderFilesTable() {
    const files = appState.files || [];
    updateBulkSelectedUI();
    if (files.length === 0) {
      els.filesTableBody.innerHTML =
        '<tr><td colspan="6">No permanent files or links uploaded yet. Add one above.</td></tr>';
      return;
    }
    if (!selectedSimFileId || !files.some((f) => f.id === selectedSimFileId)) {
      selectedSimFileId = files[0].id;
    }

    els.filesTableBody.innerHTML = files
      .map((f) => {
        const displayName = f.custom_name || f.file_name || "file_" + f.id;
        const isChecked = selectedFileIds.has(Number(f.id));
        const grpBadge = f.group_name
          ? `<span class="perm-badge" style="background:rgba(168,85,247,0.18);color:#d8b4fe;border-color:rgba(168,85,247,0.4)">👥 ${escapeHtml(f.group_name)}</span> `
          : "";
        const isUserUpload = f.uploader_role === "user" || !f.is_permanent;
        const retentionBadge = isUserUpload
          ? `<span class="expiry-badge">⏳ 7-Day User Upload</span>`
          : `<span class="perm-badge">♾️ Lifetime (Admin)</span>`;
        return `
        <tr>
          <td class="checkbox-col">
            <input
              type="checkbox"
              class="file-row-checkbox"
              data-file-checkbox="${f.id}"
              aria-label="Select ${escapeHtml(displayName)}"
              ${isChecked ? "checked" : ""}
            />
          </td>
          <td>
            <strong>#${f.id}</strong>
            <div>${retentionBadge}</div>
          </td>
          <td>
            <div>${grpBadge}<strong>${escapeHtml(f.icon)} ${escapeHtml(displayName)}</strong></div>
            <div class="field-hint">Code: <code>${escapeHtml(f.random_code || f.id)}</code> ${f.caption ? "· " + escapeHtml(f.caption) : ""}</div>
          </td>
          <td>
            <div><code>${escapeHtml(f.share_link)}</code></div>
          </td>
          <td><strong>⬇️ ${f.downloads}</strong></td>
          <td>
            <div class="action-cell">
              <button type="button" class="btn-colorful btn-color-emerald btn-sm" data-test-file="${f.id}" aria-label="Test ${escapeHtml(displayName)} in simulator">
                🟢 ▶️ Test
              </button>
              <button type="button" class="btn-colorful btn-color-blue btn-sm" data-copy-link="${escapeHtml(f.share_link)}" aria-label="Copy link for ${escapeHtml(displayName)}">
                🔵 📋 Copy
              </button>
              <button type="button" class="btn-colorful btn-color-rose btn-sm" data-del-file="${f.id}" aria-label="Delete ${escapeHtml(displayName)}">
                🔴 🗑
              </button>
            </div>
          </td>
        </tr>
      `;
      })
      .join("");

    els.filesTableBody.querySelectorAll("[data-file-checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const fid = Number(cb.getAttribute("data-file-checkbox"));
        if (cb.checked) {
          selectedFileIds.add(fid);
        } else {
          selectedFileIds.delete(fid);
        }
        updateBulkSelectedUI();
      });
    });

    els.filesTableBody.querySelectorAll("[data-test-file]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedSimFileId = Number(btn.getAttribute("data-test-file"));
        els.simFileSelect.value = String(selectedSimFileId);
        runSimulation("deep_link", selectedSimFileId);
      });
    });

    els.filesTableBody.querySelectorAll("[data-copy-link]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const link = btn.getAttribute("data-copy-link") || "";
        if (navigator.clipboard) {
          navigator.clipboard.writeText(link).catch(() => {});
        }
        setFeedback(els.fileFeedback, `📋 Copied link: ${link}`, false);
      });
    });

    els.filesTableBody.querySelectorAll("[data-del-file]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.getAttribute("data-del-file"));
        const res = await apiFetch(`/api/files/${id}`, { method: "DELETE" });
        if (res.ok) {
          selectedFileIds.delete(id);
          renderAll(await res.json());
        }
      });
    });
  }

  // Select All Checkbox handler
  if (els.selectAllFilesCheckbox) {
    els.selectAllFilesCheckbox.addEventListener("change", () => {
      const files = appState.files || [];
      if (els.selectAllFilesCheckbox.checked) {
        files.forEach((f) => selectedFileIds.add(Number(f.id)));
      } else {
        selectedFileIds.clear();
      }
      renderFilesTable();
    });
  }

  // Bulk Actions Dropdown ('Actions' -> Bulk Delete Selected Files)
  if (els.applyBulkFileActionBtn) {
    els.applyBulkFileActionBtn.addEventListener("click", async () => {
      const actionVal = els.bulkFileActionsSelect
        ? els.bulkFileActionsSelect.value
        : "";
      if (actionVal !== "bulk_delete") {
        setFeedback(
          els.fileFeedback,
          "❌ Actions dropdown se 'Bulk Delete Selected Files' chunein!",
          true
        );
        return;
      }
      const ids = Array.from(selectedFileIds);
      if (ids.length === 0) {
        setFeedback(
          els.fileFeedback,
          "❌ Kam se kam 1 file checkbox select karein bulk delete ke liye!",
          true
        );
        return;
      }
      const res = await apiFetch("/api/files/bulk-delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: ids }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setFeedback(
          els.fileFeedback,
          err.detail || "Failed to bulk delete selected files.",
          true
        );
        return;
      }
      const payload = await res.json();
      selectedFileIds.clear();
      renderAll(payload);
      setFeedback(
        els.fileFeedback,
        `✅ Bulk deleted ${payload.deleted_count ?? ids.length} selected vault item(s)!`,
        false
      );
    });
  }

  function renderBotBuildTables() {
    if (els.userBotsTableBody) {
      const uBots = appState.user_bots || [];
      if (uBots.length === 0) {
        els.userBotsTableBody.innerHTML =
          '<tr><td colspan="5">No user bots built via /BOT-build yet. Verify a token above!</td></tr>';
      } else {
        els.userBotsTableBody.innerHTML = uBots
          .map((ub) => {
            const isProOwner = Boolean(ub.owner_is_pro);
            const chBadge = isProOwner
              ? `<span class="perm-badge" style="background:rgba(245,158,11,0.22);color:#fde68a;border-color:rgba(245,158,11,0.5)">👑 Pro: Admin Removed · ${ub.user_channels_count || 0}/4 Own Channels</span>`
              : `<span class="perm-badge">🛡️ 2 Admin</span> + <span class="perm-badge" style="background:rgba(168,85,247,0.2);color:#e9d5ff;border-color:rgba(168,85,247,0.45)">📢 ${ub.user_channels_count || 0}/2 User Channels</span>`;
            const chDetails = isProOwner
              ? `1: ${escapeHtml(ub.channel_1_title || "Not Set")} · 2: ${escapeHtml(ub.channel_2_title || "Not Set")} · 3: ${escapeHtml(ub.channel_3_title || "Not Set")} · 4: ${escapeHtml(ub.channel_4_title || "Not Set")}`
              : `1: ${escapeHtml(ub.channel_1_title || "Not Set")} · 2: ${escapeHtml(ub.channel_2_title || "Not Set")}`;
            return `
            <tr>
              <td>
                <strong>${escapeHtml(ub.bot_name)}</strong>
                <div class="field-hint">@${escapeHtml(ub.bot_username)}</div>
              </td>
              <td>
                <strong>👤 ${escapeHtml(ub.owner_name)}</strong> ${isProOwner ? '<span class="perm-badge">👑 PRO</span>' : '<span class="expiry-badge">Free</span>'}
                <div class="field-hint">Token: <code>${escapeHtml(ub.bot_token_masked || "")}</code></div>
              </td>
              <td>
                <div>${chBadge}</div>
                <div class="field-hint">${chDetails}</div>
              </td>
              <td><span class="perm-badge">🟢 24/7 Online</span></td>
              <td>
                <div class="action-cell">
                  <button type="button" class="btn-colorful btn-color-purple btn-sm" data-sim-userbot="${ub.id}" aria-label="Open ${escapeHtml(ub.bot_name)} Home Screen">
                    🦄 🏠 Home Screen
                  </button>
                  <button type="button" class="btn-colorful btn-color-rose btn-sm" data-del-userbot="${ub.id}" aria-label="Delete user bot ${escapeHtml(ub.bot_name)}">
                    🔴 🗑
                  </button>
                </div>
              </td>
            </tr>
          `;
          })
          .join("");

        els.userBotsTableBody.querySelectorAll("[data-sim-userbot]").forEach((btn) => {
          btn.addEventListener("click", () => {
            runSimulation("user_bot_home");
          });
        });

        els.userBotsTableBody.querySelectorAll("[data-del-userbot]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const ubid = btn.getAttribute("data-del-userbot");
            const res = await apiFetch(`/api/user-bots/${ubid}`, { method: "DELETE" });
            if (res.ok) {
              renderAll(await res.json());
            }
          });
        });
      }
    }

    if (els.usersActivityTableBody) {
      const users = appState.users || [];
      if (users.length === 0) {
        els.usersActivityTableBody.innerHTML =
          '<tr><td colspan="5">No users recorded yet.</td></tr>';
      } else {
        els.usersActivityTableBody.innerHTML = users
          .map((u) => {
            const isPro = Number(u.is_pro || 0) === 1;
            return `
            <tr>
              <td><code>${u.user_id}</code></td>
              <td>
                <strong>${escapeHtml(u.first_name || "User")}</strong>
                ${u.username ? `<span class="field-hint">@${escapeHtml(u.username)}</span>` : ""}
              </td>
              <td>
                ${
                  isPro
                    ? '<span class="perm-badge" style="background:rgba(245,158,11,0.22);color:#fde68a;border-color:rgba(245,158,11,0.5)">👑 YOUR PRO PLAN ACTIVE (4 Ch + Lifetime)</span>'
                    : '<span class="expiry-badge">⏳ Free Plan (2+2 Ch · 7d Upload)</span>'
                }
              </td>
              <td>
                ${u.used_bot_build ? '<span class="perm-badge">🦄 /BOT-build</span> ' : ""}
                ${u.used_user_upload ? '<span class="perm-badge">📤 /user-upload</span>' : ""}
                ${!u.used_bot_build && !u.used_user_upload ? '<span class="field-hint">—</span>' : ""}
              </td>
              <td>
                <button
                  type="button"
                  class="btn-colorful ${isPro ? "btn-color-rose" : "btn-color-amber"} btn-sm"
                  data-toggle-pro="${u.user_id}"
                  data-pro-next="${isPro ? "0" : "1"}"
                >
                  ${isPro ? "🔴 Revoke Pro" : "👑 Grant Pro (4 Ch)"}
                </button>
              </td>
            </tr>
          `;
          })
          .join("");

        els.usersActivityTableBody.querySelectorAll("[data-toggle-pro]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const uid = Number(btn.getAttribute("data-toggle-pro"));
            const nextPro = btn.getAttribute("data-pro-next") === "1";
            const res = await apiFetch("/api/users/pro", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ user_id: uid, is_pro: nextPro }),
            });
            if (res.ok) {
              renderAll(await res.json());
            }
          });
        });
      }
    }
  }

  function renderGroupsTable() {
    if (!els.groupsTableBody) return;
    const groups = appState.managed_groups || [];
    if (groups.length === 0) {
      els.groupsTableBody.innerHTML =
        '<tr><td colspan="5">No groups added via /ad-group yet. Add one above.</td></tr>';
      return;
    }
    els.groupsTableBody.innerHTML = groups
      .map(
        (g) => `
        <tr>
          <td>
            <strong>📢 ${escapeHtml(g.title)}</strong>
            <div class="field-hint">${escapeHtml(g.description || "")}</div>
          </td>
          <td><code>${g.chat_id}</code></td>
          <td><span class="perm-badge">⏱️ Post First ➜ Stay 15m ➜ Delete &amp; Repost</span></td>
          <td><strong>#${g.send_count || 0}</strong></td>
          <td>
            <div class="action-cell">
              <button type="button" class="btn-colorful btn-color-cyan btn-sm" data-rotate-group="${g.id}" aria-label="Rotate banner now for ${escapeHtml(g.title)}">
                🩵 🚀 Send &amp; Rotate Now
              </button>
              <button type="button" class="btn-colorful btn-color-rose btn-sm" data-del-group="${g.id}" aria-label="Remove group ${escapeHtml(g.title)}">
                🔴 🗑
              </button>
            </div>
          </td>
        </tr>
      `
      )
      .join("");

    els.groupsTableBody.querySelectorAll("[data-rotate-group]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const gid = Number(btn.getAttribute("data-rotate-group"));
        const res = await apiFetch("/api/groups/rotate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ group_id: gid }),
        });
        if (res.ok) {
          renderAll(await res.json());
          setFeedback(
            els.groupFeedback,
            "✅ Previous banner deleted & new 15m banner sent to group!",
            false
          );
          runSimulation("ad_group");
        }
      });
    });

    els.groupsTableBody.querySelectorAll("[data-del-group]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const gid = btn.getAttribute("data-del-group");
        const res = await apiFetch(`/api/groups/${gid}`, { method: "DELETE" });
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
          `<option value="${f.id}" ${f.id === selectedSimFileId ? "selected" : ""}>#${f.id}: ${escapeHtml(f.custom_name || f.file_name)} (${escapeHtml(f.random_code || "")})</option>`
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
              ${isJoined ? "🟢 Joined:" : "🔴 Not Joined:"} ${escapeHtml(ch.title)}
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

    const bannerHtml = payload.banner_url
      ? `<div style="margin-bottom:0.65rem;border-radius:10px;overflow:hidden;border:1px solid rgba(245,158,11,0.45)"><img src="${escapeHtml(payload.banner_url)}" alt="VIP Pro Plan Active Banner" style="width:100%;max-height:170px;object-fit:cover;display:block" /></div>`
      : "";
    els.tgBubbleContent.innerHTML = bannerHtml + (payload.message_html || "");

    if (payload.delivered_file) {
      const df = payload.delivered_file;
      els.tgDeliveredBox.classList.remove("hidden");
      const linkLine =
        df.file_type === "link" || df.external_url
          ? `<div style="margin-top:6px"><a href="${escapeHtml(df.external_url || df.tg_file_id)}" target="_blank" rel="noopener" class="btn-colorful btn-color-emerald btn-sm">🟢 🌐 Open Unlocked Direct Link</a></div>`
          : "";
      els.tgDeliveredBox.innerHTML = `
        <div><strong>${escapeHtml(df.icon || "📄")} ${escapeHtml(df.custom_name || df.file_name)}</strong> <span class="perm-badge">♾️ Permanent</span></div>
        <div style="margin-top:4px">${df.caption_html || ""}</div>
        ${linkLine}
        <div style="margin-top:6px;font-size:0.75rem;color:#6ee7b7">
          ⚡ Delivered in &lt;1s · ⬇️ Total Downloads: <strong>${df.downloads}</strong>
        </div>
      `;
    } else {
      els.tgDeliveredBox.classList.add("hidden");
      els.tgDeliveredBox.innerHTML = "";
    }

    const rows = payload.buttons || [];
    const fallbackColors = ["primary", "purple", "success", "amber", "pink", "cyan"];
    els.tgInlineKeyboard.innerHTML = rows
      .map(
        (row, rIdx) => `
        <div class="tg-kb-row" style="grid-template-columns: repeat(${row.length}, 1fr)">
          ${row
            .map((b, bIdx) => {
              const cStyle = b.color || fallbackColors[(rIdx + bIdx) % fallbackColors.length];
              return `<button type="button" class="tg-kb-btn tg-kb-${escapeHtml(cStyle)}" data-sim-kb="${escapeHtml(b.action)}">${escapeHtml(b.text)}</button>`;
            })
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
        } else if (act.startsWith("sim:")) {
          runSimulation(act.split(":")[1]);
        } else if (act.startsWith("url:")) {
          const targetUrl = act.slice(4);
          if (navigator.clipboard) {
            navigator.clipboard.writeText(targetUrl).catch(() => {});
          }
        }
      });
    });
  }

  // One-Click Pro Activation Link Controls
  if (els.copyProActivationLinkBtn) {
    els.copyProActivationLinkBtn.addEventListener("click", () => {
      const link = els.proActivationLinkReadonly
        ? els.proActivationLinkReadonly.value
        : "";
      if (navigator.clipboard && link) {
        navigator.clipboard.writeText(link).catch(() => {});
      }
      setFeedback(
        els.proLinkActionFeedback,
        `📋 Copied One-Click Pro Link: ${link}`,
        false
      );
    });
  }

  if (els.generateProKeyBtn) {
    els.generateProKeyBtn.addEventListener("click", async () => {
      const res = await apiFetch("/api/pro-plan/generate-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        if (els.proPlanSecretKeyInput) {
          delete els.proPlanSecretKeyInput.dataset.dirty;
        }
        renderAll(data);
        setFeedback(
          els.proLinkActionFeedback,
          `🎲 Generated New Key & Single-Use Link: ${data.pro_activation_link}`,
          false
        );
      }
    });
  }

  if (els.resetProLinkBtn) {
    els.resetProLinkBtn.addEventListener("click", async () => {
      const res = await apiFetch("/api/pro-plan/reset-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        renderAll(await res.json());
        setFeedback(
          els.proLinkActionFeedback,
          "🔄 Single-Use Pro Activation Link re-armed & ready for next user click!",
          false
        );
      }
    });
  }

  if (els.simProLinkClickBtn) {
    els.simProLinkClickBtn.addEventListener("click", () => {
      runSimulation("pro_link_activate");
    });
  }

  // Save /BOT-build-description & User Feature Permissions
  if (els.botBuilderConfigForm) {
    els.botBuilderConfigForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const desc = els.botBuildDescInput.value.trim();
      const secretKey = els.proPlanSecretKeyInput
        ? els.proPlanSecretKeyInput.value.trim()
        : "FILE-SHARE-YU6J-IEHU-828H";
      if (!desc) {
        setFeedback(
          els.botBuilderConfigFeedback,
          "❌ /BOT-build-description khali nahi ho sakta!",
          true
        );
        return;
      }
      const res = await apiFetch("/api/bot-builder/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: desc,
          allow_bot_build: els.allowBotBuildToggle.checked,
          allow_user_upload: els.allowUserUploadToggle.checked,
          allow_pro_plan: els.allowProPlanToggle
            ? els.allowProPlanToggle.checked
            : true,
          allow_user_two_channels: els.allowUserTwoChannelsToggle.checked,
          show_start_help: els.showStartHelpToggle
            ? els.showStartHelpToggle.checked
            : true,
          pro_plan_secret_key: secretKey || "FILE-SHARE-YU6J-IEHU-828H",
          reset_single_use: true,
        }),
      });
      if (res.ok) {
        renderAll(await res.json());
        setFeedback(
          els.botBuilderConfigFeedback,
          "✅ /start Feature Permissions, Pro Key & Description saved!",
          false
        );
        runSimulation("start");
      }
    });
  }

  // Create / Verify User Bot via @BotFather Token
  if (els.createUserBotForm) {
    els.createUserBotForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ownerName = els.userBotOwnerName.value.trim();
      const token = els.userBotTokenInput.value.trim();
      const c1Title = els.userBotCh1Title.value.trim();
      const c1Link = els.userBotCh1Link.value.trim();
      const c2Title = els.userBotCh2Title.value.trim();
      const c2Link = els.userBotCh2Link.value.trim();
      const c3Title = els.userBotCh3Title ? els.userBotCh3Title.value.trim() : "";
      const c3Link = els.userBotCh3Link ? els.userBotCh3Link.value.trim() : "";
      const c4Title = els.userBotCh4Title ? els.userBotCh4Title.value.trim() : "";
      const c4Link = els.userBotCh4Link ? els.userBotCh4Link.value.trim() : "";

      if (!ownerName || !token) {
        setFeedback(
          els.userBotFeedback,
          "❌ User Name aur @BotFather Token daalna zaroori hai!",
          true
        );
        return;
      }

      const res = await apiFetch("/api/user-bots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          owner_name: ownerName,
          bot_token: token,
          channel_1_title: c1Title,
          channel_1_link: c1Link,
          channel_2_title: c2Title,
          channel_2_link: c2Link,
          channel_3_title: c3Title,
          channel_3_link: c3Link,
          channel_4_title: c4Title,
          channel_4_link: c4Link,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setFeedback(
          els.userBotFeedback,
          err.detail || "Could not verify @BotFather token.",
          true
        );
        return;
      }
      els.userBotOwnerName.value = "";
      els.userBotTokenInput.value = "";
      els.userBotCh1Title.value = "";
      els.userBotCh1Link.value = "";
      els.userBotCh2Title.value = "";
      els.userBotCh2Link.value = "";
      if (els.userBotCh3Title) els.userBotCh3Title.value = "";
      if (els.userBotCh3Link) els.userBotCh3Link.value = "";
      if (els.userBotCh4Title) els.userBotCh4Title.value = "";
      if (els.userBotCh4Link) els.userBotCh4Link.value = "";
      renderAll(await res.json());
      setFeedback(
        els.userBotFeedback,
        "🦄 ✅ Token Verified! User Bot is now 24/7 Online!",
        false
      );
      runSimulation("user_bot_home");
    });
  }

  // Trigger 5-Minute Keep-Alive Heartbeat manually
  if (els.triggerKeepAliveBtn) {
    els.triggerKeepAliveBtn.addEventListener("click", async () => {
      const customWh = els.inputWebhookUrl ? els.inputWebhookUrl.value.trim() : "";
      const res = await apiFetch("/api/keepalive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ webhook_url: customWh }),
      });
      if (res.ok) {
        const updated = await res.json();
        renderAll(updated);
        setFeedback(
          els.configFeedback,
          "💓 5-Minute Keep-Alive Heartbeat executed & Webhook registered with Telegram API!",
          false
        );
      }
    });
  }

  els.configForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const adminIds = els.inputAdminIds.value.trim();
    const botName = els.inputBotName.value.trim();
    const dbPath = els.inputDbPath.value.trim();
    const botToken = els.inputBotToken.value.trim();
    const webhookUrl = els.inputWebhookUrl ? els.inputWebhookUrl.value.trim() : "";

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
      webhook_url: webhookUrl,
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
      "✅ Saved to .env & synced with 24/7 Keep-Alive Engine!",
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
    setFeedback(els.channelFeedback, "✅ Channel saved permanently!", false);
  });

  els.addFileForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const customName = els.fileCustomName.value.trim();
    const groupName = els.fileGroupName.value.trim();
    const uploaderRole = els.fileUploaderRole ? els.fileUploaderRole.value : "admin";
    const fileType = els.fileType.value;
    const randomDigits = Number(els.fileRandomDigits.value) || 6;
    const externalUrl = els.fileExternalUrl.value.trim();
    const caption = els.fileCaption.value.trim();

    if (!customName) {
      setFeedback(
        els.fileFeedback,
        "❌ Custom Name (NAME) daalna zaroori hai!",
        true
      );
      return;
    }

    const res = await apiFetch("/api/files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        custom_name: customName,
        file_name: customName,
        group_name: groupName,
        uploader_role: uploaderRole,
        file_type: fileType,
        random_digits: randomDigits,
        external_url: externalUrl,
        tg_file_id: externalUrl,
        caption,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setFeedback(
        els.fileFeedback,
        err.detail || "Could not save item.",
        true
      );
      return;
    }
    const payload = await res.json();
    els.fileCustomName.value = "";
    els.fileGroupName.value = "";
    els.fileExternalUrl.value = "";
    els.fileCaption.value = "";
    selectedSimFileId = payload.created_file_id || selectedSimFileId;
    renderAll(payload);
    const created = (payload.files || []).find((f) => f.id === payload.created_file_id);
    const policyMsg =
      uploaderRole === "user"
        ? "⚠️ Saved for 1 Week (7-Day Auto-Delete)"
        : "♾️ Saved for Lifetime (Admin)";
    setFeedback(
      els.fileFeedback,
      `✅ ${policyMsg}! Link: ${created ? created.share_link : ""}`,
      false
    );
    runSimulation("deep_link", selectedSimFileId);
  });

  if (els.groupBannerForm) {
    els.groupBannerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const bannerFid = els.bannerFileId.value.trim();
      const desc = els.bannerDescription.value.trim();
      if (!bannerFid || !desc) {
        setFeedback(
          els.bannerFeedback,
          "❌ Banner Image aur Description dono daalna zaroori hai.",
          true
        );
        return;
      }
      const res = await apiFetch("/api/group-banner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          banner_file_id: bannerFid,
          description: desc,
          banner_type: "photo",
        }),
      });
      if (res.ok) {
        renderAll(await res.json());
        setFeedback(
          els.bannerFeedback,
          "✅ /Group-image-description Verified & Permanently Saved!",
          false
        );
        runSimulation("group_banner");
      }
    });
  }

  if (els.addGroupForm) {
    els.addGroupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = els.groupTitle.value.trim();
      const chatId = Number(els.groupChatId.value.trim());
      const inviteLink = els.groupInviteLink.value.trim();
      const intervalMin = Number(els.groupInterval.value) || 15;

      if (!title || !chatId) {
        setFeedback(
          els.groupFeedback,
          "❌ Group Name aur Numeric Chat ID zaroori hai.",
          true
        );
        return;
      }
      const res = await apiFetch("/api/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          chat_id: chatId,
          invite_link: inviteLink,
          interval_minutes: intervalMin,
        }),
      });
      if (res.ok) {
        els.groupTitle.value = "";
        els.groupChatId.value = "";
        els.groupInviteLink.value = "";
        renderAll(await res.json());
        setFeedback(
          els.groupFeedback,
          "✅ Group added via /ad-group! 15-Minute Auto Banner Send & Delete active.",
          false
        );
        runSimulation("ad_group");
      }
    });
  }

  els.simFileSelect.addEventListener("change", () => {
    selectedSimFileId = Number(els.simFileSelect.value);
    runSimulation("deep_link", selectedSimFileId);
  });

  els.simBtnStart.addEventListener("click", () => runSimulation("start"));
  els.simBtnDeepLink.addEventListener("click", () =>
    runSimulation("deep_link", selectedSimFileId)
  );
  if (els.simBtnBotBuild) {
    els.simBtnBotBuild.addEventListener("click", () =>
      runSimulation("bot_build")
    );
  }
  if (els.simBtnUserUpload) {
    els.simBtnUserUpload.addEventListener("click", () =>
      runSimulation("user_upload")
    );
  }
  if (els.simBtnProPlan) {
    els.simBtnProPlan.addEventListener("click", () =>
      runSimulation("pro_plan")
    );
  }
  if (els.simBtnProLinkActivate) {
    els.simBtnProLinkActivate.addEventListener("click", () =>
      runSimulation("pro_link_activate")
    );
  }
  if (els.simBtnGroupUpload) {
    els.simBtnGroupUpload.addEventListener("click", () =>
      runSimulation("group_upload")
    );
  }
  if (els.simBtnGroupBanner) {
    els.simBtnGroupBanner.addEventListener("click", () =>
      runSimulation("group_banner")
    );
  }
  if (els.simBtnAdGroup) {
    els.simBtnAdGroup.addEventListener("click", () => runSimulation("ad_group"));
  }
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
