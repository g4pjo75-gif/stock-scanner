/**
 * 글로벌 이평선 대순환 & 모멘텀 스캐너
 * 메인 앱 로직
 */

const API_BASE = '';

// 상태 관리
const state = {
    currentMarket: 'JP',
    currentTicker: null,
    currentAnalysis: null,
    stockList: [],
    reportDate: new Date().toISOString().split('T')[0]
};

// 유틸리티 함수
function formatPrice(price, market = 'US') {
    if (market === 'JP') {
        return `¥${Math.round(price).toLocaleString()}`;
    }
    return `$${price.toFixed(2)}`;
}

function formatPercent(pct) {
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
}

function getStageClass(stage) {
    if (stage === 6) return 'badge-stage-6';
    if (stage === 1) return 'badge-stage-1';
    return 'badge-stage';
}

function getStageDescription(stage) {
    const descriptions = {
        1: '정배열 상승',
        2: '단기 조정',
        3: '하락 전환',
        4: '역배열 하락',
        5: '바닥 다지기',
        6: '상승 반전 🚀'
    };
    return descriptions[stage] || '분석 불가';
}

function getScoreClass(score) {
    if (score >= 70) return 'badge-score-high';
    if (score >= 50) return 'badge-score-mid';
    return 'badge-score-low';
}

// 토스트 알림
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// API 요청
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) throw new Error('API 오류');
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast('데이터 로딩 실패', 'error');
        throw error;
    }
}

// === 시장 토글 ===
function initMarketToggle() {
    const buttons = document.querySelectorAll('.market-btn');

    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            state.currentMarket = btn.dataset.market;
            loadStockList();
            loadAvailableDates(); // 시장 변경 시 날짜 목록도 갱신

            // 차트 초기화
            clearAnalysis();
        });
    });
}

// === 종목 리스트 ===
async function loadStockList() {
    const listEl = document.getElementById('stock-list');
    listEl.innerHTML = '<div class="loading"><div class="spinner"></div><span>데이터 로딩 중...</span></div>';

    try {
        // 저장된 리포트 먼저 시도
        let data = await fetchAPI(`/api/reports?market=${state.currentMarket}&report_date=${state.reportDate}`);

        if (data.items.length === 0) {
            // 리포트가 없으면 안내 메시지 표시 (자동 스캔 하지 않음)
            listEl.innerHTML = '<div class="loading"><span>저장된 데이터가 없습니다.<br>⚡ 전체 스캔 버튼을 눌러주세요.</span></div>';
            return;
        }

        state.stockList = data.items;
        renderStockList(data.items);

    } catch (error) {
        listEl.innerHTML = '<div class="loading"><span>데이터 로딩 실패</span></div>';
    }
}

function renderStockList(items, filter = 'all') {
    const listEl = document.getElementById('stock-list');

    const filtered = filter === 'all'
        ? items
        : items.filter(item => item.stage === parseInt(filter));

    if (filtered.length === 0) {
        listEl.innerHTML = '<div class="loading"><span>해당 조건의 종목이 없습니다</span></div>';
        return;
    }

    listEl.innerHTML = filtered.map(item => `
        <div class="stock-item ${state.currentTicker === item.ticker ? 'active' : ''}" 
             data-ticker="${item.ticker}">
            <div class="stock-info">
                <div class="stock-ticker">${item.ticker}</div>
                <div class="stock-name">${item.name || ''}</div>
            </div>
            <div class="stock-price">
                <div class="price">${formatPrice(item.price, state.currentMarket)}</div>
                <div class="change ${item.change_pct >= 0 ? 'positive' : 'negative'}">
                    ${formatPercent(item.change_pct)}
                </div>
            </div>
            <div class="stock-badges">
                <span class="badge ${getStageClass(item.stage)}">Stage ${item.stage}</span>
                <span class="badge badge-score">⭐ ${item.score}</span>
            </div>
        </div>
    `).join('');

    // 클릭 이벤트
    listEl.querySelectorAll('.stock-item').forEach(el => {
        el.addEventListener('click', () => {
            selectStock(el.dataset.ticker);
        });
    });
}

// === 종목 선택 ===
async function selectStock(ticker) {
    state.currentTicker = ticker;

    // 리스트 활성화 표시
    document.querySelectorAll('.stock-item').forEach(el => {
        el.classList.toggle('active', el.dataset.ticker === ticker);
    });

    // 분석 데이터 가져오기
    try {
        const data = await fetchAPI(`/api/analyze/${ticker}`);
        state.currentAnalysis = data;

        updateAnalysisUI(data);
        updateChart(ticker);

        // 버튼 활성화
        document.getElementById('add-portfolio-btn').disabled = false;
        document.getElementById('position-calc-btn').disabled = false;

    } catch (error) {
        console.error('분석 실패:', error);
    }
}
window.selectStock = selectStock;

function updateAnalysisUI(data) {
    // 상단 정보
    document.getElementById('selected-ticker').textContent = data.ticker;
    document.getElementById('selected-name').textContent = data.name;
    document.getElementById('current-price').textContent = formatPrice(data.price, state.currentMarket);

    const changePctEl = document.getElementById('change-pct');
    changePctEl.textContent = formatPercent(data.change_pct);
    changePctEl.className = `change-pct ${data.change_pct >= 0 ? 'positive' : 'negative'}`;

    // 스테이지
    document.getElementById('stage-number').textContent = data.stage;
    document.getElementById('stage-desc').textContent = getStageDescription(data.stage);

    const indicator = document.querySelector('.stage-indicator');
    indicator.style.left = `${(data.stage - 1) * 16.66}%`;

    // 모멘텀
    document.getElementById('momentum-pct').textContent = `${data.momentum_pct}%`;
    document.getElementById('vcp-ratio').textContent = data.vcp_ratio.toFixed(2);

    // 거래량
    document.getElementById('vol-ratio').textContent = `${data.vol_ratio}x`;
    document.getElementById('distance-pct').textContent = `${data.distance_pct}%`;

    // 점수
    document.getElementById('score-value').textContent = data.score;
    const scoreCircle = document.getElementById('score-circle');
    const circumference = 2 * Math.PI * 45;
    scoreCircle.style.strokeDashoffset = circumference - (data.score / 100) * circumference;

    // 어드바이스
    const adviceBox = document.getElementById('advice-box');
    document.getElementById('advice-text').textContent = data.advice;

    // 어드바이스 색상
    if (data.advice.includes('매수급소')) {
        adviceBox.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%)';
    } else if (data.advice.includes('매도경고')) {
        adviceBox.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(245, 158, 11, 0.2) 100%)';
    } else {
        adviceBox.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)';
    }
}

function clearAnalysis() {
    state.currentTicker = null;
    state.currentAnalysis = null;

    document.getElementById('selected-ticker').textContent = '-';
    document.getElementById('selected-name').textContent = '종목을 선택하세요';
    document.getElementById('current-price').textContent = '-';
    document.getElementById('change-pct').textContent = '-';
    document.getElementById('change-pct').className = 'change-pct';

    document.getElementById('stage-number').textContent = '-';
    document.getElementById('stage-desc').textContent = '분석 대기';
    document.getElementById('momentum-pct').textContent = '-';
    document.getElementById('vcp-ratio').textContent = '-';
    document.getElementById('vol-ratio').textContent = '-';
    document.getElementById('distance-pct').textContent = '-';
    document.getElementById('score-value').textContent = '-';
    document.getElementById('advice-text').textContent = '종목을 선택하면 AI 어드바이스가 표시됩니다.';

    document.getElementById('add-portfolio-btn').disabled = true;
    document.getElementById('position-calc-btn').disabled = true;
}

// === 필터 탭 ===
function initFilterTabs() {
    const tabs = document.querySelectorAll('.filter-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            renderStockList(state.stockList, tab.dataset.filter);
        });
    });
}

// === 검색 ===
function initSearch() {
    const input = document.getElementById('ticker-search');
    const btn = document.getElementById('search-btn');

    const doSearch = () => {
        let ticker = input.value.trim().toUpperCase();
        if (!ticker) return;

        // 일본 시장일 때 .T 접미사 자동 추가
        if (state.currentMarket === 'JP' && !ticker.includes('.T')) {
            ticker = ticker + '.T';
        }

        selectStock(ticker);
    };

    btn.addEventListener('click', doSearch);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doSearch();
    });
}

// === 스캔 버튼 ===
function initScanButton() {
    const btn = document.getElementById('scan-btn');

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> 스캔 중...';

        try {
            await fetchAPI(`/api/scan?market=${state.currentMarket}&top_n=30`);
            await loadStockList();
            showToast('스캔 완료!');
        } catch (error) {
            showToast('스캔 실패', 'error');
        }

        btn.disabled = false;
        btn.innerHTML = '<span class="scan-icon">⚡</span><span>전체 스캔</span>';
    });
}

// === 날짜 선택 ===
function initDatePicker() {
    const input = document.getElementById('report-date');
    input.value = state.reportDate;

    input.addEventListener('change', () => {
        state.reportDate = input.value;
        loadStockList();
        // 선택한 날짜에 맞게 버튼 활성화 상태 업데이트
        updateAvailableDatesUI();
    });

    // 데이터가 있는 날짜 목록 로드
    loadAvailableDates();
}

// 데이터가 있는 날짜 목록 로드
async function loadAvailableDates() {
    try {
        const response = await fetch(`/api/reports/dates?market=${state.currentMarket}`);
        const data = await response.json();
        state.availableDates = data.dates || [];
        renderAvailableDates();
    } catch (error) {
        console.error('Failed to load available dates:', error);
    }
}

// 데이터가 있는 날짜 버튼 렌더링
function renderAvailableDates() {
    const container = document.getElementById('available-dates');
    if (!container) return;

    if (!state.availableDates || state.availableDates.length === 0) {
        container.innerHTML = '<span class="no-data-hint">📅 스캔된 리포트가 없습니다</span>';
        return;
    }

    container.innerHTML = state.availableDates.map(date => {
        const isActive = date === state.reportDate;
        const displayDate = formatDateShort(date);
        return `<button class="date-btn ${isActive ? 'active' : ''}" data-date="${date}">${displayDate}</button>`;
    }).join('');

    // 클릭 이벤트
    container.querySelectorAll('.date-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const date = btn.dataset.date;
            state.reportDate = date;
            document.getElementById('report-date').value = date;
            loadStockList();
            updateAvailableDatesUI();
        });
    });
}

// 날짜 버튼 활성화 상태 업데이트
function updateAvailableDatesUI() {
    const container = document.getElementById('available-dates');
    if (!container) return;

    container.querySelectorAll('.date-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.date === state.reportDate);
    });
}

// 날짜 짧게 표시 (MM/DD 형식)
function formatDateShort(dateStr) {
    const date = new Date(dateStr);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${month}/${day}`;
}

// === 모달 ===
function initModals() {
    // 포트폴리오 추가 모달
    const addModal = document.getElementById('add-modal');
    const addBtn = document.getElementById('add-portfolio-btn');

    addBtn.addEventListener('click', () => {
        if (!state.currentAnalysis) return;

        const data = state.currentAnalysis;
        document.getElementById('form-ticker').value = `${data.ticker} - ${data.name}`;
        document.getElementById('form-entry-price').value = data.price;
        document.getElementById('form-stop-loss').value = data.stop_loss;
        document.getElementById('form-entry-date').value = new Date().toISOString().split('T')[0];

        addModal.classList.add('active');
    });

    // 포지션 계산기 모달
    const posModal = document.getElementById('position-modal');
    const posBtn = document.getElementById('position-calc-btn');

    posBtn.addEventListener('click', () => {
        if (!state.currentAnalysis) return;

        const data = state.currentAnalysis;
        document.getElementById('calc-price').value = data.price;
        document.getElementById('calc-stop-loss').value = data.stop_loss;

        posModal.classList.add('active');
    });

    // 사용 방법 모달
    const helpModal = document.getElementById('help-modal');
    const helpBtn = document.getElementById('help-btn');

    if (helpBtn && helpModal) {
        helpBtn.addEventListener('click', () => {
            helpModal.classList.add('active');
        });
    }

    // 모달 닫기
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            addModal.classList.remove('active');
            posModal.classList.remove('active');
            if (helpModal) helpModal.classList.remove('active');
        });
    });

    // 배경 클릭으로 닫기
    [addModal, posModal, helpModal].filter(m => m).forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // 포트폴리오 추가 폼
    document.getElementById('add-portfolio-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = state.currentAnalysis;
        const payload = {
            ticker: data.ticker,
            name: data.name,
            market: state.currentMarket,
            entry_date: document.getElementById('form-entry-date').value || new Date().toISOString().split('T')[0],
            entry_price: parseFloat(document.getElementById('form-entry-price').value),
            entry_stage: data.stage,
            entry_score: data.score || 0,
            stop_loss: parseFloat(document.getElementById('form-stop-loss').value) || 0,
            target_price: parseFloat(document.getElementById('form-target-price').value) || 0,
            quantity: parseInt(document.getElementById('form-quantity').value) || 0,
            memo: document.getElementById('form-memo').value
        };

        try {
            await fetchAPI('/api/portfolio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            showToast('포트폴리오에 추가되었습니다!');
            addModal.classList.remove('active');
            loadPortfolio();

        } catch (error) {
            showToast('추가 실패', 'error');
        }
    });

    // 포지션 계산 폼
    document.getElementById('position-calc-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            total_capital: parseFloat(document.getElementById('calc-capital').value),
            current_price: parseFloat(document.getElementById('calc-price').value),
            stop_loss_price: parseFloat(document.getElementById('calc-stop-loss').value),
            risk_pct: parseFloat(document.getElementById('calc-risk-pct').value)
        };

        try {
            const result = await fetchAPI('/api/calculate-position', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            document.getElementById('result-shares').textContent = `${result.shares}주`;
            document.getElementById('result-position').textContent = formatPrice(result.position_value, state.currentMarket);
            document.getElementById('result-risk').textContent = formatPrice(result.risk_amount, state.currentMarket);
            document.getElementById('result-pct').textContent = `${result.position_pct}%`;

            document.getElementById('calc-result').classList.remove('hidden');

        } catch (error) {
            showToast('계산 실패', 'error');
        }
    });
}

// === 초기화 ===
document.addEventListener('DOMContentLoaded', () => {
    initMarketToggle();
    initFilterTabs();
    initSearch();
    initScanButton();
    initDatePicker();
    initModals();

    loadStockList();

    // SVG 그라데이션 추가
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.innerHTML = `
        <defs>
            <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#3b82f6"/>
                <stop offset="100%" style="stop-color:#8b5cf6"/>
            </linearGradient>
        </defs>
    `;
    svg.style.position = 'absolute';
    svg.style.width = '0';
    svg.style.height = '0';
    document.body.appendChild(svg);
});
