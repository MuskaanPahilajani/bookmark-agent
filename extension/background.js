chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get("backendUrl", ({ backendUrl }) => {
    if (!backendUrl) {
      chrome.storage.sync.set({ backendUrl: "" });
    }
  });
});
