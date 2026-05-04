console.log("[Travel Agent] Content script loaded");

function fillDestination(destination) {
  const input = document.querySelector('input[name="ss"]');

  if (input) {
    input.focus();
    input.value = destination;

    // 이벤트 강제로 발생 (중요)
    input.dispatchEvent(new Event("input", { bubbles: true }));

    console.log("Destination filled:", destination);
  } else {
    console.log("Destination input not found");
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "FILL_DESTINATION") {
    fillDestination(message.payload.destination);
    sendResponse({ ok: true });
  }
});