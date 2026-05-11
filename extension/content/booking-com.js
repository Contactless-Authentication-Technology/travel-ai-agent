function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setNativeValue(element, value) {
  const valueSetter = Object.getOwnPropertyDescriptor(element, "value")?.set;
  const prototype = Object.getPrototypeOf(element);
  const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;

  if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
    prototypeValueSetter.call(element, value);
  } else if (valueSetter) {
    valueSetter.call(element, value);
  } else {
    element.value = value;
  }

  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function simulateClick(element) {
  const rect = element.getBoundingClientRect();
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  const props = { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y };

  element.dispatchEvent(new PointerEvent("pointerdown", props));
  element.dispatchEvent(new MouseEvent("mousedown", props));
  element.dispatchEvent(new PointerEvent("pointerup", props));
  element.dispatchEvent(new MouseEvent("mouseup", props));
  element.dispatchEvent(new MouseEvent("click", props));
}

async function fillDestination(destination) {
  const input =
    document.querySelector('input[name="ss"]') ||
    document.querySelector('[data-testid="destination-container"] input');

  if (!input) {
    return { ok: false, error: "Destination input not found" };
  }

  input.focus();
  setNativeValue(input, destination);

  await wait(1000);

  const firstSuggestion =
    document.querySelector('[data-testid="autocomplete-result"]') ||
    document.querySelector('[data-testid="destination-container"] [role="option"]') ||
    document.querySelector('li[id^="autocomplete"] [role="option"]') ||
    document.querySelector('[data-testid="internal-input-container"] ~ ul li:first-child');

  if (firstSuggestion) {
    firstSuggestion.click();
    await wait(500);
  }

  return { ok: true, field: "destination", value: destination };
}

async function openDatePicker() {
  const dateButton =
    document.querySelector('[data-testid="searchbox-dates-container"]') ||
    document.querySelector('[data-testid="date-display-field-start"]') ||
    document.querySelector('[data-testid="date-display-field-end"]');

  if (!dateButton) {
    return { ok: false, error: "Date picker button not found" };
  }

  dateButton.click();
  await wait(700);

  return { ok: true };
}

function getCalendarDateButtons() {
  return Array.from(document.querySelectorAll("[data-date]"));
}

function getVisibleDateRange() {
  const dates = getCalendarDateButtons()
    .map((button) => button.getAttribute("data-date"))
    .filter(Boolean)
    .sort();

  if (dates.length === 0) {
    return null;
  }

  return {
    first: dates[0],
    last: dates[dates.length - 1]
  };
}

function getNextMonthButton() {
  return (
    document.querySelector('[data-testid="calendar-arrow-right"]') ||
    document.querySelector('button[aria-label*="Next"]') ||
    document.querySelector('button[aria-label*="다음"]')
  );
}

function getPrevMonthButton() {
  return (
    document.querySelector('[data-testid="calendar-arrow-left"]') ||
    document.querySelector('button[aria-label*="Previous"]') ||
    document.querySelector('button[aria-label*="이전"]')
  );
}

function findDateButton(date) {
  return document.querySelector(`[data-date="${date}"]`);
}

function extractHotelCards() {
  const cards = Array.from(
    document.querySelectorAll('[data-testid="property-card"]')
  );

  return cards.map((card, index) => {
    const name = card
      .querySelector('[data-testid="title"]')
      ?.textContent?.trim();

    const price = card
      .querySelector('[data-testid="price-and-discounted-price"]')
      ?.textContent?.trim();

    const scoreText = card
      .querySelector('[data-testid="review-score"]')
      ?.textContent?.trim();

    const description = card.textContent.trim();

    return {
      index,
      name,
      price,
      scoreText,
      description
    };
  });
}

function clickFirstHotelCard() {
  const firstCard = document.querySelector(
    '[data-testid="property-card"] a'
  );

  if (!firstCard) {
    return {
      ok: false,
      error: "No hotel card found"
    };
  }

  firstCard.click();

  return {
    ok: true
  };
}

function parseHotelScore(scoreText) {
  if (!scoreText) {
    return 0;
  }

  const match = scoreText.replace(",", ".").match(/\d+(\.\d+)?/);

  if (!match) {
    return 0;
  }

  return Number(match[0]);
}

function calculateHotelRankingScore(hotel, preferences = []) {
  let score = parseHotelScore(hotel.scoreText);
  const reasons = [];

  if (score > 0) {
    reasons.push(`Review score: ${score}`);
  }

  const description = hotel.description || "";

  if (
    preferences.includes("breakfast_included") &&
    (
      description.includes("조식") ||
      description.toLowerCase().includes("breakfast")
    )
  ) {
    score += 1;
    reasons.push("Matched preference: breakfast_included");
  }

  if (
    preferences.includes("near_eiffel_tower") &&
    (
      description.includes("에펠") ||
      description.toLowerCase().includes("eiffel")
    )
  ) {
    score += 1;
    reasons.push("Matched preference: near_eiffel_tower");
  }

  if (
    preferences.includes("near_metro") &&
    (
      description.includes("지하철") ||
      description.includes("역") ||
      description.toLowerCase().includes("metro") ||
      description.toLowerCase().includes("subway")
    )
  ) {
    score += 1;
    reasons.push("Matched preference: near_metro");
  }

  return {
    score,
    reasons
  };
}

function clickBestMatchedHotel(preferences = []) {
  const cards = Array.from(
    document.querySelectorAll('[data-testid="property-card"]')
  );

  if (!cards.length) {
    return {
      ok: false,
      error: "No hotel cards found"
    };
  }

  let bestCard = null;
  let bestHotel = null;
  let bestRankingScore = -1;
  let bestReasons = [];
  let recommendedHotelCard = null;

  cards.forEach((card, index) => {
    const hotel = {
      index,
      name: card.querySelector('[data-testid="title"]')?.textContent?.trim(),
      price: card
        .querySelector('[data-testid="price-and-discounted-price"]')
        ?.textContent?.trim(),
      scoreText: card
        .querySelector('[data-testid="review-score"]')
        ?.textContent?.trim(),
      description: card.textContent.trim()
    };

    const rankingResult = calculateHotelRankingScore(
      hotel,
      preferences
    );

    if (rankingResult.score > bestRankingScore) {
      bestRankingScore = rankingResult.score;
      bestCard = card;
      bestHotel = hotel;
      bestReasons = rankingResult.reasons;
    }
  });

  if (!bestCard) {
    return {
      ok: false,
      error: "No matched hotel found"
    };
  }

  const hotelLink = bestCard.querySelector("a");

  if (!hotelLink) {
    return {
      ok: false,
      error: "No hotel link found"
    };
  }

  recommendedHotelCard = bestCard;

  return {
    ok: true,
    selectedHotel: bestHotel.name,
    rankingScore: bestRankingScore,
    preferences,
    reasons: bestReasons,
    hotelIndex: bestHotel.index
  };
}

function confirmRecommendedHotelSelection() {
  if (!recommendedHotelCard) {
    return {
      ok: false,
      error: "No recommended hotel stored"
    };
  }

  const hotelLink = recommendedHotelCard.querySelector("a");

  if (!hotelLink) {
    return {
      ok: false,
      error: "No hotel link found"
    };
  }

  hotelLink.click();

  return {
    ok: true
  };
}

async function findDateButtonWithNavigation(date, maxClicks = 12) {
  for (let i = 0; i <= maxClicks; i++) {
    const dateButton = findDateButton(date);

    if (dateButton) {
      return dateButton;
    }

    const range = getVisibleDateRange();

    if (!range) {
      return null;
    }

    if (date < range.first) {
      const prevButton = getPrevMonthButton();
      if (!prevButton) return null;
      prevButton.click();
      await wait(500);
      continue;
    }

    if (date > range.last) {
      const nextButton = getNextMonthButton();
      if (!nextButton) return null;
      nextButton.click();
      await wait(500);
      continue;
    }

    return null;
  }

  return null;
}

async function selectBookingDates(checkIn, checkOut) {
  const opened = await openDatePicker();

  if (!opened.ok) {
    return opened;
  }

  const checkInButton = await findDateButtonWithNavigation(checkIn);

  if (!checkInButton) {
    return { ok: false, error: `Check-in date not found after navigation: ${checkIn}` };
  }

  checkInButton.click();
  await wait(500);

  const checkOutButton = await findDateButtonWithNavigation(checkOut);

  if (!checkOutButton) {
    return { ok: false, error: `Check-out date not found after navigation: ${checkOut}` };
  }

  checkOutButton.click();
  await wait(500);

  return { ok: true, field: "dates", checkIn, checkOut };
}

async function openGuestSelector() {
  const guestButton =
    document.querySelector('[data-testid="occupancy-config"]') ||
    document.querySelector('[data-testid="searchbox-occupancy"]');

  if (!guestButton) {
    return { ok: false, error: "Guest selector button not found" };
  }

  guestButton.click();
  await wait(500);

  return { ok: true };
}

function getOccupancyIconButtons() {
  const popup = document.querySelector('[data-testid="occupancy-popup"]');

  if (!popup) return null;

  // 순서: 성인-, 성인+, 어린이-, 어린이+, 객실-, 객실+
  return Array.from(popup.querySelectorAll("button")).filter(
    (b) => !b.textContent.trim()
  );
}

function getAdultCountElement() {
  const popup = document.querySelector('[data-testid="occupancy-popup"]');

  if (!popup) return null;

  return Array.from(popup.querySelectorAll("span")).find((el) =>
    /^\d+$/.test(el.textContent.trim())
  );
}

function getAdultMinusButton() {
  const buttons = getOccupancyIconButtons();
  return buttons?.[0] || null;
}

function getAdultPlusButton() {
  const buttons = getOccupancyIconButtons();
  return buttons?.[1] || null;
}

async function setAdultCount(targetAdults) {
  const opened = await openGuestSelector();

  if (!opened.ok) return opened;

  await wait(500);

  const countElement = getAdultCountElement();

  if (!countElement) {
    return { ok: false, error: "Adult count element not found" };
  }

  let current = parseInt(countElement.textContent.trim(), 10);

  if (isNaN(current)) {
    return { ok: false, error: "Failed to read adult count" };
  }

  const MAX_CLICKS = 10;

  for (let i = 0; current < targetAdults && i < MAX_CLICKS; i++) {
    const plusButton = getAdultPlusButton();

    if (!plusButton) {
      return { ok: false, error: "Plus button not found" };
    }

    simulateClick(plusButton);
    await wait(400);

    const next = parseInt(getAdultCountElement()?.textContent.trim(), 10);

    if (isNaN(next) || next === current) {
      return { ok: false, error: `Adult count stuck at ${current}` };
    }

    current = next;
  }

  for (let i = 0; current > targetAdults && i < MAX_CLICKS; i++) {
    const minusButton = getAdultMinusButton();

    if (!minusButton) {
      return { ok: false, error: "Minus button not found" };
    }

    simulateClick(minusButton);
    await wait(400);

    const next = parseInt(getAdultCountElement()?.textContent.trim(), 10);

    if (isNaN(next) || next === current) {
      return { ok: false, error: `Adult count stuck at ${current}` };
    }

    current = next;
  }

  return { ok: true, field: "adults", value: targetAdults };
}

async function clickGuestDoneButton() {
  const popup = document.querySelector('[data-testid="occupancy-popup"]');

  if (!popup) {
    return { ok: false, error: "Occupancy popup not found" };
  }

  const doneButton =
    popup.querySelector('[data-testid="occupancy-popup-continue-button"]') ||
    Array.from(popup.querySelectorAll("button")).find((btn) => {
      const text = btn.textContent.trim();
      return text === "완료" || text === "Done" || text === "확인";
    });

  if (!doneButton) {
    return { ok: false, error: "Guest done button not found" };
  }

  doneButton.click();
  await wait(300);

  return { ok: true };
}

async function clickSearchButton() {
  const searchButton =
    document.querySelector('[data-testid="search-button"]') ||
    document.querySelector('button[type="submit"]');

  if (!searchButton) {
    return { ok: false, error: "Search button not found" };
  }

  searchButton.click();

  return { ok: true };
}

async function runBookingFlow(data) {
  try {
    console.log("[Travel Agent] Run booking flow:", data);

    const destinationResult = await fillDestination(data.destination);
    if (!destinationResult.ok) return destinationResult;

    await wait(800);

    const datesResult = await selectBookingDates(data.checkIn, data.checkOut);
    if (!datesResult.ok) return datesResult;

    await wait(800);

    const adultsResult = await setAdultCount(data.adults);
    if (!adultsResult.ok) return adultsResult;

    await wait(800);

    const doneResult = await clickGuestDoneButton();
    if (!doneResult.ok) return doneResult;

    await wait(500);

    return await clickSearchButton();

  } catch (error) {
    console.error("[Travel Agent] Flow failed:", error);
    return { ok: false, error: error.message };
  }
}
