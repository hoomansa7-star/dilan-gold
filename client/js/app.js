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

    // Hide all tab sections
    document.getElementById("tab-daily-ledger")?.classList.add("hidden");
    document.getElementById("tab-workshop-matrix")?.classList.add("hidden");
    document.getElementById("tab-melting-calc")?.classList.add("hidden");

    // Show active section
    const targetSection = document.getElementById(`tab-${tabId}`);
    if (targetSection) targetSection.classList.remove("hidden");

    // Update tab button styles
    const tabs = ["daily-ledger", "workshop-matrix", "melting-calc"];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        if (!btn) return;
        if (t === tabId) {
            btn.className = "main-nav-tab flex items-center gap-2 px-4 py-2.5 rounded-lg font-bold text-xs bg-amber-600 text-white transition-all shadow-sm";
        } else {
            btn.className = "main-nav-tab flex items-center gap-2 px-4 py-2.5 rounded-lg font-bold text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-subtle)] transition-all";
        }
    });

    if (tabId === "melting-calc") {
        renderIngotRows();
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
});
