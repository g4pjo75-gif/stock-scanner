/**
 * Lightweight Charts 차트 위젯 (v4.x API)
 * - 캔들스틱 차트
 * - 이동평균선 (5, 20, 40일)
 * - 거래량 차트
 */

let chart = null;
let candleSeries = null;
let volumeSeries = null;
let ma5Series = null;
let ma20Series = null;
let ma40Series = null;

/**
 * 차트 데이터 로드 및 표시
 */
async function updateChart(ticker) {
    const container = document.getElementById('tradingview-chart');

    // 로딩 표시
    container.innerHTML = `
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #6b7280;
        ">
            <div class="spinner"></div>
            <span style="margin-top: 16px;">차트 로딩 중...</span>
        </div>
    `;

    try {
        // API에서 차트 데이터 가져오기 (캐시 방지)
        const timestamp = Date.now();
        const response = await fetch(`/api/chart/${encodeURIComponent(ticker)}?period=6mo&_t=${timestamp}`);
        if (!response.ok) {
            throw new Error('차트 데이터를 가져올 수 없습니다');
        }
        const data = await response.json();

        // 컨테이너 초기화
        container.innerHTML = '';

        // 차트 생성 (Lightweight Charts v4.x API)
        chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight,
            layout: {
                background: { type: 'solid', color: '#1a1a2e' },
                textColor: '#d1d5db',
            },
            grid: {
                vertLines: { color: '#2d2d44' },
                horzLines: { color: '#2d2d44' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#3f3f5a',
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.25,
                },
            },
            timeScale: {
                borderColor: '#3f3f5a',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // 캔들스틱 시리즈 (v4.x API)
        candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderDownColor: '#ef5350',
            borderUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            wickUpColor: '#26a69a',
        });
        candleSeries.setData(data.candles);

        // 이동평균선 5일 (파란색)
        ma5Series = chart.addSeries(LightweightCharts.LineSeries, {
            color: '#2563eb',
            lineWidth: 2,
            title: 'MA5',
        });
        ma5Series.setData(data.ma5);

        // 이동평균선 20일 (주황색)
        ma20Series = chart.addSeries(LightweightCharts.LineSeries, {
            color: '#ea580c',
            lineWidth: 2,
            title: 'MA20',
        });
        ma20Series.setData(data.ma20);

        // 이동평균선 40일 (빨간색)
        ma40Series = chart.addSeries(LightweightCharts.LineSeries, {
            color: '#dc2626',
            lineWidth: 2,
            title: 'MA40',
        });
        ma40Series.setData(data.ma40);

        // 거래량 시리즈 (v4.x API)
        volumeSeries = chart.addSeries(LightweightCharts.HistogramSeries, {
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });
        volumeSeries.setData(data.volumes);

        // 차트 크기에 맞게 조정
        chart.timeScale().fitContent();

        // 윈도우 리사이즈 대응
        const resizeHandler = () => {
            if (chart && container) {
                chart.applyOptions({
                    width: container.clientWidth,
                    height: container.clientHeight
                });
            }
        };
        window.addEventListener('resize', resizeHandler);

    } catch (error) {
        console.error('Chart error:', error);
        container.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: #ef4444;
            ">
                <span style="font-size: 2rem; margin-bottom: 16px;">⚠️</span>
                <span>차트를 표시할 수 없습니다</span>
                <span style="font-size: 0.875rem; color: #6b7280; margin-top: 8px;">${error.message}</span>
            </div>
        `;
    }
}

/**
 * 차트 플레이스홀더 초기화
 */
function initChartPlaceholder() {
    const container = document.getElementById('tradingview-chart');
    container.innerHTML = `
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #6b7280;
        ">
            <span style="font-size: 3rem; margin-bottom: 16px;">📊</span>
            <span>종목을 선택하면 차트가 표시됩니다</span>
        </div>
    `;
}

/**
 * 차트 정리
 */
function destroyChart() {
    if (chart) {
        chart.remove();
        chart = null;
        candleSeries = null;
        volumeSeries = null;
        ma5Series = null;
        ma20Series = null;
        ma40Series = null;
    }
}

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    initChartPlaceholder();
});
