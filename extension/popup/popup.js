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

function getPayloadFromTextarea() {
  const raw = document.getElementById("payloadTextarea").value;

  try {
    return JSON.parse(raw);
  } catch (error) {
    result.textContent = JSON.stringify(
      {
        ok: false,
        error: "Invalid JSON payload"
      },
      null,
      2
    );

    return null;
  }
}

function buildMockPayload() {
  return {
    site: "booking.com",
    payload: {
      destination: "Paris",
      checkIn: "2026-07-10",
      checkOut: "2026-07-15",
      adults: 2
    }
  };
}

document
  .getElementById("convertRequestButton")
  ?.addEventListener("click", () => {

    const payload = buildMockPayload();

    document.getElementById(
      "payloadTextarea"
    ).value = JSON.stringify(
      payload,
      null,
      2
    );
  });

document.getElementById("runFlowButton")
  ?.addEventListener("click", () => {
    const request = getPayloadFromTextarea();

    if (!request) {
      return;
    }

    if (request.site !== "booking.com") {
      result.textContent = JSON.stringify(
        {
          ok: false,
          error: `Unsupported site: ${request.site}`
        },
        null,
        2
      );
      return;
    }

    sendToContent({
      type: "RUN_BOOKING_FLOW",
      payload: request.payload
    });
  });