const requestInput = document.getElementById("requestInput");
const resultView = document.getElementById("resultView");
const recommendationsRoot = document.getElementById("recommendations");
const roomOptionsRoot = document.getElementById("roomOptions");
const flightResultsRoot = document.getElementById("flightResults");
const priceCalendarRoot = document.getElementById("priceCalendar");
const requestSummaryRoot = document.getElementById("requestSummary");
const agentStatusValue = document.getElementById("agentStatusValue");
const agentStatusMeta = document.getElementById("agentStatusMeta");

let sessionState = null;
let selectedHotelIndex = null;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderResult(value) {
  resultView.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function renderPriceCalendar(calendar) {
  if (!calendar?.days?.length) {
    priceCalendarRoot.innerHTML = "";
    return;
  }

  const prices = calendar.days.map((d) => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice || 1;
  const selectedDate = sessionState?.travelRequest?.departureDate;

  const firstDay = new Date(calendar.days[0].date).getDay();
  const dayNames = ["일", "월", "화", "수", "목", "금", "토"];

  const headers = dayNames.map((d) => `<div class="calendar-day-header">${d}</div>`).join("");
  const blanks = Array(firstDay).fill(`<div class="calendar-day empty"></div>`).join("");

  const dayCells = calendar.days.map((d) => {
    const ratio = (d.price - minPrice) / range;
    let tier = ratio < 0.25 ? "cheap" : ratio < 0.6 ? "moderate" : "expensive";
    const isSelected = d.date === selectedDate ? "selected-date" : "";
    const dateNum = d.date.slice(8);
    const priceStr = `₩${Math.round(d.price / 10000)}만`;

    return `
      <div class="calendar-day ${tier} ${isSelected}">
        <div class="cal-date">${dateNum}</div>
        <div class="cal-price">${priceStr}</div>
      </div>
    `;
  }).join("");

  const cheapestBadge = calendar.cheapestDate
    ? `<div class="calendar-cheapest-badge">최저가: ${calendar.cheapestDate} · ₩${Number(calendar.cheapestPrice).toLocaleString()}</div>`
    : "";

  priceCalendarRoot.innerHTML = `
    <div class="subtle" style="margin-bottom: 6px;">${escapeHtml(calendar.month)} 출발 날짜별 최저가 (1인 기준)</div>
    <div class="calendar-grid">${headers}${blanks}${dayCells}</div>
    ${cheapestBadge}
  `;
}

function formatFlightTime(isoStr) {
  if (!isoStr) return "-";
  const d = new Date(isoStr);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${mm}/${dd} ${hh}:${min}`;
}

function renderFlightLeg(label, flight, isReturn = false) {
  const dep = isReturn ? flight.returnDeparture : flight.departure;
  const arr = isReturn ? flight.returnArrival : flight.arrival;
  const stops = isReturn ? flight.returnStops : flight.stops;
  const duration = isReturn ? flight.returnDurationHours : flight.durationHours;

  if (!dep) return "";

  const stopsLabel = stops === 0 ? "직항" : `${stops}회 경유`;
  const durationLabel = duration ? `${duration}시간` : "-";
  const timeLabel = `${formatFlightTime(dep)} → ${formatFlightTime(arr)}`;

  return `
    <div class="flight-leg">
      <span class="flight-leg-label">${escapeHtml(label)}</span>
      <span class="subtle">${escapeHtml(stopsLabel)} · ${escapeHtml(durationLabel)}</span>
      <div class="flight-leg-time">${escapeHtml(timeLabel)}</div>
    </div>
  `;
}

function renderFlightResults(flights) {
  if (!flights?.length) {
    flightResultsRoot.innerHTML = `<div class="subtle">아직 항공편을 검색하지 않았습니다.</div>`;
    return;
  }

  flightResultsRoot.innerHTML = flights.map((flight) => {
    const adults = sessionState?.travelRequest?.adults || 1;
    const perPerson = flight.price ? Math.round(flight.price / adults) : null;
    const priceLabel = flight.price
      ? adults > 1
        ? `₩${Number(flight.price).toLocaleString()} (성인 ${adults}인 총액 · 1인당 약 ₩${perPerson.toLocaleString()})`
        : `₩${Number(flight.price).toLocaleString()}`
      : "가격 정보 없음";
    const airlinesLabel = (flight.airlineNames || flight.airlines || []).join(", ") || "-";
    const isRoundTrip = !!flight.returnDeparture;
    const routeLabel = flight.flyFromCity && flight.flyToCity
      ? `${flight.flyFromCity} (${flight.flyFrom}) ↔ ${flight.flyToCity} (${flight.flyTo})`
      : `${flight.flyFrom || "-"} ↔ ${flight.flyTo || "-"}`;

    const outboundLeg = renderFlightLeg("가는 편", flight, false);
    const returnLeg = isRoundTrip ? renderFlightLeg("오는 편", flight, true) : "";
    const divider = isRoundTrip ? `<div class="flight-leg-divider"></div>` : "";

    return `
      <div class="flight-card">
        <div class="flight-price">${escapeHtml(priceLabel)}</div>
        <div class="flight-route">${escapeHtml(isRoundTrip ? routeLabel : routeLabel.replace("↔", "→"))}</div>
        <div class="subtle" style="margin-bottom: 10px;">${escapeHtml(airlinesLabel)}</div>
        ${outboundLeg}
        ${divider}
        ${returnLeg}
        ${flight.deepLink ? `<a class="flight-link" href="${escapeHtml(flight.deepLink)}" target="_blank">Kiwi.com에서 예약하기 →</a>` : ""}
      </div>
    `;
  }).join("");
}

function buildSummaryItem(label, value) {
  return `
    <div class="summary-item">
      <div class="summary-label">${escapeHtml(label)}</div>
      <div class="summary-value">${escapeHtml(value)}</div>
    </div>
  `;
}

function renderRequestSummary(session) {
  const travelRequest = session?.travelRequest;

  if (!travelRequest) {
    requestSummaryRoot.innerHTML = buildSummaryItem("상태", "아직 요청이 해석되지 않았습니다.");
    return;
  }

  const preferences = travelRequest.hotelPreference?.length
    ? travelRequest.hotelPreference.join(", ")
    : "없음";

  requestSummaryRoot.innerHTML = [
    buildSummaryItem("출발지", travelRequest.origin || "서울"),
    buildSummaryItem("목적지", travelRequest.destination || "-"),
    buildSummaryItem("일정", `${travelRequest.departureDate} ~ ${travelRequest.returnDate}`),
    buildSummaryItem("인원", `성인 ${travelRequest.adults}명`),
    buildSummaryItem("선호", preferences)
  ].join("");
}

function buildBadges(hotel) {
  const badges = [];

  if (hotel.signals?.reviewTier === "excellent") badges.push("평점 매우 높음");
  else if (hotel.signals?.reviewTier === "strong") badges.push("평점 높음");
  else if (hotel.signals?.reviewTier === "good") badges.push("평점 양호");

  if (hotel.signals?.luxuryTier === "strong") badges.push("럭셔리 강함");
  else if (hotel.signals?.luxuryTier === "good") badges.push("고급 숙소");

  if (hotel.signals?.valueBucket === "strong") badges.push("가성비 매우 좋음");
  else if (hotel.signals?.valueBucket === "good") badges.push("가성비 좋음");
  else if (hotel.signals?.valueBucket === "moderate") badges.push("가성비 무난");

  if (hotel.signals?.hasBreakfast) badges.push("조식");
  if (hotel.signals?.hasMetroAccess) badges.push("지하철");

  if (hotel.signals?.eiffelDistanceKm !== null && hotel.signals?.eiffelDistanceKm !== undefined) {
    badges.push(`에펠탑 ${hotel.signals.eiffelDistanceKm}km`);
  } else if (hotel.signals?.mentionsEiffel) {
    badges.push("에펠탑 언급");
  }

  return badges;
}

async function updateSelectedHotelIndex(hotelIndex) {
  selectedHotelIndex = hotelIndex;
  await fetchJson("/api/session/selection", {
    method: "POST",
    body: JSON.stringify({ hotelIndex })
  });
  renderRecommendations(sessionState?.recommendations || []);
}

function renderRecommendations(recommendations) {
  if (!recommendations?.length) {
    recommendationsRoot.innerHTML = `
      <div class="subtle">아직 추천 결과가 없습니다. Booking.com 검색 결과 페이지에서 추천을 실행해 주세요.</div>
    `;
    return;
  }

  const selected = selectedHotelIndex ?? sessionState?.selectedHotelIndex ?? recommendations[0].index;
  selectedHotelIndex = selected;

  recommendationsRoot.innerHTML = recommendations.map((hotel, position) => {
    const badges = buildBadges(hotel);
    const selectedClass = hotel.index === selected ? "selected" : "";
    const reasons = hotel.reasons?.length ? hotel.reasons.join(" | ") : "추천 이유 없음";

    return `
      <div class="recommendation ${selectedClass}">
        <div><strong>TOP ${position + 1}</strong> · ${escapeHtml(hotel.name || "Unknown hotel")}</div>
        <div class="subtle" style="margin-top: 6px;">점수 ${escapeHtml(hotel.rankingScore)} · 리뷰 ${escapeHtml(hotel.scoreText || "-")} · ${escapeHtml(hotel.price || "가격 정보 없음")}</div>
        <div class="badge-row">
          ${badges.length ? badges.map((badge) => `<span class="badge">${escapeHtml(badge)}</span>`).join("") : '<span class="badge">추가 신호 없음</span>'}
        </div>
        <div class="reason-list">${escapeHtml(reasons)}</div>
        <div class="button-row">
          <button data-select-hotel="${hotel.index}" class="${hotel.index === selected ? "" : "secondary"}">
            ${hotel.index === selected ? "선택됨" : "이 호텔 선택"}
          </button>
        </div>
      </div>
    `;
  }).join("");

  recommendationsRoot
    .querySelectorAll("[data-select-hotel]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        updateSelectedHotelIndex(Number(button.dataset.selectHotel));
      });
    });
}

function renderRoomOptions(roomOptions) {
  if (!roomOptions?.length) {
    roomOptionsRoot.innerHTML = `
      <div class="subtle">아직 객실 옵션이 없습니다. 호텔 상세 페이지에서 객실 옵션을 불러와 주세요.</div>
    `;
    return;
  }

  roomOptionsRoot.innerHTML = roomOptions.map((option, index) => {
    const badges = [];

    if (option.breakfastIncluded) badges.push("조식 포함");
    if (option.freeCancellation) badges.push("무료 취소");
    if (option.payLater) badges.push("현장 결제 가능");
    if (option.highlights?.length) {
      option.highlights.forEach((item) => badges.push(item));
    }

    return `
      <div class="room-option">
        <div><strong>옵션 ${index + 1}</strong> · ${escapeHtml(option.roomName)}</div>
        <div class="subtle" style="margin-top: 6px; font-size: 15px; color: #152033; font-weight: 700;">
          ${escapeHtml(option.displayPrice || option.price || "가격 정보 없음")}
        </div>
        <div class="badge-row" style="margin-top: 8px;">
          ${badges.length ? badges.map((badge) => `<span class="badge">${escapeHtml(badge)}</span>`).join("") : '<span class="badge">추가 정보 없음</span>'}
        </div>
        <div class="reason-list">${escapeHtml(option.optionSummary || option.text || "")}</div>
      </div>
    `;
  }).join("");
}

function renderAgentStatus(session) {
  const status = session?.agentStatus;

  if (status?.connected) {
    agentStatusValue.textContent = "연결됨";
    agentStatusValue.classList.add("connected");
    agentStatusMeta.textContent = `최근 연결: ${status.lastSeenAt || "-"} / ${status.url || "-"}`;
    return;
  }

  agentStatusValue.textContent = "연결 대기 중";
  agentStatusValue.classList.remove("connected");
  agentStatusMeta.textContent = "Booking.com 탭을 열어 두면 extension이 자동으로 연결됩니다.";
}

async function refreshSession() {
  const data = await fetchJson("/api/session");
  sessionState = data.session;
  selectedHotelIndex = sessionState.selectedHotelIndex;
  renderRequestSummary(sessionState);
  renderFlightResults(sessionState.flightResults || []);
  renderRecommendations(sessionState.recommendations || []);
  renderRoomOptions(sessionState.roomOptions || []);
  renderAgentStatus(sessionState);

  if (sessionState.lastResult) {
    renderResult(sessionState.lastResult);
  }
}

async function enqueueCommand(action, payload = {}) {
  const data = await fetchJson("/api/commands", {
    method: "POST",
    body: JSON.stringify({ action, payload })
  });

  renderResult({
    ok: true,
    message: "명령이 큐에 등록되었습니다. Booking.com 탭에서 곧 실행됩니다.",
    command: data.command
  });

  return data.command;
}

document.getElementById("parseButton").addEventListener("click", async () => {
  const data = await fetchJson("/api/parse", {
    method: "POST",
    body: JSON.stringify({ text: requestInput.value.trim() })
  });
  sessionState = {
    ...(sessionState || {}),
    travelRequest: data.travelRequest,
    payload: data.payload
  };
  renderRequestSummary(sessionState);
  renderResult(data);
});

document.getElementById("runSearchButton").addEventListener("click", async () => {
  const payload = sessionState?.payload?.payload;

  if (!payload) {
    renderResult("먼저 요청을 해석해 주세요.");
    return;
  }

  await enqueueCommand("RUN_BOOKING_FLOW", payload);
});

document.getElementById("recommendButton").addEventListener("click", async () => {
  const preferences = sessionState?.payload?.payload?.hotelPreference || [];
  await enqueueCommand("GET_TOP_HOTEL_RECOMMENDATIONS", {
    hotelPreference: preferences,
    limit: 3
  });
});

document.getElementById("bestMatchButton").addEventListener("click", async () => {
  const preferences = sessionState?.payload?.payload?.hotelPreference || [];
  await enqueueCommand("CLICK_BEST_MATCHED_HOTEL", {
    hotelPreference: preferences
  });
});

document.getElementById("confirmHotelButton").addEventListener("click", async () => {
  if (selectedHotelIndex === null || selectedHotelIndex === undefined) {
    renderResult("먼저 추천 후보 중 하나를 선택해 주세요.");
    return;
  }

  await enqueueCommand("CONFIRM_SPECIFIC_HOTEL_SELECTION", {
    hotelIndex: selectedHotelIndex
  });
});

document.getElementById("extractRoomsButton").addEventListener("click", async () => {
  await enqueueCommand("EXTRACT_ROOM_OPTIONS");
});

document.getElementById("priceCalendarButton").addEventListener("click", async () => {
  if (!sessionState?.travelRequest) {
    renderResult("먼저 여행 요청을 해석해 주세요.");
    return;
  }

  renderResult("날짜별 가격 조회 중...");
  try {
    const data = await fetchJson("/api/flights/price-calendar", { method: "POST" });
    if (data.ok) {
      renderPriceCalendar(data.calendar);
      renderResult({ ok: true, month: data.calendar.month, cheapestDate: data.calendar.cheapestDate });
    } else {
      renderResult({ ok: false, error: data.error });
    }
  } catch (e) {
    renderResult({ ok: false, error: e.message });
  }
});

document.getElementById("searchFlightsButton").addEventListener("click", async () => {
  if (!sessionState?.travelRequest) {
    renderResult("먼저 여행 요청을 해석해 주세요.");
    return;
  }

  renderResult("항공편 검색 중...");
  try {
    const data = await fetchJson("/api/flights/search", { method: "POST" });
    if (data.ok) {
      renderFlightResults(data.flights);
      renderResult({ ok: true, count: data.flights.length, flights: data.flights });
    } else {
      renderResult({ ok: false, error: data.error });
    }
  } catch (e) {
    renderResult({ ok: false, error: e.message });
  }
});

refreshSession();
setInterval(refreshSession, 2500);
