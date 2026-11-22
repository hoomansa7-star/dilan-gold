// -*- coding: utf-8 -*-
// Dilan Gold ERP - Workshop Application Script

const API_BASE = "";

// Global State
let activeTab = "daily-ledger";
let isNightMode = false;
let currentWorkerFilter = "all";
let currentStageFilter = "all";
let currentSearchQuery = "";

// Stage Configurations & Tags
const stageConfig = {
    skin: { label: "پوست", class: "stage-skin" },
    polish: { label: "پرداخت", class: "stage-polish" },
    melting: { label: "ذوب", class: "stage-melting" },
    rolling: { label: "نورد", class: "stage-rolling" },
    laser: { label: "لیزر", class: "stage-laser" },
    melgat: { label: "ملگات", class: "stage-melgat" },
    stripping: { label: "لایه‌برداری", class: "stage-stripping" },
    swarf: { label: "سوآله", class: "stage-swarf" },
    wire_solder: { label: "لحیم و مفتول", class: "stage-wire" }
};

// Real Notebook Shift Data (Wednesday 1405/07/29)
let ledgerRows = [
    { id: 1, time: "۰۸:۳۰", stage: "skin", worker: "نیما", item: "پوست و ملگات گل (سایز ۱ تا ۶)", count: 16, in: 12.510, out: 12.340, loss: -0.170, notes: "سایز ۱ تا ۶ (دفتر صفحه ۱)" },
    { id: 2, time: "۰۸:۴۵", stage: "skin", worker: "امیر", item: "پوست و ملگات گل (سایز ۱ تا ۶)", count: 17, in: 14.250, out: 14.090, loss: -0.160, notes: "سایز ۱ تا ۶ (دفتر صفحه ۱)" },
    { id: 3, time: "۰۹:۱۵", stage: "skin", worker: "نیما", item: "پوست انگشتر متفرقه", count: 2, in: 5.850, out: 5.440, loss: -0.410, notes: "انگشتر متفرقه (صفحه ۱)" },
    { id: 4, time: "۰۹:۳۰", stage: "skin", worker: "امیر", item: "پوست انگشتر متفرقه", count: 2, in: 6.040, out: 4.960, loss: -1.080, notes: "انگشتر متفرقه (صفحه ۱)" },
    { id: 5, time: "۱۰:۰۰", stage: "skin", worker: "نیما", item: "پوست انگشتر و نگین", count: 5, in: 6.910, out: 6.420, loss: -0.490, notes: "صفحه ۲ دفترچه" },
    { id: 6, time: "۱۰:۱۵", stage: "skin", worker: "امیر", item: "پوست انگشتر و نگین", count: 6, in: 8.220, out: 7.480, loss: -0.740, notes: "صفحه ۲ دفترچه" },
    { id: 7, time: "۱۰:۴۵", stage: "skin", worker: "عطا", item: "پوست انگشتر و نگین", count: 7, in: 8.710, out: 8.500, loss: -0.210, notes: "صفحه ۲ دفترچه" },
    { id: 8, time: "۱۱:۱۵", stage: "swarf", worker: "عطا", item: "انگشتر و نگین سایز ۳ عطا", count: 1, in: 1.100, out: 0.000, loss: -1.100, notes: "یک عدد انگشتر به سوآله رفت (وزن بعد: ۷.۴۰)" },
    { id: 9, time: "۱۱:۴۵", stage: "polish", worker: "نیما", item: "پرداخت انگشتر متفرقه", count: 2, in: 5.440, out: 5.280, loss: -0.160, notes: "پرداخت نهایی (صفحه ۲)" },
    { id: 10, time: "۱۲:۱۰", stage: "polish", worker: "امیر", item: "پرداخت انگشتر متفرقه", count: 2, in: 4.960, out: 4.820, loss: -0.140, notes: "پرداخت نهایی (صفحه ۲)" },
    { id: 11, time: "۱۲:۳۰", stage: "polish", worker: "نیما", item: "پرداخت انگشتر و نگین", count: 5, in: 6.420, out: 6.350, loss: -0.070, notes: "پرداخت نهایی (صفحه ۲)" },
    { id: 12, time: "۱۳:۰۰", stage: "polish", worker: "امیر", item: "پرداخت انگشتر و نگین", count: 6, in: 7.480, out: 7.350, loss: -0.130, notes: "پرداخت نهایی (صفحه ۲)" },
    { id: 13, time: "۱۳:۲۰", stage: "polish", worker: "عطا", item: "پرداخت انگشتر و نگین", count: 6, in: 7.410, out: 7.230, loss: -0.180, notes: "پرداخت نهایی (صفحه ۲)" }
];

// Ingot Data for Melting Calculator (قانون ۱)
let multiIngots = [
    { title: "شمش ۱ (ریخته)", weight: 80.000, carat: 740 },
    { title: "شمش ۲ (متفرقه)", weight: 100.000, carat: 765 },
    { title: "شمش ۳ (آبشده)", weight: 45.000, carat: 750 },
    { title: "شمش ۴ (متفرقه)", weight: 25.000, carat: 780 }
];

// Formatting Functions
function formatDigits(val) {
    if (val === null || val === undefined) return "";
    return String(val).replace(/[0-9]/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
}

function formatGold(val) {
    if (val === null || val === undefined || isNaN(val)) return "۰.۰۰۰";
    const num = Number(val).toFixed(3);
    const parts = num.split(".");
    const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, "،");
    return formatDigits(`${intPart}.${parts[1]}`);
}

// Toast System
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    const colors = {
        success: "bg-emerald-950 border-emerald-500 text-emerald-100",
        danger: "bg-rose-950 border-rose-600 text-rose-100",
        info: "bg-slate-900 border-amber-500 text-amber-100"
    };
    toast.className = `border px-4 py-3 rounded-xl shadow-xl text-xs flex items-center justify-between gap-3 transition-all duration-300 transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `
        <span class="font-bold">${message}</span>
        <button onclick="this.parentElement.remove()" class="text-xs opacity-70 hover:opacity-100 font-bold">✕</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.classList.remove("translate-y-2", "opacity-0"), 10);
    setTimeout(() => {
        toast.classList.add("opacity-0", "-translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// -------------------------------------------------------------
// 1. Tab Switching
// -------------------------------------------------------------
function switchMainTab(tabId) {
    activeTab = tabId;

    const allTabs = [
        "daily-ledger",
        "workshop-matrix",
        "bench-quickpad",
        "melting-calc",
        "craftsmen-payroll",
        "crucible-refining"
    ];

    // Hide all tab sections
    allTabs.forEach(t => {
        const sec = document.getElementById(`tab-${t}`);
        if (sec) sec.classList.add("hidden");
    });

    // Show active section
    const targetSection = document.getElementById(`tab-${tabId}`);
    if (targetSection) targetSection.classList.remove("hidden");

    // Update tab button styles
    allTabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        if (!btn) return;
        if (t === tabId) {
            btn.className = "main-nav-tab flex items-center gap-2 px-3.5 py-2.5 rounded-lg font-bold text-xs bg-amber-600 text-white transition-all shadow-sm shrink-0";
        } else {
            btn.className = "main-nav-tab flex items-center gap-2 px-3.5 py-2.5 rounded-lg font-bold text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-subtle)] transition-all shrink-0";
        }
    });

    if (tabId === "melting-calc") {
        renderIngotRows();
    } else if (tabId === "craftsmen-payroll") {
        loadCraftsmenPayroll();
        loadSettlements();
    } else if (tabId === "crucible-refining") {
        loadCruciblesAndRefining();
        runSolderCalculation();
    }
}

// -------------------------------------------------------------
// 2. Workshop Table & Filtering
// -------------------------------------------------------------
function getWorkerAvatarClass(name) {
    if (name.includes("نیما")) return "avatar-nima";
    if (name.includes("امیر")) return "avatar-amir";
    if (name.includes("عطا")) return "avatar-ata";
    return "avatar-other";
}

function renderWorkshopTable() {
    const tbody = document.getElementById("workshop-ledger-tbody");
    if (!tbody) return;

    const filtered = ledgerRows.filter(r => {
        const matchWorker = currentWorkerFilter === "all" || r.worker === currentWorkerFilter;
        const matchStage = currentStageFilter === "all" || r.stage === currentStageFilter;
        const matchSearch = !currentSearchQuery || 
            r.item.toLowerCase().includes(currentSearchQuery.toLowerCase()) ||
            r.worker.toLowerCase().includes(currentSearchQuery.toLowerCase()) ||
            (r.notes && r.notes.toLowerCase().includes(currentSearchQuery.toLowerCase()));
        return matchWorker && matchStage && matchSearch;
    });

    // Update count badge
    const countBadge = document.getElementById("table-row-count-badge");
    if (countBadge) countBadge.innerText = `${formatDigits(filtered.length)} ردیف`;

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="text-center py-8 text-[var(--text-muted)] text-xs">
                    موردی با فیلترهای انتخابی یافت نشد.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map((r, idx) => {
        const stageInfo = stageConfig[r.stage] || { label: r.stage, class: "stage-skin" };
        const avatarClass = getWorkerAvatarClass(r.worker);
        const firstLetter = r.worker ? r.worker.trim()[0] : "ک";

        return `
            <tr>
                <td class="text-center font-mono font-bold text-[var(--text-muted)]">${formatDigits(idx + 1)}</td>
                <td class="text-center font-mono text-xs text-[var(--text-muted)]">${r.time || "--:--"}</td>
                <td class="text-center">
                    <span class="stage-tag ${stageInfo.class}">${stageInfo.label}</span>
                </td>
                <td>
                    <div class="worker-badge">
                        <span class="worker-avatar ${avatarClass}">${firstLetter}</span>
                        <span>${r.worker}</span>
                    </div>
                </td>
                <td class="font-medium text-[var(--text-primary)]">${r.item}</td>
                <td class="text-center font-mono font-bold">${formatDigits(r.count)}</td>
                <td class="text-center font-mono font-bold">${formatGold(r.in)}</td>
                <td class="text-center font-mono font-bold text-emerald-700 dark:text-emerald-400">${formatGold(r.out)}</td>
                <td class="text-center">
                    <span class="loss-badge text-xs">${formatGold(r.loss)}</span>
                </td>
                <td class="text-xs text-[var(--text-muted)]">
                    <div class="flex items-center justify-between gap-2">
                        <span>${r.notes || "-"}</span>
                        ${r.stage !== "swarf" ? `
                            <button onclick="sendItemToSwarf(${r.id})" class="text-[10px] text-rose-600 hover:text-rose-800 dark:text-rose-400 border border-rose-200 dark:border-rose-900 px-1.5 py-0.5 rounded hover:bg-rose-50 dark:hover:bg-rose-950/30 whitespace-nowrap" title="انتقال به ظرف سوآله چرم">
                                به سوآله
                            </button>
                        ` : ''}
                    </div>
                </td>
                <td class="text-center">
                    <button onclick="deleteLedgerRow(${r.id})" class="text-rose-600 hover:text-rose-800 dark:text-rose-400 text-xs font-bold px-2 py-1 rounded hover:bg-rose-500/10 transition-colors" title="حذف ردیف">
                        ✕
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

function filterByWorker(worker) {
    currentWorkerFilter = worker;
    document.querySelectorAll(".worker-filter-btn").forEach(btn => {
        if (btn.dataset.worker === worker) {
            btn.className = "worker-filter-btn px-2 py-0.5 rounded font-bold bg-amber-600 text-white";
        } else {
            btn.className = "worker-filter-btn px-2 py-0.5 rounded font-bold text-[var(--text-muted)] hover:text-[var(--text-primary)]";
        }
    });
    renderWorkshopTable();
}

function filterByStage(stage) {
    currentStageFilter = stage;
    renderWorkshopTable();
}

function filterBySearch(query) {
    currentSearchQuery = query.trim();
    renderWorkshopTable();
}

// -------------------------------------------------------------
// 3. Quick Row Entry Form
// -------------------------------------------------------------
function calculateFormLiveLoss() {
    const inVal = parseFloat(document.getElementById("form-weight-in").value) || 0.0;
    const outVal = parseFloat(document.getElementById("form-weight-out").value) || 0.0;
    const badge = document.getElementById("form-live-loss-badge");
    if (!badge) return;

    if (inVal > 0 && outVal >= 0) {
        const loss = Number((outVal - inVal).toFixed(3));
        badge.innerText = `${formatGold(loss)} گرم`;
    } else {
        badge.innerText = "۰.۰۰۰ گرم";
    }
}

function handleQuickRowSubmit(e) {
    e.preventDefault();

    const stage = document.getElementById("form-stage").value;
    const worker = document.getElementById("form-worker").value.trim();
    const item = document.getElementById("form-item").value.trim();
    const count = parseInt(document.getElementById("form-count").value) || 1;
    const weightIn = parseFloat(document.getElementById("form-weight-in").value) || 0.0;
    const weightOut = parseFloat(document.getElementById("form-weight-out").value) || 0.0;

    if (!worker || !item || weightIn <= 0) {
        showToast("لطفاً اطلاعات مرحله و وزن ورودی را کامل وارد نمایید.", "danger");
        return;
    }

    const loss = Number((weightOut - weightIn).toFixed(3));
    const now = new Date();
    const timeStr = formatDigits(`${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`);
    const newId = ledgerRows.length > 0 ? Math.max(...ledgerRows.map(r => r.id)) + 1 : 1;

    ledgerRows.unshift({
        id: newId,
        time: timeStr,
        stage: stage,
        worker: worker,
        item: item,
        count: count,
        in: weightIn,
        out: weightOut,
        loss: loss,
        notes: "ثبت مستقیم در دفتر"
    });

    // Reset Form fields
    document.getElementById("form-item").value = "";
    document.getElementById("form-count").value = "1";
    document.getElementById("form-weight-in").value = "";
    document.getElementById("form-weight-out").value = "";
    document.getElementById("form-live-loss-badge").innerText = "۰.۰۰۰ گرم";

    renderWorkshopTable();
    updateTopMetrics();
    showToast(`مرحله برای ${worker} با کسری ${formatGold(loss)} گرم ثبت شد.`, "success");
}

function sendItemToSwarf(id) {
    const row = ledgerRows.find(r => r.id === id);
    if (!row) return;

    const swarfWeight = prompt(`وزن قطعه منتقل‌شده به سوآله برای «${row.item}» را وارد کنید (گرم):`, "1.100");
    if (!swarfWeight) return;

    const w = parseFloat(swarfWeight);
    if (isNaN(w) || w <= 0) {
        showToast("وزن نامعتبر است.", "danger");
        return;
    }

    // Add Swarf Incident Row
    const now = new Date();
    const timeStr = formatDigits(`${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`);
    const newId = Math.max(...ledgerRows.map(r => r.id)) + 1;

    ledgerRows.unshift({
        id: newId,
        time: timeStr,
        stage: "swarf",
        worker: row.worker,
        item: `انتقال به سوآله: ${row.item}`,
        count: 1,
        in: w,
        out: 0.000,
        loss: -w,
        notes: `قطعه خراب‌شده / پودر تراش چرم ${row.worker}`
    });

    renderWorkshopTable();
    updateTopMetrics();
    showToast(`${formatGold(w)} گرم به موجودی سوآله چرم اضافه شد.`, "info");
}

function deleteLedgerRow(id) {
    if (confirm("آیا از حذف این ردیف مطمئن هستید؟")) {
        ledgerRows = ledgerRows.filter(r => r.id !== id);
        renderWorkshopTable();
        updateTopMetrics();
        showToast("ردیف حذف شد.", "info");
    }
}

function updateTopMetrics() {
    let totalIn = 0;
    let totalOut = 0;
    let totalSwarf = 0;
    let totalLoss = 0;

    ledgerRows.forEach(r => {
        totalIn += Number(r.in);
        totalOut += Number(r.out);
        totalLoss += Number(r.loss);
        if (r.stage === "swarf") {
            totalSwarf += Number(r.in);
        }
    });

    const elIn = document.getElementById("metric-in-gold");
    const elOut = document.getElementById("metric-out-gold");
    const elSwarf = document.getElementById("metric-swarf-gold");
    const elLoss = document.getElementById("metric-total-loss");

    if (elIn) elIn.innerText = formatGold(totalIn);
    if (elOut) elOut.innerText = formatGold(totalOut);
    if (elSwarf) elSwarf.innerText = formatGold(totalSwarf > 0 ? totalSwarf : 1.100);
    if (elLoss) elLoss.innerText = formatGold(totalLoss);
}

// -------------------------------------------------------------
// 4. Multi-Ingot Melting Logic (بند ۱ همکار)
// -------------------------------------------------------------
function renderIngotRows() {
    const tbody = document.getElementById("multi-ingots-tbody");
    if (!tbody) return;

    tbody.innerHTML = multiIngots.map((ingot, idx) => {
        const equiv = (ingot.weight * ingot.carat) / 750;
        return `
            <tr>
                <td class="text-center font-mono font-bold text-[var(--text-muted)]">${formatDigits(idx + 1)}</td>
                <td>
                    <input type="text" value="${ingot.title}" onchange="multiIngots[${idx}].title = this.value" class="w-full bg-transparent border-b border-[var(--border-color)] px-1 py-0.5 outline-none font-medium">
                </td>
                <td class="text-center">
                    <input type="number" step="0.001" value="${ingot.weight}" oninput="multiIngots[${idx}].weight = parseFloat(this.value) || 0; calculateMultiMeltingTotals()" class="w-24 font-mono text-center dilan-input p-1">
                </td>
                <td class="text-center">
                    <input type="number" value="${ingot.carat}" oninput="multiIngots[${idx}].carat = parseInt(this.value) || 750; calculateMultiMeltingTotals()" class="w-20 font-mono text-center dilan-input p-1">
                </td>
                <td class="text-center font-mono font-bold text-amber-700 dark:text-amber-400">
                    ${formatGold(equiv)}
                </td>
                <td class="text-center">
                    <button onclick="removeIngotRow(${idx})" class="text-rose-600 hover:text-rose-800 font-bold">✕</button>
                </td>
            </tr>
        `;
    }).join("");

    calculateMultiMeltingTotals();
}

function addIngotRow() {
    const nextNum = multiIngots.length + 1;
    multiIngots.push({
        title: `شمش ${formatDigits(nextNum)} متفرقه`,
        weight: 50.000,
        carat: 750
    });
    renderIngotRows();
}

function removeIngotRow(idx) {
    if (multiIngots.length <= 1) {
        showToast("حداقل یک شمش باید در لیست باشد.", "danger");
        return;
    }
    multiIngots.splice(idx, 1);
    renderIngotRows();
}

function calculateMultiMeltingTotals() {
    let rawTotal = 0;
    let equiv750Total = 0;
    let alloyNeeded = 0;

    multiIngots.forEach(i => {
        const w = Number(i.weight) || 0;
        const c = Number(i.carat) || 750;
        rawTotal += w;
        const eq = (w * c) / 750;
        equiv750Total += eq;

        // Ingot carat > 750 requires alloy (بار مس/نقره)
        if (c > 750) {
            alloyNeeded += (w * (c - 750)) / 750;
        }
    });

    document.getElementById("melt-total-raw").innerText = `${formatGold(rawTotal)} گرم`;
    document.getElementById("melt-total-750").innerText = `${formatGold(equiv750Total)} گرم`;
    document.getElementById("melt-alloy-needed").innerText = `${formatGold(alloyNeeded)} گرم`;

    calculateMeltingLoss();
}

function calculateMeltingLoss() {
    const outWeight = parseFloat(document.getElementById("melt-output-weight")?.value) || 0.0;
    const badge = document.getElementById("melt-loss-badge");
    if (!badge) return;

    if (outWeight > 0) {
        let equiv750Total = 0;
        let alloyNeeded = 0;
        multiIngots.forEach(i => {
            const w = Number(i.weight) || 0;
            const c = Number(i.carat) || 750;
            equiv750Total += (w * c) / 750;
            if (c > 750) alloyNeeded += (w * (c - 750)) / 750;
        });

        // Melting loss = (Total 750 + Alloy) - Output
        const loss = Number((outWeight - (equiv750Total + alloyNeeded)).toFixed(3));
        badge.innerText = `${formatGold(loss)} گرم`;
    } else {
        badge.innerText = "۰.۰۰۰ گرم";
    }
}

function applyMeltingToLedger() {
    const outWeight = parseFloat(document.getElementById("melt-output-weight")?.value) || 0.0;
    if (outWeight <= 0) {
        showToast("لطفاً وزن شمش‌های خروجی بعد از ذوب را وارد نمایید.", "danger");
        return;
    }

    let equiv750Total = 0;
    let alloyNeeded = 0;
    multiIngots.forEach(i => {
        const w = Number(i.weight) || 0;
        const c = Number(i.carat) || 750;
        equiv750Total += (w * c) / 750;
        if (c > 750) alloyNeeded += (w * (c - 750)) / 750;
    });

    const totalInWithAlloy = equiv750Total + alloyNeeded;
    const loss = Number((outWeight - totalInWithAlloy).toFixed(3));

    const now = new Date();
    const timeStr = formatDigits(`${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`);
    const newId = ledgerRows.length > 0 ? Math.max(...ledgerRows.map(r => r.id)) + 1 : 1;

    ledgerRows.unshift({
        id: newId,
        time: timeStr,
        stage: "melting",
        worker: "مسئول ذوب",
        item: `ذوب ۴ شمش (با ${formatGold(alloyNeeded)} g بار آلیاژ)`,
        count: multiIngots.length,
        in: Number(totalInWithAlloy.toFixed(3)),
        out: outWeight,
        loss: loss,
        notes: "محاسبه خودکار ماشین‌حساب ذوب"
    });

    renderWorkshopTable();
    updateTopMetrics();
    switchMainTab("daily-ledger");
    showToast(`عملیات ذوب با کسری ${formatGold(loss)} گرم به دفتر کارگاه اضافه شد.`, "success");
}

// -------------------------------------------------------------
// 5. Nightly Audit Modal (بند ۹ همکار - کنترل طلای گم‌شده)
// -------------------------------------------------------------
function openNightlyAuditModal() {
    document.getElementById("modal-audit")?.classList.remove("hidden");
    runGoldAuditCheck();
}

function closeNightlyAuditModal() {
    document.getElementById("modal-audit")?.classList.add("hidden");
}

function runGoldAuditCheck() {
    const inGold = parseFloat(document.getElementById("audit-in-gold")?.value) || 0.0;
    const outGold = parseFloat(document.getElementById("audit-out-gold")?.value) || 0.0;
    const swarfGold = parseFloat(document.getElementById("audit-swarf-gold")?.value) || 0.0;
    const lossGold = parseFloat(document.getElementById("audit-loss-gold")?.value) || 0.0;

    // Unconnected loss = inGold - (outGold + swarfGold + lossGold)
    const unconnected = Number((inGold - (outGold + swarfGold + lossGold)).toFixed(3));
    const valEl = document.getElementById("audit-unconnected-val");
    const msgEl = document.getElementById("audit-status-msg");
    const boxEl = document.getElementById("audit-res-box");

    if (valEl) valEl.innerText = `${formatGold(unconnected)} گرم`;

    if (Math.abs(unconnected) < 0.005) {
        if (boxEl) boxEl.className = "p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-xs";
        if (valEl) valEl.className = "font-mono text-sm text-emerald-800 dark:text-emerald-300 font-black";
        if (msgEl) msgEl.innerText = "تراز کارگاه ۱۰۰٪ متصل و بسته است؛ هیچ طلای مفقودی در شیفت وجود ندارد.";
    } else {
        if (boxEl) boxEl.className = "p-3.5 rounded-xl border border-rose-500/40 bg-rose-500/15 text-xs animate-pulse";
        if (valEl) valEl.className = "font-mono text-sm text-rose-800 dark:text-rose-300 font-black";
        if (msgEl) msgEl.innerText = `هشدار: عدم تطابق به میزان ${formatGold(unconnected)} گرم! طلای گم‌شده یا ثبت‌نشده در مراحل وجود دارد.`;
    }
}

// -------------------------------------------------------------
// 6. Excel Export
// -------------------------------------------------------------
function exportShiftExcel() {
    showToast("در حال آماده‌سازی و دانلود فایل اکسل کارگاه...", "info");
    const downloadUrl = `${API_BASE}/api/workshop/shifts/1/export/excel`;
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = "Dilan_Gold_Workshop_Ledger.xlsx";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// -------------------------------------------------------------
// 7. Night Mode
// -------------------------------------------------------------
function toggleNightMode() {
    isNightMode = !isNightMode;
    document.body.classList.toggle("dark", isNightMode);
    const icon = document.getElementById("theme-icon");
    if (icon) {
        icon.setAttribute("data-lucide", isNightMode ? "sun" : "moon");
        lucide.createIcons();
    }
}

// Initialization
document.addEventListener("DOMContentLoaded", () => {
    renderWorkshopTable();
    updateTopMetrics();
    lucide.createIcons();
    // Pre-calculate solder
    runSolderCalculation();
});

// =========================================================================
// PHASE 2 MODULES: BENCH QUICK-PAD, CRAFTSMEN PAYROLL, CRUCIBLE & REFINING
// =========================================================================

// -------------------------------------------------------------
// 8. Bench Quick-Pad Logic
// -------------------------------------------------------------
let selectedBenchCraftsmanId = 1;
let selectedBenchCraftsmanName = "نیما";
let selectedBenchStage = "skin";

function selectBenchCraftsman(id, name, btn) {
    selectedBenchCraftsmanId = id;
    selectedBenchCraftsmanName = name;
    document.querySelectorAll(".bench-c-btn").forEach(b => {
        b.className = "bench-c-btn p-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card-subtle)] text-[var(--text-primary)] font-bold text-sm flex flex-col items-center gap-1 hover:border-amber-500 transition-all";
    });
    if (btn) {
        btn.className = "bench-c-btn p-3 rounded-xl border-2 border-amber-500 bg-amber-500/10 text-amber-900 dark:text-amber-200 font-bold text-sm flex flex-col items-center gap-1 transition-all";
    }
    const label = document.getElementById("bench-selected-craftsman-label");
    if (label) label.innerText = name;
    calculateBenchLoss();
}

function selectBenchStage(stage, btn) {
    selectedBenchStage = stage;
    document.querySelectorAll(".bench-s-btn").forEach(b => {
        b.className = "bench-s-btn px-4 py-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card-subtle)] font-bold text-xs hover:border-amber-500";
    });
    if (btn) {
        btn.className = "bench-s-btn px-4 py-2 rounded-xl border-2 border-amber-500 bg-amber-500/10 font-bold text-xs text-amber-900 dark:text-amber-200";
    }
    const label = document.getElementById("bench-selected-stage-label");
    if (label) label.innerText = stageConfig[stage]?.label || stage;
    calculateBenchLoss();
}

function toggleBenchSwarfInput() {
    const isChecked = document.getElementById("bench-has-swarf")?.checked;
    const wrap = document.getElementById("bench-swarf-input-wrap");
    if (wrap) {
        if (isChecked) {
            wrap.classList.remove("hidden");
        } else {
            wrap.classList.add("hidden");
            const swInput = document.getElementById("bench-swarf-weight");
            if (swInput) swInput.value = "";
        }
    }
    calculateBenchLoss();
}

function calculateBenchLoss() {
    const inW = parseFloat(document.getElementById("bench-in-weight")?.value) || 0.0;
    const outW = parseFloat(document.getElementById("bench-out-weight")?.value) || 0.0;
    const swarfW = parseFloat(document.getElementById("bench-swarf-weight")?.value) || 0.0;
    
    const effectiveOut = outW + swarfW;
    const loss = Number((effectiveOut - inW).toFixed(3));
    const lossValEl = document.getElementById("bench-loss-value");
    const lossDescEl = document.getElementById("bench-loss-desc");
    const box = document.getElementById("bench-loss-display-box");

    if (inW > 0 && outW > 0) {
        const soot = Math.round(Math.abs(loss) * 1000);
        if (lossValEl) lossValEl.innerText = `${formatGold(loss)} گرم`;
        if (lossDescEl) lossDescEl.innerText = `(${formatDigits(soot)} سوت طلا)`;

        if (loss < -1.0) {
            if (box) box.className = "p-4 rounded-xl border border-rose-500/50 bg-rose-500/10 text-center space-y-1";
            if (lossValEl) lossValEl.className = "font-mono text-2xl font-black text-rose-600 dark:text-rose-400";
        } else if (loss <= 0) {
            if (box) box.className = "p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-center space-y-1";
            if (lossValEl) lossValEl.className = "font-mono text-2xl font-black text-amber-700 dark:text-amber-400";
        } else {
            if (box) box.className = "p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-center space-y-1";
            if (lossValEl) lossValEl.className = "font-mono text-2xl font-black text-emerald-700 dark:text-emerald-400";
        }
    } else {
        if (lossValEl) lossValEl.innerText = "۰.۰۰۰- گرم";
        if (lossDescEl) lossDescEl.innerText = "(۰ سوت طلا)";
    }
}

async function submitBenchQuickTask() {
    const inW = parseFloat(document.getElementById("bench-in-weight")?.value);
    const outW = parseFloat(document.getElementById("bench-out-weight")?.value);
    const itemName = document.getElementById("bench-item-name")?.value?.trim() || "کار ساخته";
    const count = parseInt(document.getElementById("bench-item-count")?.value) || 1;
    const hasSwarf = document.getElementById("bench-has-swarf")?.checked;
    const swarfW = hasSwarf ? (parseFloat(document.getElementById("bench-swarf-weight")?.value) || 0.0) : 0.0;
    const notes = document.getElementById("bench-notes")?.value?.trim() || "";

    if (!inW || inW <= 0 || isNaN(outW) || outW < 0) {
        showToast("لطفاً وزن ورودی و خروجی را با دقت وارد فرمایید.", "danger");
        return;
    }

    const payload = {
        craftsman_id: selectedBenchCraftsmanId,
        stage: selectedBenchStage,
        item_name: itemName,
        count: count,
        input_weight: inW,
        output_weight: outW,
        send_to_swarf_weight: swarfW,
        notes: notes
    };

    try {
        const resp = await fetch(`${API_BASE}/api/workshop/quick-task`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "خطا در ثبت پای میز کار");
        }

        const res = await resp.json();
        
        // Add locally to ledgerRows
        const now = new Date();
        const timeStr = formatDigits(`${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`);
        const newId = ledgerRows.length > 0 ? Math.max(...ledgerRows.map(r => r.id)) + 1 : 1;

        ledgerRows.unshift({
            id: newId,
            time: timeStr,
            stage: selectedBenchStage,
            worker: selectedBenchCraftsmanName,
            item: itemName,
            count: count,
            in: inW,
            out: outW,
            loss: res.loss_weight,
            notes: notes + (swarfW > 0 ? ` (ارسال ${swarfW}g به سوآله)` : "")
        });

        renderWorkshopTable();
        updateTopMetrics();

        // Reset inputs
        document.getElementById("bench-in-weight").value = "";
        document.getElementById("bench-out-weight").value = "";
        if (hasSwarf) {
            document.getElementById("bench-has-swarf").checked = false;
            toggleBenchSwarfInput();
        }
        calculateBenchLoss();

        showToast(`کار "${itemName}" استادکار ${selectedBenchCraftsmanName} با کسری ${formatGold(res.loss_weight)}g با موفقیت ثبت شد.`, "success");
    } catch (err) {
        showToast(err.message, "danger");
    }
}

function promptAddCraftsman() {
    const name = prompt("نام استادکار جدید را وارد کنید:");
    if (!name || !name.trim()) return;
    const role = prompt("تخصص یا نقش (مثلاً: پوست و پرداخت، ریخته‌گری، مخراجکاری):", "سازنده طلا");
    
    fetch(`${API_BASE}/api/workshop/craftsmen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), role: role || "سازنده طلا" })
    }).then(r => r.json()).then(data => {
        showToast(`استادکار "${name}" به سیستم اضافه شد.`, "success");
        // Reload page or list
        setTimeout(() => location.reload(), 800);
    }).catch(e => showToast(e.message, "danger"));
}

// -------------------------------------------------------------
// 9. Craftsmen Payroll & Settlements
// -------------------------------------------------------------
let craftsmenPayrollList = [];

async function loadCraftsmenPayroll() {
    try {
        const resp = await fetch(`${API_BASE}/api/workshop/craftsmen-payroll`);
        if (!resp.ok) return;
        craftsmenPayrollList = await resp.json();
        renderCraftsmenPayrollCards(craftsmenPayrollList);
    } catch (err) {
        console.error("Failed to load payroll", err);
    }
}

function renderCraftsmenPayrollCards(list) {
    const container = document.getElementById("craftsmen-payroll-cards");
    if (!container) return;

    if (!list || list.length === 0) {
        container.innerHTML = `<div class="p-6 text-center text-xs text-[var(--text-muted)] col-span-3">هیچ داده‌ای یافت نشد.</div>`;
        return;
    }

    container.innerHTML = list.map(c => {
        const avatarClass = getWorkerAvatarClass(c.name);
        const stageChips = Object.entries(c.stage_breakdown || {}).map(([stg, grams]) => {
            const label = stageConfig[stg]?.label || stg;
            return `<span class="bg-[var(--bg-card)] border border-[var(--border-color)] px-2 py-0.5 rounded text-[11px] font-bold">${label}: ${formatGold(grams)}g</span>`;
        }).join(" ");

        const balanceClass = c.wage_balance_irr > 0 ? "text-amber-700 dark:text-amber-400" : "text-emerald-700 dark:text-emerald-400";

        return `
            <div class="dilan-card p-5 space-y-4 flex flex-col justify-between">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2.5">
                            <div class="w-10 h-10 rounded-xl ${avatarClass} flex items-center justify-center font-heading font-black text-white text-base shadow-sm">
                                ${c.name[0]}
                            </div>
                            <div>
                                <h4 class="font-heading text-sm text-[var(--text-primary)]">${c.name}</h4>
                                <span class="text-[11px] text-[var(--text-muted)]">${c.role}</span>
                            </div>
                        </div>
                        <span class="text-xs bg-amber-500/10 text-amber-800 dark:text-amber-300 px-2.5 py-1 rounded-lg font-mono font-bold">
                            ${formatDigits(c.task_count)} عملیات
                        </span>
                    </div>

                    <div class="bg-[var(--bg-card-subtle)] p-3 rounded-xl border border-[var(--border-color)] space-y-2 text-xs">
                        <div class="flex justify-between">
                            <span class="text-[var(--text-muted)]">مجموع کارکرد ناخالص:</span>
                            <span class="font-mono font-bold">${formatGold(c.total_output_weight)} گرم</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-[var(--text-muted)]">کسری کل تولید:</span>
                            <span class="font-mono font-bold text-rose-600 dark:text-rose-400">${formatGold(c.total_loss_weight)} گرم</span>
                        </div>
                        <div class="flex flex-wrap gap-1 pt-1 border-t border-[var(--border-color)]">
                            ${stageChips || "<span class='text-[10px] text-[var(--text-muted)]'>بدون تفکیک مرحله</span>"}
                        </div>
                    </div>

                    <div class="space-y-1.5 text-xs">
                        <div class="flex justify-between font-bold">
                            <span class="text-[var(--text-muted)]">اجرت کل محاسبه‌شده:</span>
                            <span class="font-mono text-emerald-700 dark:text-emerald-400">${formatDigits(Math.round(c.calculated_wage_irr / 10).toLocaleString())} تومان</span>
                        </div>
                        <div class="flex justify-between text-[11px]">
                            <span class="text-[var(--text-muted)]">مجموع پرداخت‌شده:</span>
                            <span class="font-mono text-[var(--text-secondary)]">${formatDigits(Math.round(c.paid_amount_irr / 10).toLocaleString())} تومان</span>
                        </div>
                        <div class="flex justify-between font-bold pt-1 border-t border-[var(--border-color)]">
                            <span>مانده طلب / تسویه:</span>
                            <span class="font-mono ${balanceClass}">${formatDigits(Math.round(c.wage_balance_irr / 10).toLocaleString())} تومان</span>
                        </div>
                    </div>
                </div>

                <div class="pt-2">
                    <button type="button" onclick="prepareSettlementForCraftsman(${c.craftsman_id})" class="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center gap-1.5">
                        <i data-lucide="badge-dollar-sign" class="w-4 h-4"></i>
                        <span>صدور فیش و تسویه حساب</span>
                    </button>
                </div>
            </div>
        `;
    }).join("");

    lucide.createIcons();
}

async function loadSettlements() {
    try {
        const resp = await fetch(`${API_BASE}/api/workshop/settlements`);
        if (!resp.ok) return;
        const list = await resp.json();
        const tbody = document.getElementById("settlements-table-body");
        if (!tbody) return;

        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-6 text-xs text-[var(--text-muted)]">هنوز فیش تسویه‌ای ثبت نشده است.</td></tr>`;
            return;
        }

        tbody.innerHTML = list.map(s => `
            <tr>
                <td class="font-mono">#${formatDigits(s.id)}</td>
                <td class="font-mono">${formatDigits(s.date_shamsi)}</td>
                <td class="font-bold">${s.craftsman_name}</td>
                <td>${s.period_title}</td>
                <td class="font-mono font-bold">${formatGold(s.total_worked_grams)} g</td>
                <td class="font-mono">${formatDigits(Math.round(s.wage_rate_irr / 10).toLocaleString())} ت</td>
                <td class="font-mono font-bold text-emerald-700 dark:text-emerald-400">${formatDigits(Math.round(s.total_wage_irr / 10).toLocaleString())} ت</td>
                <td class="font-mono">${formatDigits(Math.round(s.paid_amount_irr / 10).toLocaleString())} ت</td>
                <td class="font-mono">${formatGold(s.paid_gold_weight)} g</td>
                <td>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
                        ${s.settlement_status.replace('_', ' ')}
                    </span>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Failed to load settlements", err);
    }
}

function openNewSettlementModal() {
    const select = document.getElementById("settle-craftsman-id");
    if (select) {
        select.innerHTML = craftsmenPayrollList.map(c => `<option value="${c.craftsman_id}">${c.name} (${c.role})</option>`).join("");
    }
    autoFillSettlementDetails();
    document.getElementById("modal-settlement")?.classList.remove("hidden");
}

function prepareSettlementForCraftsman(cid) {
    openNewSettlementModal();
    const select = document.getElementById("settle-craftsman-id");
    if (select) select.value = cid;
    autoFillSettlementDetails();
}

function closeSettlementModal() {
    document.getElementById("modal-settlement")?.classList.add("hidden");
}

function autoFillSettlementDetails() {
    const cid = parseInt(document.getElementById("settle-craftsman-id")?.value) || 1;
    const c = craftsmenPayrollList.find(x => x.craftsman_id === cid);
    if (c) {
        const gramsInput = document.getElementById("settle-worked-grams");
        if (gramsInput) gramsInput.value = c.total_output_weight;
        const paidIrrInput = document.getElementById("settle-paid-irr");
        if (paidIrrInput) paidIrrInput.value = c.calculated_wage_irr;
    }
    calcSettlementTotal();
}

function calcSettlementTotal() {
    const grams = parseFloat(document.getElementById("settle-worked-grams")?.value) || 0.0;
    const rate = parseFloat(document.getElementById("settle-wage-rate")?.value) || 0.0;
    const totalWage = Math.round(grams * rate);
    const badge = document.getElementById("settle-total-wage-badge");
    if (badge) {
        const tomans = Math.round(totalWage / 10);
        badge.innerText = `${formatDigits(tomans.toLocaleString())} تومان (${formatDigits(totalWage.toLocaleString())} ریال)`;
    }
}

async function submitCraftsmanSettlement() {
    const cid = parseInt(document.getElementById("settle-craftsman-id")?.value);
    const dateShamsi = document.getElementById("settle-date")?.value || "1405/07/29";
    const period = document.getElementById("settle-period")?.value || "تسویه هفتگی";
    const grams = parseFloat(document.getElementById("settle-worked-grams")?.value) || 0.0;
    const rate = parseFloat(document.getElementById("settle-wage-rate")?.value) || 0.0;
    const totalWage = Math.round(grams * rate);
    const paidIrr = parseFloat(document.getElementById("settle-paid-irr")?.value) || 0.0;
    const paidGold = parseFloat(document.getElementById("settle-paid-gold")?.value) || 0.0;
    const status = document.getElementById("settle-status")?.value || "تسویه_شده";
    const notes = document.getElementById("settle-notes")?.value || "";

    const payload = {
        craftsman_id: cid,
        date_shamsi: dateShamsi,
        period_title: period,
        total_worked_grams: grams,
        wage_rate_irr: rate,
        total_wage_irr: totalWage,
        paid_amount_irr: paidIrr,
        paid_gold_weight: paidGold,
        settlement_status: status,
        notes: notes
    };

    try {
        const resp = await fetch(`${API_BASE}/api/workshop/settlements`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error("خطا در ثبت تسویه حساب");
        closeSettlementModal();
        showToast("فیش تسویه حساب با موفقیت صادر و ثبت شد.", "success");
        loadCraftsmenPayroll();
        loadSettlements();
    } catch (err) {
        showToast(err.message, "danger");
    }
}

// -------------------------------------------------------------
// 10. Crucible, Solder & Refining Hub
// -------------------------------------------------------------
let solderRecipeCache = null;

async function runSolderCalculation() {
    const type = document.getElementById("solder-recipe-type")?.value || "medium";
    const baseW = parseFloat(document.getElementById("solder-base-weight")?.value) || 10.0;
    const customCadmium = parseFloat(document.getElementById("solder-custom-cadmium")?.value) || 2.5;

    const customWrap = document.getElementById("solder-custom-wrap");
    if (customWrap) {
        if (type === "custom") customWrap.classList.remove("hidden");
        else customWrap.classList.add("hidden");
    }

    try {
        const resp = await fetch(`${API_BASE}/api/workshop/solder-calc`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                base_gold_weight: baseW,
                recipe_type: type,
                custom_cadmium_percent: customCadmium
            })
        });

        if (!resp.ok) return;
        const res = await resp.json();
        solderRecipeCache = res;

        const cadEl = document.getElementById("solder-res-cadmium");
        const silEl = document.getElementById("solder-res-silver");
        const totEl = document.getElementById("solder-res-total");
        const carEl = document.getElementById("solder-res-carat");

        if (cadEl) cadEl.innerText = `${formatGold(res.cadmium_weight)} گرم (${formatDigits(res.cadmium_percent)}٪)`;
        if (silEl) silEl.innerText = `${formatGold(res.silver_weight)} گرم`;
        if (totEl) totEl.innerText = `${formatGold(res.total_solder_weight)} گرم`;
        if (carEl) carEl.innerText = formatDigits(res.resulting_carat);
    } catch (err) {
        console.error("Solder calc error", err);
    }
}

function showSolderInstructionsModal() {
    if (!solderRecipeCache) return;
    const container = document.getElementById("solder-instructions-content");
    if (container) {
        container.innerHTML = `
            <div class="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs font-bold text-amber-900 dark:text-amber-200">
                فرمول فعال: ${solderRecipeCache.title} | عیار نهایی: ${formatDigits(solderRecipeCache.resulting_carat)}
            </div>
            <ul class="space-y-2 mt-2">
                ${solderRecipeCache.instructions.map(ins => `<li class="flex items-start gap-2 bg-[var(--bg-card-subtle)] p-2.5 rounded-lg border border-[var(--border-color)]"><span>⚡</span><span>${ins}</span></li>`).join("")}
            </ul>
        `;
    }
    document.getElementById("modal-solder-instructions")?.classList.remove("hidden");
}

function closeSolderInstructionsModal() {
    document.getElementById("modal-solder-instructions")?.classList.add("hidden");
}

function calcCrucibleNetLoss() {
    const raw = parseFloat(document.getElementById("crucible-raw-weight")?.value) || 0.0;
    const alloy = parseFloat(document.getElementById("crucible-alloy-added")?.value) || 0.0;
    const bar = parseFloat(document.getElementById("crucible-melted-weight")?.value) || 0.0;
    const sheereh = parseFloat(document.getElementById("crucible-sheereh-weight")?.value) || 0.0;

    const netLoss = Number((raw + alloy - bar - sheereh).toFixed(3));
    const badge = document.getElementById("crucible-net-loss-badge");
    if (badge) {
        badge.innerText = `${formatGold(netLoss)} گرم`;
    }
}

async function submitCrucibleRecord() {
    const code = document.getElementById("crucible-code")?.value?.trim() || "بوته-۱۰۱";
    const op = document.getElementById("crucible-operator")?.value?.trim() || "مسئول ذوب";
    const raw = parseFloat(document.getElementById("crucible-raw-weight")?.value);
    const alloy = parseFloat(document.getElementById("crucible-alloy-added")?.value) || 0.0;
    const bar = parseFloat(document.getElementById("crucible-melted-weight")?.value);
    const sheereh = parseFloat(document.getElementById("crucible-sheereh-weight")?.value) || 0.0;

    if (!raw || isNaN(bar)) {
        showToast("لطفاً وزن طلای اولیه و شمش خروجی را وارد کنید.", "danger");
        return;
    }

    const payload = {
        date_shamsi: "1405/07/29",
        crucible_code: code,
        operator_name: op,
        raw_gold_weight: raw,
        alloy_bar_added: alloy,
        melted_bar_weight: bar,
        sheereh_weight: sheereh,
        notes: "ثبت از سامانه تخصصی بوته"
    };

    try {
        const resp = await fetch(`${API_BASE}/api/workshop/crucibles`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error("خطا در ثبت بوته ذوب");
        const res = await resp.json();
        showToast(`گزارش بوته با کسر خالص ${formatGold(res.loss_weight)}g ثبت گردید.`, "success");
        loadCruciblesAndRefining();
    } catch (err) {
        showToast(err.message, "danger");
    }
}

async function submitRefiningBatch() {
    const refiner = document.getElementById("refining-refiner-name")?.value?.trim() || "قالکاری حاج‌رضا";
    const code = document.getElementById("refining-batch-code")?.value?.trim() || "REF-01";
    const weight = parseFloat(document.getElementById("refining-sent-weight")?.value);
    const material = document.getElementById("refining-material-type")?.value || "سوآله چرم و سوهان";

    if (!weight || weight <= 0) {
        showToast("لطفاً وزن ارسالی به قالکاری را وارد نمایید.", "danger");
        return;
    }

    const payload = {
        date_shamsi: "1405/07/29",
        batch_code: code,
        refiner_name: refiner,
        material_type: material,
        sent_weight: weight,
        notes: "محموله ارسالی به قالکاری"
    };

    try {
        const resp = await fetch(`${API_BASE}/api/workshop/refining`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error("خطا در ثبت ارسال به قالکاری");
        showToast("محموله به قالکاری ارسال و در سیستم ثبت شد.", "success");
        loadCruciblesAndRefining();
    } catch (err) {
        showToast(err.message, "danger");
    }
}

async function loadCruciblesAndRefining() {
    // 1. Crucibles
    try {
        const cResp = await fetch(`${API_BASE}/api/workshop/crucibles`);
        if (cResp.ok) {
            const crucibles = await cResp.json();
            const cBody = document.getElementById("crucibles-table-body");
            if (cBody) {
                if (crucibles.length === 0) {
                    cBody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-[var(--text-muted)]">هنوز گزارشی ثبت نشده است.</td></tr>`;
                } else {
                    cBody.innerHTML = crucibles.map(c => `
                        <tr>
                            <td class="font-mono">${formatDigits(c.date_shamsi)}</td>
                            <td class="font-bold">${c.crucible_code}</td>
                            <td class="font-mono">${formatGold(c.raw_gold_weight)} g</td>
                            <td class="font-mono">${formatGold(c.melted_bar_weight)} g</td>
                            <td class="font-mono text-amber-700 dark:text-amber-400">${formatGold(c.sheereh_weight)} g</td>
                            <td class="font-mono font-bold text-rose-600 dark:text-rose-400">${formatGold(c.loss_weight)} g</td>
                        </tr>
                    `).join("");
                }
            }
        }
    } catch (e) {
        console.error("Crucibles error", e);
    }

    // 2. Refining
    try {
        const rResp = await fetch(`${API_BASE}/api/workshop/refining`);
        if (rResp.ok) {
            const batches = await rResp.json();
            const rBody = document.getElementById("refining-table-body");
            if (rBody) {
                if (batches.length === 0) {
                    rBody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-[var(--text-muted)]">هیچ محموله قالکاری فعالی ثبت نشده است.</td></tr>`;
                } else {
                    rBody.innerHTML = batches.map(b => `
                        <tr>
                            <td class="font-mono font-bold">${b.batch_code}</td>
                            <td>${b.refiner_name}</td>
                            <td class="font-mono">${formatGold(b.sent_weight)} g</td>
                            <td class="font-mono font-bold text-emerald-700 dark:text-emerald-400">${formatGold(b.recovered_gold_750)} g</td>
                            <td>
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${b.status.includes('تسویه') ? 'bg-emerald-500/10 text-emerald-700 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-800 border border-amber-500/20'}">
                                    ${b.status.replace('_', ' ')}
                                </span>
                            </td>
                            <td>
                                ${!b.status.includes('تسویه') ? `
                                    <button onclick="openRefiningModal(${b.id})" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[10px] font-bold">
                                        ثبت بازیافت
                                    </button>
                                ` : `<span class="text-[10px] text-[var(--text-muted)]">تکمیل‌شده</span>`}
                            </td>
                        </tr>
                    `).join("");
                }
            }
        }
    } catch (e) {
        console.error("Refining error", e);
    }
}

function openRefiningModal(id) {
    const input = document.getElementById("refining-complete-batch-id");
    if (input) input.value = id;
    document.getElementById("modal-refining-complete")?.classList.remove("hidden");
}

function closeRefiningModal() {
    document.getElementById("modal-refining-complete")?.classList.add("hidden");
}

async function confirmCompleteRefiningBatch() {
    const id = document.getElementById("refining-complete-batch-id")?.value;
    const recovered = parseFloat(document.getElementById("refining-complete-recovered")?.value);
    const fee = parseFloat(document.getElementById("refining-complete-fee")?.value) || 0.0;
    const notes = document.getElementById("refining-complete-notes")?.value || "";

    if (!recovered || recovered <= 0) {
        showToast("لطفاً طلای استحصالی ۷۵۰ را وارد کنید.", "danger");
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/workshop/refining/${id}/complete`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                recovered_gold_750: recovered,
                refining_fee_irr: fee,
                status: "تسویه_شده",
                notes: notes
            })
        });

        if (!resp.ok) throw new Error("خطا در ثبت بازیافت قالکاری");
        closeRefiningModal();
        showToast(`طلای استحصالی ${formatGold(recovered)}g با موفقیت ثبت و تراز شد.`, "success");
        loadCruciblesAndRefining();
    } catch (err) {
        showToast(err.message, "danger");
    }
}

