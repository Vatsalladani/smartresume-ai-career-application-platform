// SmartApply Copilot - Service Worker Background Script (Manifest V3)

chrome.runtime.onInstalled.addListener(() => {
  console.log("SmartApply Copilot extension installed successfully.");
  chrome.storage.local.set({
    apiUrl: "http://127.0.0.1:8000/api/v1",
    authToken: null,
    connectedUser: null
  });
});

// Listener for messages from popup or content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_CONFIG") {
    chrome.storage.local.get(["apiUrl", "authToken", "connectedUser"], (data) => {
      sendResponse(data);
    });
    return true; // async response
  }

  if (request.action === "STORE_AUTH") {
    chrome.storage.local.set({
      authToken: request.token,
      connectedUser: request.user
    }, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (request.action === "CLEAR_AUTH") {
    chrome.storage.local.remove(["authToken", "connectedUser"], () => {
      sendResponse({ success: true });
    });
    return true;
  }
});
