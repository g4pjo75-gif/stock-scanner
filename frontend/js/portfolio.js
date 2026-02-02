/**
 * 포트폴리오 관리
 */

let portfolioStatus = '';
let portfolioDateFilter = '';

// 포트폴리오 로드 및 렌더링 통합
async function loadPortfolio(status = null, date = null) {
    const tbody = document.getElementById('portfolio-body');
    if (status !== null) portfolioStatus = status;
    if (date !== null) portfolioDateFilter = date;

    try {
        const url = portfolioStatus
            ? `/api/portfolio?status=${portfolioStatus}`
            : '/api/portfolio';
        const data = await fetchAPI(url);

        // 등록일 필터 적용
        let items = data.items;
        if (portfolioDateFilter) {
            items = items.filter(item => item.entry_date === portfolioDateFilter);
        }

        renderPortfolioTable(items);

    } catch (error) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="11">데이터 로딩 실패</td></tr>';
    }
}

// 테이블 렌더링 로직 분리
function renderPortfolioTable(items) {
    const tbody = document.getElementById('portfolio-body');

    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="11">포트폴리오가 비어있거나 조건에 맞는 항목이 없습니다</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(item => {
        const profitPct = item.profit_pct || 0;
        const profitClass = profitPct >= 0 ? 'positive' : 'negative';
        const entryDate = item.entry_date || '-';
        const entryScore = item.entry_score || 0;

        return `
            <tr data-id="${item.portfolio_id}" data-ticker="${item.ticker}" data-market="${item.market}" 
                onclick="analyzePortfolioItem('${item.ticker}', '${item.market}')" style="cursor: pointer;">
                <td>
                    <strong>${item.ticker}</strong>
                    <br><small style="color: var(--text-muted)">${item.name || ''}</small>
                </td>
                <td>
                    <span class="badge">${item.market}</span>
                </td>
                <td>${entryDate}</td>
                <td>${formatPrice(item.entry_price, item.market)}</td>
                <td>
                    ${item.current_price ? formatPrice(item.current_price, item.market) : '-'}
                </td>
                <td class="${profitClass}">
                    ${profitPct ? formatPercent(profitPct) : '-'}
                </td>
                <td>
                    <span class="badge ${getStageClass(item.current_stage || item.entry_stage)}">
                        Stage ${item.current_stage || item.entry_stage}
                    </span>
                </td>
                <td>
                    <span class="badge ${getScoreClass(entryScore)}">${entryScore}점</span>
                </td>
                <td>${item.stop_loss ? formatPrice(item.stop_loss, item.market) : '-'}</td>
                <td style="max-width: 150px; overflow: hidden; text-overflow: ellipsis;">
                    ${item.current_advice || item.memo || '-'}
                </td>
                <td>
                    <div style="display: flex; gap: 8px;" onclick="event.stopPropagation()">
                        ${item.current_status === 'HOLDING' ? `
                            <button class="btn btn-danger btn-sm" onclick="sellStock(${item.portfolio_id})">
                                매도
                            </button>
                        ` : ''}
                        <button class="btn btn-secondary btn-sm" onclick="deletePortfolio(${item.portfolio_id})">
                            삭제
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 매도 처리
async function sellStock(portfolioId) {
    if (!confirm('정말 매도 처리하시겠습니까?')) return;

    try {
        await fetchAPI(`/api/portfolio/${portfolioId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_status: 'SOLD' })
        });

        showToast('매도 처리되었습니다');
        loadPortfolio(); // 현재 필터 유지하며 로드

    } catch (error) {
        showToast('처리 실패', 'error');
    }
}

// 삭제
async function deletePortfolio(portfolioId) {
    if (!confirm('정말 삭제하시겠습니까?')) return;

    try {
        await fetchAPI(`/api/portfolio/${portfolioId}`, {
            method: 'DELETE'
        });

        showToast('삭제되었습니다');
        loadPortfolio(); // 현재 필터 유지하며 로드

    } catch (error) {
        showToast('삭제 실패', 'error');
    }
}

// 포트폴리오 항목 클릭 시 분석 표시
async function analyzePortfolioItem(ticker, market) {
    // 해당 시장으로 전환
    if (state.currentMarket !== market) {
        state.currentMarket = market;
        document.querySelectorAll('.market-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.market === market);
        });
    }

    // 분석 실행
    if (window.selectStock) {
        window.selectStock(ticker);
    } else {
        console.error('selectStock function not found');
    }

    // 스크롤을 상단으로 이동하여 분석 결과 표시
    window.scrollTo({ top: 0, behavior: 'smooth' });

    showToast(`${ticker} 분석 중...`);
}

function initPortfolioFilters() {
    const filters = document.querySelectorAll('.portfolio-filter');
    const dateInput = document.getElementById('portfolio-date-filter');
    const clearBtn = document.getElementById('clear-date-filter');

    filters.forEach(btn => {
        btn.addEventListener('click', () => {
            filters.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadPortfolio(btn.dataset.status || '');
        });
    });

    // 등록일 필터
    if (dateInput) {
        dateInput.addEventListener('change', () => {
            loadPortfolio(null, dateInput.value);
        });
    }

    // 초기화 버튼
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            dateInput.value = '';
            loadPortfolio(null, '');
        });
    }
}

// 글로벌 스코프에 노출
window.loadPortfolio = loadPortfolio;
window.sellStock = sellStock;
window.deletePortfolio = deletePortfolio;
window.analyzePortfolioItem = analyzePortfolioItem;

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    initPortfolioFilters();
    loadPortfolio();
});
