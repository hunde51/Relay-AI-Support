(function () {
  "use strict";

  var KEY = document.currentScript.getAttribute("data-key") || "";
  var COLOR = document.currentScript.getAttribute("data-color") || "#6366f1";
  var TITLE = document.currentScript.getAttribute("data-title") || "Support";
  var BASE_URL =
    document.currentScript.getAttribute("data-base-url") ||
    "http://localhost:8000";

  if (!KEY) {
    console.error("[RelayAI Widget] Missing data-key attribute");
    return;
  }

  var state = {
    step: "form", // form | connecting | waiting | chatting
    ticketId: null,
    sessionToken: null,
    ws: null,
    messages: [],
    aiSteps: [],
  };

  /* ── Inject styles ─────────────────────────────────────────────────── */
  var style = document.createElement("style");
  style.textContent =
    "\
#relayai-widget * { box-sizing: border-box; margin: 0; padding: 0; }\
#relayai-widget { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }\
#relayai-btn {\
  position: fixed; bottom: 20px; right: 20px; z-index: 999999;\
  width: 56px; height: 56px; border-radius: 50%; border: none;\
  cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.2);\
  display: flex; align-items: center; justify-content: center;\
  transition: transform 0.2s;\
}\
#relayai-btn:hover { transform: scale(1.08); }\
#relayai-btn svg { width: 26px; height: 26px; fill: #fff; }\
#relayai-panel {\
  position: fixed; bottom: 88px; right: 20px; z-index: 999999;\
  width: 360px; height: 540px; border-radius: 16px;\
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);\
  display: none; flex-direction: column; overflow: hidden;\
  background: #fff; color: #1a1a1a;\
}\
#relayai-panel.open { display: flex; }\
#relayai-header {\
  padding: 16px 20px; color: #fff; font-weight: 600; font-size: 16px;\
  display: flex; justify-content: space-between; align-items: center;\
}\
#relayai-close { background: none; border: none; color: inherit; cursor: pointer; font-size: 20px; opacity: 0.8; }\
#relayai-close:hover { opacity: 1; }\
#relayai-body { flex: 1; overflow-y: auto; padding: 16px; }\
#relayai-footer { padding: 12px 16px; border-top: 1px solid #e5e7eb; }\
.relayai-form label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; color: #374151; }\
.relayai-form input, .relayai-form textarea {\
  width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px;\
  font-size: 14px; outline: none; margin-bottom: 12px;\
  font-family: inherit;\
}\
.relayai-form input:focus, .relayai-form textarea:focus { border-color: " +
    COLOR +
    "; box-shadow: 0 0 0 2px " +
    COLOR +
    "22; }\
.relayai-form textarea { resize: vertical; min-height: 72px; }\
.relayai-btn-primary {\
  width: 100%; padding: 10px; border: none; border-radius: 8px;\
  color: #fff; font-weight: 600; font-size: 14px; cursor: pointer;\
  transition: opacity 0.2s;\
}\
.relayai-btn-primary:hover { opacity: 0.9; }\
.relayai-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }\
.relayai-msg { margin-bottom: 12px; }\
.relayai-msg-customer, .relayai-msg-ai, .relayai-msg-system {\
  padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5;\
  max-width: 85%; word-wrap: break-word;\
}\
.relayai-msg-customer {\
  background: #f3f4f6; color: #1a1a1a;\
  margin-right: auto; border-bottom-left-radius: 4px;\
}\
.relayai-msg-ai {\
  background: " +
    COLOR +
    "; color: #fff;\
  margin-left: auto; border-bottom-right-radius: 4px;\
}\
.relayai-msg-system {\
  text-align: center; font-size: 12px; color: #9ca3af;\
  margin: 8px 0;\
}\
.relayai-ai-step {\
  padding: 8px 12px; margin-bottom: 6px; background: #f9fafb;\
  border-radius: 8px; font-size: 13px; color: #4b5563;\
  border-left: 3px solid " +
    COLOR +
    ";\
}\
.relayai-ai-step .step-name { font-weight: 600; }\
.relayai-ai-step .step-status { color: #6b7280; font-size: 12px; }\
.relayai-typing { display: flex; gap: 4px; padding: 8px 0; justify-content: center; }\
.relayai-typing span {\
  width: 8px; height: 8px; background: #d1d5db; border-radius: 50%;\
  animation: relayai-bounce 1.2s infinite;\
}\
.relayai-typing span:nth-child(2) { animation-delay: 0.2s; }\
.relayai-typing span:nth-child(3) { animation-delay: 0.4s; }\
@keyframes relayai-bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }\
.relayai-input-group { display: flex; gap: 8px; }\
.relayai-input-group input {\
  flex: 1; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px;\
  font-size: 14px; outline: none; font-family: inherit;\
}\
.relayai-input-group input:focus { border-color: " +
    COLOR +
    "; }\
.relayai-input-group button {\
  padding: 10px 16px; border: none; border-radius: 8px; background: " +
    COLOR +
    ";\
  color: #fff; font-weight: 600; cursor: pointer; font-size: 14px;\
}\
.relayai-input-group button:hover { opacity: 0.9; }\
";

  document.head.appendChild(style);

  /* ── Create DOM ────────────────────────────────────────────────────── */
  var container = document.createElement("div");
  container.id = "relayai-widget";

  var btn = document.createElement("button");
  btn.id = "relayai-btn";
  btn.style.background = COLOR;
  btn.innerHTML =
    '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/><path d="M7 9h10v2H7zm0-3h7v2H7z"/></svg>';
  btn.onclick = togglePanel;
  container.appendChild(btn);

  var panel = document.createElement("div");
  panel.id = "relayai-panel";
  panel.innerHTML =
    '<div id="relayai-header" style="background:' +
    COLOR +
    '">\
    <span>' +
    TITLE +
    '</span>\
    <button id="relayai-close">&times;</button>\
  </div>\
  <div id="relayai-body"></div>\
  <div id="relayai-footer"></div>';

  panel.querySelector("#relayai-close").onclick = togglePanel;
  container.appendChild(panel);
  document.body.appendChild(container);

  var bodyEl = document.getElementById("relayai-body");
  var footerEl = document.getElementById("relayai-footer");

  /* ── Core functions ────────────────────────────────────────────────── */

  function togglePanel() {
    panel.classList.toggle("open");
    if (panel.classList.contains("open") && state.step === "form") {
      renderForm();
    }
  }

  function renderForm() {
    bodyEl.innerHTML =
      '\
    <div class="relayai-form">\
      <label for="relayai-name">Your Name</label>\
      <input id="relayai-name" type="text" placeholder="Jane Smith" />\
      <label for="relayai-email">Email</label>\
      <input id="relayai-email" type="email" placeholder="jane@example.com" />\
      <label for="relayai-message">How can we help?</label>\
      <textarea id="relayai-message" placeholder="Describe your issue..."></textarea>\
      <button id="relayai-submit" class="relayai-btn-primary" style="background:' +
      COLOR +
      '">Send</button>\
    </div>';
    footerEl.innerHTML = "";
    document.getElementById("relayai-submit").onclick = submitTicket;
  }

  async function submitTicket() {
    var name = document.getElementById("relayai-name").value.trim();
    var email = document.getElementById("relayai-email").value.trim();
    var message = document.getElementById("relayai-message").value.trim();

    if (!name || !email || !message) {
      alert("Please fill in all fields");
      return;
    }

    var submitBtn = document.getElementById("relayai-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending...";

    try {
      var resp = await fetch(BASE_URL + "/widget/tickets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Widget-Key": KEY,
        },
        body: JSON.stringify({
          name: name,
          email: email,
          message: message,
          page_url: window.location.href,
        }),
      });

      if (!resp.ok) {
        var err = await resp.json();
        throw new Error(err.detail || "Failed to submit ticket");
      }

      var data = await resp.json();
      state.ticketId = data.ticket_id;
      state.sessionToken = data.session_token;
      state.step = "connecting";

      renderChatView();
      connectWebSocket();
    } catch (e) {
      bodyEl.innerHTML =
        '<div style="text-align:center;padding:24px;color:#dc2626">' +
        e.message +
        '</div><button class="relayai-btn-primary" style="background:' +
        COLOR +
        '" onclick="location.reload()">Try Again</button>';
    }
  }

  function renderChatView() {
    bodyEl.innerHTML = "";
    // add existing messages
    state.messages.forEach(function (m) {
      appendMessage(m);
    });
    // add pending AI steps
    state.aiSteps.forEach(function (s) {
      appendAIStep(s);
    });
    footerEl.innerHTML =
      '\
    <div class="relayai-input-group">\
      <input id="relayai-chat-input" type="text" placeholder="Type a message..." />\
      <button id="relayai-send">Send</button>\
    </div>';
    document.getElementById("relayai-send").onclick = sendMessage;
    document.getElementById("relayai-chat-input").onkeydown = function (e) {
      if (e.key === "Enter") sendMessage();
    };
  }

  async function sendMessage() {
    var input = document.getElementById("relayai-chat-input");
    var text = input.value.trim();
    if (!text) return;

    input.value = "";
    appendMessage({ sender_type: "customer", body: text });
    state.messages.push({ sender_type: "customer", body: text });

    try {
      var resp = await fetch(
        BASE_URL + "/widget/tickets/" + state.ticketId + "/messages",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-Token": state.sessionToken,
          },
          body: JSON.stringify({ body: text }),
        }
      );
      if (!resp.ok) throw new Error("Failed to send");
    } catch (e) {
      appendSystemMessage("Failed to send message. Please try again.");
    }
  }

  function connectWebSocket() {
    var wsUrl =
      BASE_URL.replace(/^http/, "ws") +
      "/ws/widget/" +
      state.ticketId +
      "?session=" +
      encodeURIComponent(state.sessionToken);

    state.ws = new WebSocket(wsUrl);
    state.ws.onopen = function () {
      state.step = "waiting";
      appendSystemMessage("Connected — AI is analyzing your request...");
    };

    state.ws.onmessage = function (evt) {
      try {
        var data = JSON.parse(evt.data);
        handleWSEvent(data);
      } catch (e) {
        // ignore parse errors
      }
    };

    state.ws.onclose = function () {
      // reconnect after delay
      setTimeout(function () {
        if (state.step !== "chatting") return;
        connectWebSocket();
      }, 3000);
    };

    state.ws.onerror = function () {
      // will trigger onclose
    };
  }

  function handleWSEvent(data) {
    // step events
    if (data.step) {
      appendAIStep({
        name: data.step,
        message: data.message,
        confidence: data.confidence,
        status: data.status,
      });
      state.aiSteps.push(data);
      return;
    }

    // tool call events
    if (data.tool_call) {
      var tc = data.tool_call;
      appendAIStep({
        name: "Tool: " + (tc.name || tc.tool_name || "unknown"),
        message: tc.status || "running",
        status: tc.status,
        confidence: null,
      });
      return;
    }

    // decision
    if (data.decision) {
      appendAIStep({
        name: "Decision",
        message: "Decided to: " + data.decision + " (confidence: " + (data.confidence || "?") + ")",
        status: "completed",
        confidence: data.confidence,
      });
      return;
    }

    // response
    if (data.response) {
      appendMessage({ sender_type: "ai", body: data.response });
      state.messages.push({ sender_type: "ai", body: data.response });
      state.step = "chatting";
      appendSystemMessage("Response ready. You can reply below.");
      return;
    }

    // ai_run_completed
    if (data.event === "ai_run_completed") {
      appendSystemMessage("AI analysis complete.");
      return;
    }

    // ticket_message_added
    if (data.event === "ticket_message_added" || data.message) {
      var msgBody = data.message || data.body || "";
      if (msgBody) {
        appendMessage({ sender_type: "ai", body: msgBody });
        state.messages.push({ sender_type: "ai", body: msgBody });
      }
      return;
    }
  }

  function appendMessage(msg) {
    var el = document.createElement("div");
    el.className = "relayai-msg";
    var isCustomer = msg.sender_type === "customer";
    var isAI = msg.sender_type === "ai";
    var bubbleClass = isCustomer
      ? "relayai-msg-customer"
      : isAI
      ? "relayai-msg-ai"
      : "relayai-msg-system";
    el.innerHTML =
      '<div class="' + bubbleClass + '">' + escapeHtml(msg.body) + "</div>";
    bodyEl.appendChild(el);
    bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  function appendAIStep(step) {
    var existing = bodyEl.querySelector(
      '.relayai-ai-step[data-step="' + escapeAttr(step.name || "") + '"]'
    );
    if (existing && step.status === "completed") {
      existing.querySelector(".step-status").textContent =
        "completed " + (step.confidence ? "(" + Math.round(step.confidence * 100) + "%)" : "✓");
      return;
    }
    if (existing) return;

    var el = document.createElement("div");
    el.className = "relayai-ai-step";
    el.setAttribute("data-step", step.name || "");
    el.innerHTML =
      '<div class="step-name">' +
      escapeHtml(step.name || "") +
      '</div>\
    <div class="step-status">' +
      (step.status || "running") +
      " " +
      (step.confidence ? "(" + Math.round(step.confidence * 100) + "%)" : "") +
      "</div>\
    <div style="font-size:12px;color:#6b7280;margin-top:2px">' +
      escapeHtml(step.message || "") +
      "</div>";
    bodyEl.appendChild(el);
    bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  function appendSystemMessage(text) {
    var el = document.createElement("div");
    el.className = "relayai-msg relayai-msg-system";
    el.innerHTML = '<div class="relayai-msg-system">' + escapeHtml(text) + "</div>";
    bodyEl.appendChild(el);
    bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  function escapeHtml(text) {
    if (!text) return "";
    var d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
  }

  function escapeAttr(text) {
    if (!text) return "";
    return text.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
})();
