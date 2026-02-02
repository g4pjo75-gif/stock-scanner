window.schedulerLoaded = true;

document.addEventListener('DOMContentLoaded', () => {
    initScheduler();
});

const schedulerState = {
    enabled: false,
    hour: 22,
    minute: 0,
    nextRun: null,
    lastRun: null,
    reportDates: [],
    currentMarketFilter: 'ALL',
    currentReportDate: null,
    cachedReportItems: []
};

async function initScheduler() {
    // UI 요소
    const toggle = document.getElementById('scheduler-toggle');
    const timeInput = document.getElementById('scheduler-time');
    const saveBtn = document.getElementById('save-schedule-btn');
    const runBtn = document.getElementById('run-now-btn');

    if (!toggle || !timeInput || !saveBtn || !runBtn) return;

    // 상태 로드
    await loadSchedulerStatus();
    await loadSchedulerReports();

    // 초기 로딩 시 진행 중인지 확인
    try {
        const statusResponse = await fetch('/api/scheduler/progress');
        const statusData = await statusResponse.json();
        if (statusData.is_running) {
            startProgressPolling();
        }
    } catch (e) {
        console.error('Initial progress check failed:', e);
    }

    // 이벤트 리스너
    toggle.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        await toggleScheduler(enabled);
    });

    saveBtn.addEventListener('click', async () => {
        const timeValue = timeInput.value;
        if (!timeValue) return;
        const [hour, minute] = timeValue.split(':').map(Number);
        await saveSchedule(hour, minute);
    });

    runBtn.addEventListener('click', async () => {
        // confirm 제거: 사용자 요청에 따라 더 즉각적인 반응을 위해
        await runManualScan();
    });

    // 시장 필터 버튼 이벤트
    const filterBtns = document.querySelectorAll('.market-filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            schedulerState.currentMarketFilter = btn.dataset.market;
            applyMarketFilter();
        });
    });
}

/**
 * 스케줄러 상태 로드
 */
async function loadSchedulerStatus() {
    try {
        const response = await fetch('/api/scheduler/status');
        const data = await response.json();

        schedulerState.enabled = data.enabled;
        schedulerState.hour = data.hour;
        schedulerState.minute = data.minute;
        schedulerState.nextRun = data.next_run;
        schedulerState.lastRun = data.last_run;

        updateSchedulerUI();
    } catch (error) {
        console.error('Failed to load scheduler status:', error);
    }
}

/**
 * UI 업데이트
 */
function updateSchedulerUI() {
    const toggle = document.getElementById('scheduler-toggle');
    const statusText = document.getElementById('scheduler-status-text');
    const timeInput = document.getElementById('scheduler-time');
    const nextRunVal = document.getElementById('next-run-time');

    if (toggle) toggle.checked = schedulerState.enabled;
    if (statusText) {
        statusText.textContent = schedulerState.enabled ? 'ON' : 'OFF';
        statusText.className = `status-badge ${schedulerState.enabled ? 'on' : 'off'}`;
    }
    if (timeInput) {
        const h = String(schedulerState.hour).padStart(2, '0');
        const m = String(schedulerState.minute).padStart(2, '0');
        timeInput.value = `${h}:${m}`;
    }
    if (nextRunVal) {
        if (schedulerState.enabled && schedulerState.nextRun) {
            const date = new Date(schedulerState.nextRun);
            nextRunVal.textContent = date.toLocaleString('ko-KR');
        } else {
            nextRunVal.textContent = '예약된 스캔 없음';
        }
    }
}

/**
 * 스케줄러 토글
 */
async function toggleScheduler(enabled) {
    try {
        const response = await fetch('/api/scheduler/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();

        if (data.success) {
            schedulerState.enabled = enabled;
            await loadSchedulerStatus(); // 다음 실행 시간 갱신을 위해 다시 로드
            showToast(`스케줄러가 ${enabled ? '활성화' : '비활성화'} 되었습니다.`);
        }
    } catch (error) {
        console.error('Toggle failed:', error);
        showToast('스케줄러 설정 변경에 실패했습니다.', 'error');
    }
}

/**
 * 스케줄 시간 저장
 */
async function saveSchedule(hour, minute) {
    try {
        const response = await fetch('/api/scheduler/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hour, minute })
        });
        const data = await response.json();

        if (data.success) {
            schedulerState.hour = hour;
            schedulerState.minute = minute;
            await loadSchedulerStatus();
            showToast('스케줄 시간이 저장되었습니다.');
        }
    } catch (error) {
        console.error('Save failed:', error);
        showToast('시간 저장에 실패했습니다.', 'error');
    }
}

/**
 * 수동 스캔 실행 (비블로킹)
 */
async function runManualScan() {
    const runBtn = document.getElementById('run-now-btn');
    if (runBtn.disabled) return;

    try {
        const response = await fetch('/api/scheduler/run', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showToast('스캔이 시작되었습니다. 잠시만 기다려주세요.');
            startProgressPolling();
        } else {
            showToast(data.message || '스캔 시작 실패', 'error');
        }
    } catch (error) {
        console.error('Manual scan failed:', error);
        showToast('스캔 요청 중 오류가 발생했습니다.', 'error');
    }
}

let progressInterval = null;

function startProgressPolling() {
    if (progressInterval) clearInterval(progressInterval);

    const progressContainer = document.getElementById('scheduler-progress');
    const runBtn = document.getElementById('run-now-btn');

    if (progressContainer) progressContainer.classList.remove('hidden');
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.innerHTML = '<span>⏳</span> 스캔 중...';
    }

    progressInterval = setInterval(checkScanProgress, 2000);
    checkScanProgress(); // 즉시 한 번 실행
}

async function checkScanProgress() {
    try {
        const response = await fetch('/api/scheduler/progress');
        const data = await response.json();

        const messageEl = document.getElementById('progress-message');
        const barFill = document.getElementById('progress-bar-fill');
        const runBtn = document.getElementById('run-now-btn');
        const progressContainer = document.getElementById('scheduler-progress');

        if (data.is_running) {
            if (messageEl) messageEl.textContent = data.message;
            if (barFill) {
                barFill.classList.add('scanning');
                // 마켓별 대략적 진행도 표시 (US 완료 시 50%)
                let progress = 10;
                if (data.current_market === 'US') progress = 25;
                if (data.current_market === 'JP') progress = 75;
                barFill.style.width = `${progress}%`;
            }
        } else {
            // 스캔 완료
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;

                if (messageEl) messageEl.textContent = '스캔 완료';
                if (barFill) {
                    barFill.style.width = '100%';
                    barFill.classList.remove('scanning');
                }

                setTimeout(() => {
                    if (progressContainer) progressContainer.classList.add('hidden');
                    if (runBtn) {
                        runBtn.disabled = false;
                        runBtn.innerHTML = '<span>⚡</span> 지금 스캔';
                    }
                }, 3000);

                showToast('전체 스캔이 완료되었습니다.');
                loadSchedulerReports();
            }
        }
    } catch (error) {
        console.error('Progress check failed:', error);
    }
}

/**
 * 스케줄 리포트 날짜 목록 로드
 */
async function loadSchedulerReports() {
    try {
        const response = await fetch('/api/scheduler/reports');
        const data = await response.json();

        const dateContainer = document.getElementById('scheduler-report-dates');
        if (!dateContainer) return;

        if (!data.dates || data.dates.length === 0) {
            dateContainer.innerHTML = '<div class="empty-msg">저장된 리포트가 없습니다.</div>';
            return;
        }

        dateContainer.innerHTML = '';
        data.dates.forEach(date => {
            const btn = document.createElement('button');
            btn.className = 'report-date-btn';
            btn.textContent = date;
            btn.onclick = () => selectReportDate(date, btn);
            dateContainer.appendChild(btn);
        });
    } catch (error) {
        console.error('Failed to load reports:', error);
    }
}

/**
 * 특정 날짜 리포트 조회
 */
async function selectReportDate(date, btn) {
    // 버튼 활성화 표시
    document.querySelectorAll('.report-date-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    schedulerState.currentReportDate = date;

    try {
        const detailsContainer = document.getElementById('scheduler-report-details');
        detailsContainer.innerHTML = '<div class="loading">데이터 로딩 중...</div>';

        // US와 JP 데이터를 병렬로 가져옴
        const [usRes, jpRes] = await Promise.all([
            fetch(`/api/reports?market=US&report_date=${date}`),
            fetch(`/api/reports?market=JP&report_date=${date}`)
        ]);

        const [usData, jpData] = await Promise.all([
            usRes.json(),
            jpRes.json()
        ]);

        const combinedItems = [
            ...(usData.items || []),
            ...(jpData.items || [])
        ];

        // 캐시에 저장
        schedulerState.cachedReportItems = combinedItems;

        if (combinedItems.length === 0) {
            detailsContainer.innerHTML = '<div class="empty-msg">내용이 없는 리포트입니다.</div>';
            return;
        }

        // 점수 순으로 정렬 (선택 사항)
        combinedItems.sort((a, b) => b.score - a.score);

        // 현재 필터 적용하여 렌더링
        applyMarketFilter();
    } catch (error) {
        console.error('Failed to load report details:', error);
        showToast('리포트 상세 조회에 실패했습니다.', 'error');
    }
}

/**
 * 시장 필터 적용
 */
function applyMarketFilter() {
    const items = schedulerState.cachedReportItems;
    const filter = schedulerState.currentMarketFilter;

    if (!items || items.length === 0) {
        return;
    }

    let filteredItems = items;
    if (filter !== 'ALL') {
        filteredItems = items.filter(item => item.market === filter);
    }

    if (filteredItems.length === 0) {
        const container = document.getElementById('scheduler-report-details');
        container.innerHTML = `<div class="empty-msg">${filter} 시장의 종목이 없습니다.</div>`;
        return;
    }

    renderReportDetails(filteredItems);
}

/**
 * 리포트 상세 렌더링
 */
function renderReportDetails(items) {
    const container = document.getElementById('scheduler-report-details');

    let html = `
        <div class="scheduler-report-table-container">
            <table class="scheduler-report-table">
                <thead>
                    <tr>
                        <th>시장</th>
                        <th>종목</th>
                        <th>가격</th>
                        <th>스테이지</th>
                        <th>점수</th>
                    </tr>
                </thead>
                <tbody>
    `;

    items.forEach(item => {
        html += `
            <tr onclick="onReportItemClick('${item.ticker}')" style="cursor: pointer;">
                <td><span class="market-badge ${item.market}">${item.market}</span></td>
                <td><strong>${item.ticker}</strong><br><small>${item.name || ''}</small></td>
                <td>${item.price}</td>
                <td><span class="stage-badge stage-${item.stage}">${item.stage}단계</span></td>
                <td><span class="score-badge">${item.score}</span></td>
            </tr>
        `;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;
}

/**
 * 리포트 종목 클릭 시 메인 분석 화면으로 연동
 */
window.onReportItemClick = function (ticker) {
    if (window.selectStock) {
        window.selectStock(ticker);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (typeof selectStock === 'function') {
        selectStock(ticker);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// selectStock를 window에 명시적으로 연결 (app.js 로드 시점 이슈 대비)
if (typeof selectStock === 'function') {
    window.selectStock = selectStock;
}
