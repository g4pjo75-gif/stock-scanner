4. PC 대시보드 UI 설계 (Next.js + Tailwind)

화면 구성 (Dashboard Layout)
상단 Bar: 국가 선택 (JP/US), 특정 종목 티커 검색창.

좌측 리스트: 저녁 10시 생성된 오늘의 공략주 (스테이지 6 위주).

우측 메인: 선택 종목의 상세 차트 및 '정밀 분석 결과' 패널.

하단 패널: My Portfolio (내가 산 종목들의 현재 상태, 수익률, 대응 가이드 실시간 노출).

My Portfolio UI 상세
JavaScript

// 포트폴리오 관리 테이블 예시
<div className="bg-gray-900 p-6 rounded-xl mt-6 border border-gray-800">
  <h2 className="text-xl font-bold text-blue-400 mb-4">내 보유 종목 대응 가이드</h2>
  <table className="w-full text-left">
    <thead>
      <tr className="text-gray-500 border-b border-gray-800">
        <th className="p-3">종목</th>
        <th className="p-3">매수가</th>
        <th className="p-3">현재가</th>
        <th className="p-3">상태</th>
        <th className="p-3">대응 어드바이스</th>
      </tr>
    </thead>
    <tbody>
      <tr className="hover:bg-gray-800 transition">
        <td className="p-3 font-bold">NVDA</td>
        <td className="p-3">$130.50</td>
        <td className="p-3 text-red-400 font-bold">$145.20</td>
        <td className="p-3"><span className="bg-green-900 text-green-400 px-2 py-1 rounded">Stage 1</span></td>
        <td className="p-3 text-yellow-500">✅ 추세 양호. 20일선 이탈 전까지 홀딩.</td>
      </tr>
      {/* 데이터 반복 */}
    </tbody>
  </table>
</div>