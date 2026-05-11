console.log("[Travel Agent] Content script loaded");

const DASHBOARD_API_BASE = "http://127.0.0.1:8000/api";
let isDashboardCommandRunning = false;

async function dashboardFetch(path, options = {}) {
  const response = await fetch(`${DASHBOARD_API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`Dashboard API failed: ${response.status}`);
  }

  return response.json();
}

async function reportAgentHeartbeat() {
  if (!window.location.hostname.includes("booking.com")) {
    return;
  }

  try {
    await dashboardFetch("/agent/heartbeat", {
      method: "POST",
      body: JSON.stringify({
        url: window.location.href,
        status: "ready"
      })
    });
  } catch (error) {
    console.warn("[Travel Agent] Heartbeat failed:", error.message);
  }
}

async function executeDashboardCommand(command) {
  switch (command.action) {
    case "RUN_BOOKING_FLOW":
      return runBookingFlow(command.payload);
    case "GET_TOP_HOTEL_RECOMMENDATIONS":
      return getTopHotelRecommendations(
        command.payload?.hotelPreference || [],
        command.payload?.limit || 3
      );
    case "CLICK_BEST_MATCHED_HOTEL":
      return clickBestMatchedHotel(command.payload?.hotelPreference || []);
    case "CONFIRM_SPECIFIC_HOTEL_SELECTION":
      return confirmSpecificHotelSelection(command.payload?.hotelIndex);
    default:
      return {
        ok: false,
        error: `Unsupported dashboard command: ${command.action}`
      };
  }
}

async function pollDashboardCommands() {
  if (!window.location.hostname.includes("booking.com")) {
    return;
  }

  if (isDashboardCommandRunning) {
    return;
  }

  isDashboardCommandRunning = true;

  try {
    const data = await dashboardFetch("/commands/next");
    const command = data.command;

    if (!command) {
      return;
    }

    console.log("[Travel Agent] Running dashboard command:", command);

    const response = await executeDashboardCommand(command);

    await dashboardFetch(`/commands/${command.id}/complete`, {
      method: "POST",
      body: JSON.stringify({
        result: {
          action: command.action,
          payload: command.payload,
          response
        }
      })
    });
  } catch (error) {
    console.warn("[Travel Agent] Dashboard command polling failed:", error.message);
  } finally {
    isDashboardCommandRunning = false;
  }
}

reportAgentHeartbeat();
setInterval(reportAgentHeartbeat, 10000);
setInterval(pollDashboardCommands, 2500);

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

  if (message.type === "EXTRACT_HOTELS") {
    const hotels = extractHotelCards();

    sendResponse({
      ok: true,
      hotels
    });

    return;
  }

  if (message.type === "CLICK_FIRST_HOTEL") {
    clickFirstHotelCard().then(sendResponse);
    return true;
  }

  if (message.type === "CLICK_BEST_MATCHED_HOTEL") {
    const result = clickBestMatchedHotel(
      message.payload?.hotelPreference || []
    );

    sendResponse(result);

    return;
  }

  if (message.type === "GET_TOP_HOTEL_RECOMMENDATIONS") {
    const result = getTopHotelRecommendations(
      message.payload?.hotelPreference || [],
      message.payload?.limit || 3
    );

    sendResponse(result);

    return;
  }

  if (message.type === "CONFIRM_SPECIFIC_HOTEL_SELECTION") {
    confirmSpecificHotelSelection(message.payload?.hotelIndex).then(sendResponse);
    return true;
  }

  if (message.type === "CONFIRM_HOTEL_SELECTION") {
    confirmRecommendedHotelSelection().then(sendResponse);
    return true;
  }

});
