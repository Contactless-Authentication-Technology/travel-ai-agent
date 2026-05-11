const requestInput = document.getElementById("requestInput");
const resultView = document.getElementById("resultView");
const recommendationsRoot = document.getElementById("recommendations");
const roomOptionsRoot = document.getElementById("roomOptions");
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

refreshSession();
setInterval(refreshSession, 2500);
