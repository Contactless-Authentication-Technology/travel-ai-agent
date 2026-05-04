console.log("[Travel Agent] Content script loaded");

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

function fillDestination(destination) {
  const input =
    document.querySelector('input[name="ss"]') ||
    document.querySelector('[data-testid="destination-container"] input');

  if (!input) {
    return { ok: false, error: "Destination input not found" };
  }

  input.focus();
  setNativeValue(input, destination);

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

async function findDateButtonWithNavigation(date, maxClicks = 12) {
  for (let i = 0; i <= maxClicks; i++) {
    const dateButton = findDateButton(date);

    if (dateButton) {
      return dateButton;
    }

    const nextButton =
      document.querySelector('[data-testid="calendar-arrow-right"]') ||
      document.querySelector('button[aria-label*="Next"]') ||
      document.querySelector('button[aria-label*="다음"]');

    if (!nextButton) {
      return null;
    }

    nextButton.click();
    await wait(500);
  }

  return null;
}

function findDateButton(date) {
  return document.querySelector(`[data-date="${date}"]`);
}

async function selectBookingDates(checkIn, checkOut) {
  const opened = await openDatePicker();

  if (!opened.ok) {
    return opened;
  }

  const checkInButton = await findDateButtonWithNavigation(checkIn);

  if (!checkInButton) {
    return {
      ok: false,
      error: `Check-in date not found after navigation: ${checkIn}`
    };
  }

  checkInButton.click();
  await wait(500);

  const checkOutButton = await findDateButtonWithNavigation(checkOut);

  if (!checkOutButton) {
    return {
      ok: false,
      error: `Check-out date not found after navigation: ${checkOut}`
    };
  }

  checkOutButton.click();
  await wait(500);

  return {
    ok: true,
    field: "dates",
    checkIn,
    checkOut
  };
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

function getAdultCountElement() {
  return document.querySelector('[data-testid="occupancy-popup"] span');
}

function getAdultPlusButton() {
  return document.querySelector(
    '[data-testid="occupancy-popup"] button[aria-label*="성인 수 증가"], ' +
    '[data-testid="occupancy-popup"] button[aria-label*="Increase adults"]'
  );
}

function getAdultMinusButton() {
  return document.querySelector(
    '[data-testid="occupancy-popup"] button[aria-label*="성인 수 감소"], ' +
    '[data-testid="occupancy-popup"] button[aria-label*="Decrease adults"]'
  );
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

  const plusButton = getAdultPlusButton();
  const minusButton = getAdultMinusButton();

  if (!plusButton || !minusButton) {
    return { ok: false, error: "Plus/Minus button not found" };
  }

  while (current < targetAdults) {
    plusButton.click();
    current++;
    await wait(300);
  }

  while (current > targetAdults) {
    minusButton.click();
    current--;
    await wait(300);
  }

  return {
    ok: true,
    field: "adults",
    value: targetAdults
  };
}

async function clickGuestDoneButton() {
  const buttons = Array.from(document.querySelectorAll("button"));

  const doneButton = buttons.find((button) => {
    const text = button.textContent.trim();
    return text === "완료" || text === "Done";
  });

  if (!doneButton) {
    return { ok: false, error: "Guest done button not found" };
  }

  doneButton.click();
  await wait(500);

  return {
    ok: true,
    field: "guestDone",
    text: doneButton.textContent.trim()
  };
}

async function clickSearchButton() {
  const searchButton =
    document.querySelector('button[type="submit"]') ||
    document.querySelector('[data-testid="searchbox-submit-button"]') ||
    Array.from(document.querySelectorAll("button")).find(
      (button) => button.textContent.trim() === "검색"
    );

  if (!searchButton) {
    return { ok: false, error: "Search button not found" };
  }

  searchButton.click();

  return { ok: true, field: "search" };
}

async function runBookingFlow(data) {
  await wait(500);

  fillDestination(data.destination);
  await wait(800);

  await selectBookingDates(data.checkIn, data.checkOut);
  await wait(800);

  await setAdultCount(data.adults);
  await wait(800);

  await clickGuestDoneButton();
  await wait(500);

  await clickSearchButton();

  return { ok: true };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("[Travel Agent] Message received:", message);

  if (message.type === "PING") {
    sendResponse({
      ok: true,
      url: window.location.href
    });
    return;
  }

  if (message.type === "FILL_DESTINATION") {
    const result = fillDestination(message.payload.destination);
    sendResponse(result);
    return;
  }

  if (message.type === "SELECT_BOOKING_DATES") {
    selectBookingDates(
      message.payload.checkIn,
      message.payload.checkOut
    ).then(sendResponse);

    return true;
  }

  if (message.type === "SET_ADULTS") {
    setAdultCount(message.payload.adults).then(sendResponse);
    return true;
  }

  if (message.type === "CLICK_GUEST_DONE") {
    clickGuestDoneButton().then(sendResponse);
    return true;
  }

  if (message.type === "CLICK_SEARCH") {
    clickSearchButton().then(sendResponse);
    return true;
  }

  if (message.type === "RUN_BOOKING_FLOW") {
    runBookingFlow(message.payload).then(sendResponse);
    return true;
  }
});
