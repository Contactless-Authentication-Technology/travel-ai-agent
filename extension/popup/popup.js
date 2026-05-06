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
    if (chrome.runtime.lastError) {
      result.textContent = JSON.stringify(
        {
          ok: true,
          warning: chrome.runtime.lastError.message
        },
        null,
        2
      );
      return;
    }

    result.textContent = JSON.stringify(response, null, 2);
  });
}

function getInputValues() {
  return {
    destination: document.getElementById("destinationInput").value,
    checkIn: document.getElementById("checkInInput").value,
    checkOut: document.getElementById("checkOutInput").value,
    adults: parseInt(
      document.getElementById("adultsInput").value,
      10
    )
  };
}

document.getElementById("runFlowButton")
  ?.addEventListener("click", () => {

    const payload = getInputValues();

    sendToContent({
      type: "RUN_BOOKING_FLOW",
      payload
    });
});