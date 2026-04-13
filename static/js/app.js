// ─── SPSS Online - Main App JavaScript ────────────────────────────────────────
// Global Application State
const App = {
    datasetId: null,
    datasetName: null,
    datasetRows: 0,
    datasetCols: 0,
    columns: [],
    columnInfo: [],
    currentTab: 'data-editor',
    outputHtml: '',
    charts: [],
    syntaxLog: [],
    viewMode: 'data',
    // Editable table state
    tableColumns: [],
    tableData: [],
    hasUnsavedChanges: false,
};

const CSRF = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

// ─── API Helpers ───────────────────────────────────────────────────────────────
async function apiPost(url, data) {
    const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify(data),
    });
    return r.json();
}

async function apiGet(url) {
    const r = await fetch(url);
    return r.json();
}

// ─── Toast Notifications ───────────────────────────────────────────────────────
function toast(msg, type = 'info', duration = 4000) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const tc = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
    tc.appendChild(el);
    setTimeout(() => {
        el.style.animation = 'none';
        el.style.opacity = '0';
        el.style.transform = 'translateX(40px)';
        el.style.transition = 'all 0.3s ease';
        setTimeout(() => el.remove(), 300);
    }, duration);
}

// ─── Loading State ─────────────────────────────────────────────────────────────
function setLoading(active, message = 'Memproses...') {
    const lo = document.getElementById('loading-overlay');
    if (active) {
        lo.innerHTML = `<div class="spinner"></div><span>${message}</span>`;
        lo.classList.add('active');
    } else {
        lo.classList.remove('active');
    }
}

// ─── Tab Switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
    App.currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');
    document.getElementById(`panel-${tab}`)?.classList.add('active');
}

// ─── Dataset Selector ──────────────────────────────────────────────────────────
async function loadDatasets() {
    const res = await apiGet('/api/datasets/');
    const sel = document.getElementById('dataset-select');
    const current = sel.value;
    sel.innerHTML = '<option value="">-- Pilih Dataset --</option>';
    for (const ds of res.datasets) {
        const opt = document.createElement('option');
        opt.value = ds.id;
        opt.textContent = `${ds.name} (${ds.rows}×${ds.columns})`;
        sel.appendChild(opt);
    }
    if (current) sel.value = current;
}

async function onDatasetChange() {
    const sel = document.getElementById('dataset-select');
    const id = sel.value;
    if (!id) return;

    setLoading(true, 'Memuat dataset...');
    try {
        const res = await apiGet(`/api/dataset/${id}/`);
        if (res.success) {
            App.datasetId = res.dataset_id;
            App.datasetName = res.name;
            App.datasetRows = res.rows;
            App.datasetCols = res.columns;
            App.columns = res.columns_list;
            App.columnInfo = res.column_info;
            renderDataTable(res.columns_list, res.data);
            renderVariableTable(res.column_info);
            updateStatusBar();
            document.getElementById('dataset-info').textContent =
                `${res.rows.toLocaleString()} baris × ${res.columns} kolom`;
            toast(`Dataset "${res.name}" dimuat`, 'success');
        }
    } finally {
        setLoading(false);
    }
}

// ─── File Upload ───────────────────────────────────────────────────────────────
function triggerUpload() {
    document.getElementById('file-input').click();
}

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const allowedExt = ['.csv', '.xlsx', '.xls', '.sav'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExt.includes(ext)) {
        toast('Format tidak didukung. Gunakan CSV, Excel, atau SPSS', 'error');
        return;
    }

    setLoading(true, `Mengupload "${file.name}"...`);
    const formData = new FormData();
    formData.append('file', file);

    try {
        const r = await fetch('/api/upload/', {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF },
            body: formData,
        });
        const res = await r.json();
        if (res.success) {
            App.datasetId = res.dataset_id;
            App.datasetName = res.name;
            App.datasetRows = res.rows;
            App.datasetCols = res.columns;
            App.columns = res.preview_columns;
            App.columnInfo = res.column_info;
            renderDataTable(res.preview_columns, res.preview_data);
            renderVariableTable(res.column_info);
            updateStatusBar();
            await loadDatasets();
            document.getElementById('dataset-select').value = res.dataset_id;
            document.getElementById('dataset-info').textContent =
                `${res.rows.toLocaleString()} baris × ${res.columns} kolom`;
            switchTab('data-editor');
            addSyntax(`IMPORT FILE='${file.name}'.`);
            toast(`File "${file.name}" berhasil diupload (${res.rows} baris)`, 'success');
        } else {
            toast(res.error || 'Upload gagal', 'error');
        }
    } catch (e) {
        toast('Upload gagal: ' + e.message, 'error');
    } finally {
        setLoading(false);
        input.value = '';
    }
}

// ─── Data Table Rendering ──────────────────────────────────────────────────────
function renderDataTable(columns, data) {
    App.tableColumns = [...columns];
    App.tableData = (Array.isArray(data) ? data : []).map(row =>
        row.map(v => (v === null || v === undefined) ? '' : String(v))
    );
    _buildTable();
}

function _buildTable() {
    const wrapper = document.getElementById('data-table-wrapper');
    const empty = document.getElementById('empty-state');
    if (empty) empty.style.display = 'none';

    let html = '<table class="data-table" id="main-data-table"><thead><tr>';
    html += '<th class="row-num ctrl-cell" title="Klik kanan baris untuk opsi">#</th>';
    App.tableColumns.forEach((col, i) => {
        html += `<th><div class="col-header-wrap">
            <span>${escHtml(col)}</span>
            <button class="del-col-btn" onclick="deleteColumn(${i})" title="Hapus kolom ${escHtml(col)}">×</button>
        </div></th>`;
    });
    html += '</tr></thead><tbody>';

    App.tableData.forEach((row, r) => {
        html += `<tr id="row-${r}" data-row="${r}">`;
        html += `<td class="row-num ctrl-cell" oncontextmenu="showRowCtxMenu(event,${r})" title="Klik kanan untuk opsi">${r + 1}</td>`;
        row.forEach((val, c) => {
            const missing = val === '';
            html += `<td class="editable-cell${missing ? ' cell-missing' : ''}"
                contenteditable="true" spellcheck="false"
                data-row="${r}" data-col="${c}" data-original="${escHtml(val)}"
                onfocus="onCellFocus(this)"
                onblur="onCellBlur(this)"
                onkeydown="onCellKeyDown(event,this)"
                oninput="onCellInput(this)"
            >${escHtml(val)}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    wrapper.innerHTML = html;
    App.viewMode = 'data';
}

// ─── Cell Event Handlers ───────────────────────────────────────────────────────
function onCellFocus(td) {
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(td);
    sel.removeAllRanges();
    sel.addRange(range);
}

function onCellBlur(td) {
    const r = +td.dataset.row, c = +td.dataset.col;
    if (App.tableData[r]) App.tableData[r][c] = td.innerText.trim();
}

function onCellInput(td) {
    const val = td.innerText.trim();
    td.classList.toggle('cell-changed', val !== td.dataset.original);
    td.classList.toggle('cell-missing', val === '');
    markChanged();
}

function onCellKeyDown(e, td) {
    const r = +td.dataset.row, c = +td.dataset.col;
    if (e.key === 'Enter') {
        e.preventDefault();
        const next = document.querySelector(`[data-row="${r+1}"][data-col="${c}"]`);
        if (next) next.focus();
        else { addRow(); setTimeout(() => document.querySelector(`[data-row="${r+1}"][data-col="${c}"]`)?.focus(), 60); }
    } else if (e.key === 'Tab') {
        e.preventDefault();
        let nr = r, nc = c + (e.shiftKey ? -1 : 1);
        if (nc < 0) { nc = App.tableColumns.length - 1; nr--; }
        if (nc >= App.tableColumns.length) { nc = 0; nr++; }
        document.querySelector(`[data-row="${nr}"][data-col="${nc}"]`)?.focus();
    } else if (e.key === 'Escape') {
        td.innerText = td.dataset.original;
        td.classList.remove('cell-changed', 'cell-missing');
        td.blur();
    } else if (e.key === 'Delete' && e.ctrlKey) {
        e.preventDefault();
        td.innerText = '';
        onCellInput(td);
    }
}

// ─── Row / Column Operations ──────────────────────────────────────────────────
function addRow() {
    if (!App.datasetId) { toast('Upload dataset terlebih dahulu', 'warning'); return; }
    App.tableData.push(Array(App.tableColumns.length).fill(''));
    _buildTable();
    markChanged();
    setTimeout(() => {
        const cell = document.querySelector(`[data-row="${App.tableData.length-1}"][data-col="0"]`);
        if (cell) { cell.focus(); cell.scrollIntoView({block:'nearest'}); }
    }, 50);
    toast(`Baris ${App.tableData.length} ditambahkan`, 'success', 2000);
}

function addColumnModal() {
    if (!App.datasetId) { toast('Upload dataset terlebih dahulu', 'warning'); return; }
    document.getElementById('new-col-name').value = '';
    document.getElementById('new-col-default').value = '';
    openModal('modal-add-column');
}

function confirmAddColumn() {
    const name = document.getElementById('new-col-name').value.trim();
    if (!name) { toast('Nama variabel tidak boleh kosong', 'warning'); return; }
    if (App.tableColumns.includes(name)) { toast(`Variabel "${name}" sudah ada`, 'warning'); return; }
    const def = document.getElementById('new-col-default').value;
    App.tableColumns.push(name);
    App.tableData.forEach(row => row.push(def));
    closeModal();
    _buildTable();
    markChanged();
    toast(`Variabel "${name}" berhasil ditambahkan`, 'success');
}

function deleteRow(r) {
    if (App.tableData.length <= 1) { toast('Tidak bisa menghapus semua baris', 'warning'); return; }
    if (!confirm(`Hapus baris ${r+1}?`)) return;
    App.tableData.splice(r, 1);
    _buildTable();
    markChanged();
    toast(`Baris ${r+1} dihapus`, 'success', 2000);
}

function insertRowAt(r) {
    App.tableData.splice(r, 0, Array(App.tableColumns.length).fill(''));
    _buildTable();
    markChanged();
    toast(`Baris baru ditambahkan`, 'success', 2000);
}

function deleteColumn(c) {
    if (App.tableColumns.length <= 1) { toast('Tidak bisa menghapus semua kolom', 'warning'); return; }
    if (!confirm(`Hapus variabel "${App.tableColumns[c]}"?`)) return;
    App.tableColumns.splice(c, 1);
    App.tableData.forEach(row => row.splice(c, 1));
    _buildTable();
    markChanged();
    toast(`Kolom dihapus`, 'success', 2000);
}

// ─── Save Bar & Persistence ───────────────────────────────────────────────────
function markChanged() {
    App.hasUnsavedChanges = true;
    const bar = document.getElementById('save-bar');
    if (bar) bar.classList.add('visible');
    const info = document.getElementById('save-bar-info');
    if (info) info.textContent = `${App.tableData.length} baris × ${App.tableColumns.length} kolom — belum disimpan`;
}

async function saveTableData() {
    if (!App.datasetId) { toast('Tidak ada dataset aktif', 'warning'); return; }
    // Flush any focused cell
    document.querySelectorAll('.editable-cell').forEach(td => {
        const r = +td.dataset.row, c = +td.dataset.col;
        if (App.tableData[r] !== undefined) App.tableData[r][c] = td.innerText.trim();
    });
    setLoading(true, 'Menyimpan perubahan...');
    try {
        const res = await apiPost(`/api/dataset/${App.datasetId}/save/`, {
            columns: App.tableColumns, data: App.tableData,
        });
        if (res.success) {
            App.hasUnsavedChanges = false;
            App.columnInfo = res.column_info;
            App.datasetRows = res.rows;
            App.datasetCols = res.columns;
            document.getElementById('save-bar')?.classList.remove('visible');
            document.querySelectorAll('.cell-changed').forEach(td => {
                td.classList.remove('cell-changed');
                td.dataset.original = td.innerText.trim();
            });
            document.getElementById('dataset-info').textContent =
                `${res.rows.toLocaleString()} baris × ${res.columns} kolom`;
            updateStatusBar();
            await loadDatasets();
            toast('✅ Data berhasil disimpan!', 'success');
        } else {
            toast('Gagal menyimpan: ' + (res.error || ''), 'error');
        }
    } catch(e) { toast('Error: ' + e.message, 'error'); }
    finally { setLoading(false); }
}

function discardChanges() {
    if (!confirm('Batalkan semua perubahan? Data akan dikembalikan ke versi terakhir yang disimpan.')) return;
    App.hasUnsavedChanges = false;
    document.getElementById('save-bar')?.classList.remove('visible');
    onDatasetChange();
    toast('Perubahan dibatalkan', 'info');
}

// ─── Right-click Context Menu ─────────────────────────────────────────────────
let _ctxRow = null;
function showRowCtxMenu(e, r) {
    e.preventDefault();
    _ctxRow = r;
    const m = document.getElementById('row-ctx-menu');
    m.style.display = 'block';
    m.style.left = Math.min(e.clientX, window.innerWidth - 180) + 'px';
    m.style.top = Math.min(e.clientY, window.innerHeight - 130) + 'px';
    document.getElementById('ctx-row-label').textContent = `Baris ${r + 1}`;
}
function hideCtxMenu() { document.getElementById('row-ctx-menu').style.display = 'none'; }
document.addEventListener('click', hideCtxMenu);
function ctxInsertAbove() { if (_ctxRow!==null) insertRowAt(_ctxRow); hideCtxMenu(); }
function ctxInsertBelow() { if (_ctxRow!==null) insertRowAt(_ctxRow+1); hideCtxMenu(); }
function ctxDelRow() { if (_ctxRow!==null) deleteRow(_ctxRow); hideCtxMenu(); }

function renderVariableTable(colInfo) {
    const wrapper = document.getElementById('data-table-wrapper');
    let html = '<table class="data-table variable-table"><thead><tr>';
    ['Name', 'Type', 'Data Type', 'Missing', 'Label'].forEach(h =>
        html += `<th>${h}</th>`
    );
    html += '</tr></thead><tbody>';
    for (let i = 0; i < colInfo.length; i++) {
        const c = colInfo[i];
        const typeLabel = c.type === 'numeric' ? '🔢 Numerik' : c.type === 'date' ? '📅 Tanggal' : '🔤 String';
        html += `<tr>
            <td><strong>${escHtml(c.name)}</strong></td>
            <td>${typeLabel}</td>
            <td><code style="font-size:11px;color:var(--text-muted)">${c.dtype}</code></td>
            <td style="color:${c.missing > 0 ? 'var(--accent-orange)' : 'var(--accent-green)'}">${c.missing}</td>
            <td>${escHtml(c.name)}</td>
        </tr>`;
    }
    html += '</tbody></table>';
    if (App.viewMode === 'variable') {
        wrapper.innerHTML = html;
    } else {
        // Store for later use
        App._varTableHtml = html;
    }
}

function toggleDataVariableView() {
    const wrapper = document.getElementById('data-table-wrapper');
    if (App.viewMode === 'data') {
        App.viewMode = 'variable';
        if (App.columnInfo && App.columnInfo.length > 0) {
            renderVariableTable(App.columnInfo);
            wrapper.innerHTML = App._varTableHtml || wrapper.innerHTML;
        }
        toast('Variable View', 'info', 2000);
    } else {
        App.viewMode = 'data';
        // Reload data view
        if (App.datasetId) onDatasetChange();
    }
}

// ─── Analysis ─────────────────────────────────────────────────────────────────
async function runAnalysis(type, params) {
    if (!App.datasetId) {
        toast('Silakan upload atau pilih dataset terlebih dahulu', 'warning');
        return;
    }

    setLoading(true, 'Menjalankan analisis...');
    try {
        const res = await apiPost('/api/analyze/', {
            dataset_id: App.datasetId,
            analysis_type: type,
            params,
        });
        if (res.success) {
            appendOutput(res.output_html);
            switchTab('output-viewer');
            addSyntax(generateSyntax(type, params));
            toast('Analisis selesai', 'success');
        } else {
            toast('Error: ' + (res.error || 'Analisis gagal'), 'error');
            console.error(res.traceback);
        }
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    } finally {
        setLoading(false);
    }
}

function appendOutput(html) {
    const viewer = document.getElementById('output-viewer');
    const empty = document.getElementById('output-empty');
    if (empty) empty.style.display = 'none';
    App.outputHtml += html;
    const div = document.createElement('div');
    div.innerHTML = html;
    viewer.appendChild(div);
    viewer.scrollTop = viewer.scrollHeight;
}

function clearOutput() {
    document.getElementById('output-viewer').innerHTML = `
        <div id="output-empty" class="empty-state" style="height:100%">
            <div class="empty-state-icon">📋</div>
            <h3>Output Viewer</h3>
            <p>Hasil analisis akan muncul di sini setelah Anda menjalankan analisis.</p>
        </div>`;
    App.outputHtml = '';
    toast('Output dibersihkan', 'info', 2000);
}

// ─── Chart Generation ──────────────────────────────────────────────────────────
async function generateChart(type, params) {
    if (!App.datasetId) {
        toast('Silakan upload atau pilih dataset terlebih dahulu', 'warning');
        return;
    }

    setLoading(true, 'Membuat grafik...');
    try {
        const res = await apiPost('/api/chart/', {
            dataset_id: App.datasetId,
            chart_type: type,
            params,
        });
        if (res.success) {
            addChart(res.chart_json, type, params);
            switchTab('chart-viewer');
            toast('Grafik berhasil dibuat', 'success');
        } else {
            toast('Error: ' + (res.error || 'Chart gagal'), 'error');
        }
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    } finally {
        setLoading(false);
    }
}

function addChart(chartJson, type, params) {
    const viewer = document.getElementById('chart-viewer');
    const empty = document.getElementById('chart-empty');
    if (empty) empty.style.display = 'none';

    const chartId = 'chart-' + Date.now();
    const typeLabels = { bar: 'Bar Chart', histogram: 'Histogram', scatter: 'Scatter Plot', box: 'Box Plot', line: 'Line Chart', pie: 'Pie Chart' };
    const titleStr = params.title || typeLabels[type] || type;

    const div = document.createElement('div');
    div.className = 'chart-container';
    div.id = chartId;
    div.innerHTML = `
        <div class="chart-header">
            <span class="chart-title">📊 ${escHtml(titleStr)}</span>
            <button class="chart-del-btn" onclick="removeChart('${chartId}')" title="Hapus grafik">✕</button>
        </div>
        <div class="chart-plot" id="plot-${chartId}"></div>`;
    viewer.appendChild(div);

    Plotly.newPlot(`plot-${chartId}`, chartJson.data, chartJson.layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['sendDataToCloud'],
    });
}

function removeChart(chartId) {
    document.getElementById(chartId)?.remove();
    if (document.querySelectorAll('.chart-container').length === 0) {
        const viewer = document.getElementById('chart-viewer');
        viewer.innerHTML += `<div id="chart-empty" class="empty-state" style="height:100%;width:100%">
            <div class="empty-state-icon">📈</div>
            <h3>Chart Viewer</h3>
            <p>Grafik hasil analisis akan tampil di sini.</p>
        </div>`;
    }
}

// ─── Export Output ─────────────────────────────────────────────────────────────
async function exportOutput(fmt) {
    if (!App.outputHtml) {
        toast('Tidak ada output untuk diekspor', 'warning');
        return;
    }
    setLoading(true, `Mengekspor ke ${fmt.toUpperCase()}...`);
    try {
        const r = await fetch('/api/export/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ format: fmt, output_html: App.outputHtml }),
        });
        if (r.ok) {
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `spss_output.${fmt}`;
            a.click();
            URL.revokeObjectURL(url);
            toast(`Export ${fmt.toUpperCase()} berhasil`, 'success');
        } else {
            const err = await r.json();
            toast('Export gagal: ' + (err.error || ''), 'error');
        }
    } catch (e) {
        toast('Export error: ' + e.message, 'error');
    } finally {
        setLoading(false);
    }
}

// ─── Syntax Log ───────────────────────────────────────────────────────────────
function addSyntax(cmd) {
    const now = new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    App.syntaxLog.push({ cmd, time: now });
    const viewer = document.getElementById('syntax-viewer');
    viewer.innerHTML = '';
    for (const entry of App.syntaxLog) {
        viewer.innerHTML += `<span class="syntax-comment">* ${entry.time}</span>\n`;
        viewer.innerHTML += parseSyntax(entry.cmd) + '\n\n';
    }
    viewer.scrollTop = viewer.scrollHeight;
}

function parseSyntax(cmd) {
    return cmd
        .replace(/^(\w+)/gm, '<span class="syntax-statement">$1</span>')
        .replace(/='([^']+)'/g, "=<span class='syntax-value'>'$1'</span>")
        .replace(/\b(WITH|BY|INTO|FROM|TO|WHERE|STATISTICS|VARIABLES|METHOD)\b/g,
                 '<span class="syntax-keyword">$1</span>');
}

function generateSyntax(type, params) {
    const syntaxMap = {
        descriptive: () => `DESCRIPTIVES VARIABLES=${params.variables?.join(' ')} /STATISTICS=MEAN STDDEV MIN MAX VARIANCE SKEWNESS KURTOSIS.`,
        frequencies: () => `FREQUENCIES VARIABLES=${params.variables?.join(' ')} /BARCHART.`,
        crosstab: () => `CROSSTABS TABLES=${params.row_var} BY ${params.col_var} /STATISTICS=CHISQ.`,
        ttest_independent: () => `T-TEST GROUPS=${params.group_var}(${params.group1} ${params.group2}) /VARIABLES=${params.dep_var}.`,
        ttest_onesample: () => `T-TEST TESTVAL=${params.test_value || 0} /VARIABLES=${params.variables?.join(' ')}.`,
        ttest_paired: () => `T-TEST PAIRS=${params.pairs?.map(p => `${p.var1} WITH ${p.var2}`).join(', ')}.`,
        anova_oneway: () => `ONEWAY ${params.dep_var} BY ${params.factor_var} /STATISTICS DESCRIPTIVES.`,
        anova_twoway: () => `UNIANOVA ${params.dep_var} BY ${params.factor1} ${params.factor2}.`,
        correlation_pearson: () => `CORRELATIONS VARIABLES=${params.variables?.join(' ')} /PRINT=TWOTAIL SIG.`,
        correlation_spearman: () => `NONPAR CORR VARIABLES=${params.variables?.join(' ')} /PRINT=SPEARMAN TWOTAIL SIG.`,
        regression_linear: () => `REGRESSION /DEPENDENT=${params.dep_var} /METHOD=ENTER ${params.indep_vars?.join(' ')}.`,
        regression_logistic: () => `LOGISTIC REGRESSION VARIABLES ${params.dep_var} /METHOD=ENTER ${params.indep_vars?.join(' ')}.`,
        normality: () => `EXAMINE VARIABLES=${params.variables?.join(' ')} /PLOT NORMPLOT /STATISTICS DESCRIPTIVES.`,
        chi_square: () => `CROSSTABS TABLES=${params.row_var} BY ${params.col_var} /STATISTICS=CHISQ PHI.`,
        mann_whitney: () => `NPAR TESTS M-W=${params.dep_var} BY ${params.group_var}(${params.group1} ${params.group2}).`,
        wilcoxon: () => `NPAR TESTS WILCOXON=${params.var1} WITH ${params.var2} (PAIRED).`,
        kruskal_wallis: () => `NPAR TESTS K-W=${params.dep_var} BY ${params.group_var}.`,
        factor: () => `FACTOR VARIABLES=${params.variables?.join(' ')} /ROTATION VARIMAX.`,
        cluster: () => `QUICK CLUSTER ${params.variables?.join(' ')} /CLUSTERS=${params.n_clusters || 3}.`,
        reliability: () => `RELIABILITY VARIABLES=${params.variables?.join(' ')} /MODEL=ALPHA.`,
        manova: () => `MANOVA ${params.dep_vars?.join(' ')} BY ${params.factor_var} /PRINT=SIGNIF.`,
    };
    return (syntaxMap[type] ? syntaxMap[type]() : `/* ${type} analysis */`) + '.';
}

// ─── Modal System ──────────────────────────────────────────────────────────────
let currentModal = null;

function openModal(id) {
    closeModal();
    const overlay = document.getElementById('modal-overlay');
    overlay.classList.add('open');
    document.querySelectorAll('.modal-content').forEach(m => m.style.display = 'none');
    const m = document.getElementById(id);
    if (m) m.style.display = 'block';
    currentModal = id;
    populateAllSelects();
}

function closeModal() {
    document.getElementById('modal-overlay')?.classList.remove('open');
    currentModal = null;
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

function populateAllSelects() {
    const selects = document.querySelectorAll('.modal-content select.col-select');
    selects.forEach(sel => {
        const current = sel.value;
        sel.innerHTML = '<option value="">-- Pilih Variabel --</option>';
        for (const col of App.columns) {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            sel.appendChild(opt);
        }
        sel.value = current;
    });

    const multiSelects = document.querySelectorAll('.modal-content select.col-multi');
    multiSelects.forEach(sel => {
        const currVals = Array.from(sel.selectedOptions).map(o => o.value);
        sel.innerHTML = '';
        for (const col of App.columns) {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            if (currVals.includes(col)) opt.selected = true;
            sel.appendChild(opt);
        }
    });

    // Numeric only selects
    const numericCols = App.columnInfo.filter(c => c.type === 'numeric').map(c => c.name);
    const numSelects = document.querySelectorAll('.modal-content select.num-select');
    numSelects.forEach(sel => {
        const current = sel.value;
        sel.innerHTML = '<option value="">-- Pilih Variabel Numerik --</option>';
        for (const col of numericCols) {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            sel.appendChild(opt);
        }
        sel.value = current;
    });

    const numMultis = document.querySelectorAll('.modal-content select.num-multi');
    numMultis.forEach(sel => {
        const currVals = Array.from(sel.selectedOptions).map(o => o.value);
        sel.innerHTML = '';
        for (const col of numericCols) {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            if (currVals.includes(col)) opt.selected = true;
            sel.appendChild(opt);
        }
    });
}

function getSelectedValues(selectEl) {
    return Array.from(selectEl.selectedOptions).map(o => o.value).filter(Boolean);
}

// ─── Modal Submit Handlers ─────────────────────────────────────────────────────
function submitDescriptive() {
    const vars = getSelectedValues(document.getElementById('desc-vars'));
    if (!vars.length) { toast('Pilih minimal 1 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('descriptive', { variables: vars });
}

function submitFrequencies() {
    const vars = getSelectedValues(document.getElementById('freq-vars'));
    if (!vars.length) { toast('Pilih minimal 1 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('frequencies', { variables: vars });
}

function submitCrosstab() {
    const row = document.getElementById('crosstab-row').value;
    const col = document.getElementById('crosstab-col').value;
    if (!row || !col) { toast('Pilih Row dan Column variable', 'warning'); return; }
    if (row === col) { toast('Row dan Column harus variabel berbeda', 'warning'); return; }
    closeModal();
    runAnalysis('crosstab', { row_var: row, col_var: col });
}

function submitTTestIndep() {
    const dep = document.getElementById('ttestind-dep').value;
    const grp = document.getElementById('ttestind-grp').value;
    const g1 = document.getElementById('ttestind-g1').value.trim();
    const g2 = document.getElementById('ttestind-g2').value.trim();
    if (!dep || !grp || !g1 || !g2) { toast('Isi semua field', 'warning'); return; }
    closeModal();
    runAnalysis('ttest_independent', { dep_var: dep, group_var: grp, group1: g1, group2: g2 });
}

function submitTTestOne() {
    const vars = getSelectedValues(document.getElementById('ttest1-vars'));
    const val = parseFloat(document.getElementById('ttest1-val').value) || 0;
    if (!vars.length) { toast('Pilih minimal 1 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('ttest_onesample', { variables: vars, test_value: val });
}

function submitTTestPaired() {
    const pairs = [];
    document.querySelectorAll('.paired-row').forEach(row => {
        const v1 = row.querySelector('.paired-v1').value;
        const v2 = row.querySelector('.paired-v2').value;
        if (v1 && v2) pairs.push({ var1: v1, var2: v2 });
    });
    if (!pairs.length) { toast('Tambahkan minimal 1 pasang variabel', 'warning'); return; }
    closeModal();
    runAnalysis('ttest_paired', { pairs });
}

function addPairRow() {
    const container = document.getElementById('paired-container');
    const div = document.createElement('div');
    div.className = 'pair-row paired-row';
    div.innerHTML = `
        <select class="modal-select num-select paired-v1"><option value="">Var 1</option></select>
        <span style="color:var(--text-muted);font-size:12px">↔</span>
        <select class="modal-select num-select paired-v2"><option value="">Var 2</option></select>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--accent-red);cursor:pointer;font-size:16px">✕</button>`;
    container.appendChild(div);
    populateAllSelects();
}

function submitAnovaOne() {
    const dep = document.getElementById('anova1-dep').value;
    const fac = document.getElementById('anova1-fac').value;
    if (!dep || !fac) { toast('Pilih Dependent dan Factor variable', 'warning'); return; }
    closeModal();
    runAnalysis('anova_oneway', { dep_var: dep, factor_var: fac });
}

function submitAnovaTwo() {
    const dep = document.getElementById('anova2-dep').value;
    const f1 = document.getElementById('anova2-fac1').value;
    const f2 = document.getElementById('anova2-fac2').value;
    if (!dep || !f1 || !f2) { toast('Isi semua field', 'warning'); return; }
    closeModal();
    runAnalysis('anova_twoway', { dep_var: dep, factor1: f1, factor2: f2 });
}

function submitMANOVA() {
    const deps = getSelectedValues(document.getElementById('manova-deps'));
    const fac = document.getElementById('manova-fac').value;
    if (!deps.length || !fac) { toast('Pilih Dependent Variables dan Factor', 'warning'); return; }
    closeModal();
    runAnalysis('manova', { dep_vars: deps, factor_var: fac });
}

function submitCorrPearson() {
    const vars = getSelectedValues(document.getElementById('pearson-vars'));
    if (vars.length < 2) { toast('Pilih minimal 2 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('correlation_pearson', { variables: vars });
}

function submitCorrSpearman() {
    const vars = getSelectedValues(document.getElementById('spearman-vars'));
    if (vars.length < 2) { toast('Pilih minimal 2 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('correlation_spearman', { variables: vars });
}

function submitRegLinear() {
    const dep = document.getElementById('reglin-dep').value;
    const indep = getSelectedValues(document.getElementById('reglin-indep'));
    if (!dep || !indep.length) { toast('Isi semua field', 'warning'); return; }
    if (indep.includes(dep)) { toast('Dependent variable tidak boleh ada di Independent variables', 'warning'); return; }
    closeModal();
    runAnalysis('regression_linear', { dep_var: dep, indep_vars: indep });
}

function submitRegLogistic() {
    const dep = document.getElementById('reglog-dep').value;
    const indep = getSelectedValues(document.getElementById('reglog-indep'));
    if (!dep || !indep.length) { toast('Isi semua field', 'warning'); return; }
    closeModal();
    runAnalysis('regression_logistic', { dep_var: dep, indep_vars: indep });
}

function submitNormality() {
    const vars = getSelectedValues(document.getElementById('norm-vars'));
    if (!vars.length) { toast('Pilih minimal 1 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('normality', { variables: vars });
}

function submitChiSquare() {
    const row = document.getElementById('chi-row').value;
    const col = document.getElementById('chi-col').value;
    if (!row || !col) { toast('Pilih Row dan Column variable', 'warning'); return; }
    closeModal();
    runAnalysis('chi_square', { row_var: row, col_var: col });
}

function submitMannWhitney() {
    const dep = document.getElementById('mw-dep').value;
    const grp = document.getElementById('mw-grp').value;
    const g1 = document.getElementById('mw-g1').value.trim();
    const g2 = document.getElementById('mw-g2').value.trim();
    if (!dep || !grp || !g1 || !g2) { toast('Isi semua field', 'warning'); return; }
    closeModal();
    runAnalysis('mann_whitney', { dep_var: dep, group_var: grp, group1: g1, group2: g2 });
}

function submitWilcoxon() {
    const v1 = document.getElementById('wilcox-v1').value;
    const v2 = document.getElementById('wilcox-v2').value;
    if (!v1 || !v2) { toast('Pilih kedua variabel', 'warning'); return; }
    if (v1 === v2) { toast('Variabel harus berbeda', 'warning'); return; }
    closeModal();
    runAnalysis('wilcoxon', { var1: v1, var2: v2 });
}

function submitKruskal() {
    const dep = document.getElementById('krus-dep').value;
    const grp = document.getElementById('krus-grp').value;
    if (!dep || !grp) { toast('Pilih Dependent dan Group variable', 'warning'); return; }
    closeModal();
    runAnalysis('kruskal_wallis', { dep_var: dep, group_var: grp });
}

function submitFactor() {
    const vars = getSelectedValues(document.getElementById('factor-vars'));
    const nf = parseInt(document.getElementById('factor-nfact').value) || 0;
    if (vars.length < 2) { toast('Pilih minimal 2 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('factor', { variables: vars, n_factors: nf || null });
}

function submitCluster() {
    const vars = getSelectedValues(document.getElementById('cluster-vars'));
    const nc = parseInt(document.getElementById('cluster-nclusters').value) || 3;
    if (vars.length < 1) { toast('Pilih minimal 1 variabel', 'warning'); return; }
    closeModal();
    runAnalysis('cluster', { variables: vars, n_clusters: nc });
}

function submitReliability() {
    const vars = getSelectedValues(document.getElementById('rel-vars'));
    if (vars.length < 2) { toast('Pilih minimal 2 variabel (item)', 'warning'); return; }
    closeModal();
    runAnalysis('reliability', { variables: vars });
}

// Chart modals
function submitBarChart() {
    const x = document.getElementById('bar-x').value;
    const y = document.getElementById('bar-y').value;
    if (!x) { toast('Pilih variabel X', 'warning'); return; }
    closeModal();
    generateChart('bar', { x_var: x, y_var: y || null, title: `Bar Chart: ${x}` });
}

function submitHistogram() {
    const x = document.getElementById('hist-x').value;
    if (!x) { toast('Pilih variabel', 'warning'); return; }
    const bins = parseInt(document.getElementById('hist-bins').value) || 20;
    closeModal();
    generateChart('histogram', { x_var: x, bins, title: `Histogram: ${x}` });
}

function submitScatter() {
    const x = document.getElementById('scatter-x').value;
    const y = document.getElementById('scatter-y').value;
    if (!x || !y) { toast('Pilih variabel X dan Y', 'warning'); return; }
    closeModal();
    generateChart('scatter', { x_var: x, y_var: y, title: `Scatter: ${x} vs ${y}` });
}

function submitBoxPlot() {
    const y = document.getElementById('box-y').value;
    const x = document.getElementById('box-x').value;
    if (!y) { toast('Pilih variabel Y', 'warning'); return; }
    closeModal();
    generateChart('box', { y_var: y, x_var: x || null, title: `Box Plot: ${y}` });
}

function submitLineChart() {
    const x = document.getElementById('line-x').value;
    const ys = getSelectedValues(document.getElementById('line-ys'));
    if (!x || !ys.length) { toast('Pilih variabel X dan Y', 'warning'); return; }
    closeModal();
    generateChart('line', { x_var: x, y_vars: ys, title: `Line Chart: ${ys.join(', ')}` });
}

function submitPieChart() {
    const names = document.getElementById('pie-names').value;
    const vals = document.getElementById('pie-values').value;
    if (!names) { toast('Pilih variabel Names/Kategori', 'warning'); return; }
    closeModal();
    generateChart('pie', { names_var: names, values_var: vals || null, title: `Pie Chart: ${names}` });
}

// ─── Status Bar & Utils ────────────────────────────────────────────────────────
function updateStatusBar() {
    const el = document.getElementById('status-dataset');
    if (el) el.textContent = App.datasetName
        ? `${App.datasetName} | ${App.datasetRows.toLocaleString()} baris, ${App.datasetCols} kolom`
        : 'Tidak ada dataset aktif';
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ─── Drag & Drop Upload ────────────────────────────────────────────────────────
function setupDropzone() {
    const panel = document.getElementById('data-editor-panel');
    panel.addEventListener('dragover', e => {
        e.preventDefault();
        panel.style.outline = '2px dashed var(--accent-blue)';
    });
    panel.addEventListener('dragleave', () => {
        panel.style.outline = '';
    });
    panel.addEventListener('drop', async e => {
        e.preventDefault();
        panel.style.outline = '';
        const file = e.dataTransfer.files[0];
        if (file) {
            const dt = new DataTransfer();
            dt.items.add(file);
            const input = document.getElementById('file-input');
            input.files = dt.files;
            await handleFileUpload(input);
        }
    });
}

// ─── Delete Row / Add Row (client-side) ────────────────────────────────────────
// addRow, addColumn, deleteRow etc. defined above in editable table section

function hapusData() {
    if (!App.datasetId) { toast('Tidak ada dataset aktif', 'warning'); return; }
    if (!confirm(`Hapus dataset "${App.datasetName}"? Ini tidak dapat dibatalkan.`)) return;
    fetch(`/api/dataset/${App.datasetId}/delete/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': CSRF },
    }).then(r => r.json()).then(res => {
        if (res.success) {
            App.datasetId = null;
            App.datasetName = null;
            App.columns = [];
            App.columnInfo = [];
            document.getElementById('data-table-wrapper').innerHTML = '';
            document.getElementById('dataset-info').textContent = '';
            updateStatusBar();
            loadDatasets();
            toast('Dataset berhasil dihapus', 'success');
            // Show empty state
            const wrapper = document.getElementById('data-editor-panel');
            wrapper.innerHTML = `
                <div id="empty-state" class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <h3>Belum ada data</h3>
                    <p>Upload file CSV, Excel, atau SPSS (.sav) untuk memulai analisis</p>
                    <div class="upload-zone" onclick="triggerUpload()">
                        📂 Klik atau seret file ke sini
                    </div>
                </div>
                <div id="data-table-wrapper" class="data-table-wrapper"></div>`;
        }
    });
}

// ─── Sidebar Analysis Shortcuts ────────────────────────────────────────────────
function sidebarAnalysis(type) {
    const modalMap = {
        descriptive: 'modal-descriptive',
        frequencies: 'modal-frequencies',
        crosstab: 'modal-crosstab',
        ttest_independent: 'modal-ttest-indep',
        ttest_onesample: 'modal-ttest-one',
        ttest_paired: 'modal-ttest-paired',
        anova_oneway: 'modal-anova-one',
        anova_twoway: 'modal-anova-two',
        manova: 'modal-manova',
        correlation_pearson: 'modal-pearson',
        correlation_spearman: 'modal-spearman',
        regression_linear: 'modal-reg-linear',
        regression_logistic: 'modal-reg-logistic',
        normality: 'modal-normality',
        chi_square: 'modal-chi',
        mann_whitney: 'modal-mann-whitney',
        wilcoxon: 'modal-wilcoxon',
        kruskal_wallis: 'modal-kruskal',
        factor: 'modal-factor',
        cluster: 'modal-cluster',
        reliability: 'modal-reliability',
        bar: 'modal-bar',
        histogram: 'modal-histogram',
        scatter: 'modal-scatter',
        box: 'modal-box',
        line: 'modal-line',
        pie: 'modal-pie',
    };
    const modalId = modalMap[type];
    if (modalId) openModal(modalId);
    else toast('Analisis tidak ditemukan', 'error');

    // Highlight in sidebar
    document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll(`.sidebar-item[data-type="${type}"]`).forEach(i => i.classList.add('active'));
}

// ─── Init ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    setupDropzone();
    await loadDatasets();
    switchTab('data-editor');
    updateStatusBar();

    // Default syntax message
    document.getElementById('syntax-viewer').innerHTML =
        `<span class="syntax-comment">* SPSS Online - Syntax Log\n* Perintah analisis akan muncul di sini.\n* ${new Date().toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>\n\n`;
});
