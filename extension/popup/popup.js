pingButton.addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  chrome.tabs.sendMessage(tab.id, {
    type: "FILL_DESTINATION",
    payload: {
      destination: "Paris"
    }
  });
});