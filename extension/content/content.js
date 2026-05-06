console.log("[Travel Agent] Content script loaded");

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("[Travel Agent] Message received:", message);

  if (message.type === "PING") {
    sendResponse({ ok: true, url: window.location.href });
    return;
  }

  if (message.type === "FILL_DESTINATION") {
    fillDestination(message.payload.destination).then(sendResponse);
    return true;
  }

  if (message.type === "SELECT_BOOKING_DATES") {
    selectBookingDates(message.payload.checkIn, message.payload.checkOut).then(sendResponse);
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
