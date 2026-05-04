const result = document.getElementById("result");

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  return tab;
}

async function sendToContent(message) {
  const tab = await getActiveTab();

  chrome.tabs.sendMessage(tab.id, message, (response) => {
    result.textContent = JSON.stringify(response, null, 2);
  });
}

document.getElementById("pingButton")?.addEventListener("click", () => {
  sendToContent({ type: "PING" });
});

document.getElementById("fillDestinationButton")?.addEventListener("click", () => {
  sendToContent({
    type: "FILL_DESTINATION",
    payload: {
      destination: "Paris"
    }
  });
});

document.getElementById("selectDatesButton")?.addEventListener("click", () => {
  sendToContent({
    type: "SELECT_BOOKING_DATES",
    payload: {
      checkIn: "2026-07-10",
      checkOut: "2026-07-15"
    }
  });
});

document.getElementById("setAdultsButton")?.addEventListener("click", () => {
  sendToContent({
    type: "SET_ADULTS",
    payload: {
      adults: 2
    }
  });
});

document.getElementById("guestDoneButton")?.addEventListener("click", () => {
  sendToContent({
    type: "CLICK_GUEST_DONE"
  });
});

document.getElementById("searchButton")?.addEventListener("click", () => {
  sendToContent({
    type: "CLICK_SEARCH"
  });
});

document.getElementById("runFlowButton")?.addEventListener("click", () => {
  sendToContent({
    type: "RUN_BOOKING_FLOW",
    payload: {
      destination: "Paris",
      checkIn: "2026-07-10",
      checkOut: "2026-07-15",
      adults: 2
    }
  });
});
