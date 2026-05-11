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
          ok: false,
          warning: chrome.runtime.lastError.message
        },
        null,
        2
      );

      return;
    }

    result.textContent = JSON.stringify(
      response,
      null,
      2
    );
  });
}

function getPayloadFromTextarea() {
  const raw = document.getElementById(
    "payloadTextarea"
  ).value;

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

async function fetchPayloadFromAgent() {
  const text = document.getElementById(
    "naturalLanguageTextarea"
  ).value;

  const response = await fetch(
    "http://127.0.0.1:8000/parse",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text
      })
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to parse travel request"
    );
  }

  return await response.json();
}

document
  .getElementById("convertRequestButton")
  ?.addEventListener("click", async () => {
    try {
      const payload =
        await fetchPayloadFromAgent();

      document.getElementById(
        "payloadTextarea"
      ).value = JSON.stringify(
        payload,
        null,
        2
      );

      result.textContent = JSON.stringify(
        {
          ok: true,
          message:
            "Payload generated from FastAPI agent"
        },
        null,
        2
      );
    } catch (error) {
      result.textContent = JSON.stringify(
        {
          ok: false,
          error: error.message
        },
        null,
        2
      );
    }
  });

document
  .getElementById("runFlowButton")
  ?.addEventListener("click", () => {
    const request =
      getPayloadFromTextarea();

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

  document
  .getElementById("extractHotelsButton")
  ?.addEventListener("click", () => {
    sendToContent({
      type: "EXTRACT_HOTELS"
    });
  });

  document
  .getElementById("clickHotelButton")
  ?.addEventListener("click", () => {
    sendToContent({
      type: "CLICK_FIRST_HOTEL"
    });
  });

document
  .getElementById("clickBestMatchedHotelButton")
  ?.addEventListener("click", () => {
    const request = getPayloadFromTextarea();

    if (!request) {
      return;
    }

    sendToContent({
      type: "CLICK_BEST_MATCHED_HOTEL",
      payload: {
        hotelPreference: request.payload.hotelPreference || []
      }
    });
  });

  document
  .getElementById("confirmHotelSelectionButton")
  ?.addEventListener("click", () => {
    sendToContent({
      type: "CONFIRM_HOTEL_SELECTION"
    });
  });