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