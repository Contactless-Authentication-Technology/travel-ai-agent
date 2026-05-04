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
});